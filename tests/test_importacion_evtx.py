"""Contrato público de importación; el único doble es el proceso externo."""

import hashlib
import json
import sqlite3
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from investigacion.adaptadores.controlados import InferenciaNoDisponibleControlada
from investigacion.adaptadores.hayabusa import EvidenciaHayabusa
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.modelos import FormatoExportacion, Origen
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.errores import ErrorDeImportacion


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    distribucion = tmp_path / "hayabusa"
    distribucion.mkdir()
    ejecutable = distribucion / "hayabusa"
    ejecutable.write_bytes(b"doble externo, no es Hayabusa")
    for nombre in ("rules", "config"):
        (distribucion / nombre).mkdir()
        (distribucion / nombre / "version.txt").write_text("fixture-v1")
    entrada = tmp_path / "entrada.evtx"
    entrada.write_bytes(b"ElfFile\x00" + bytes(4088))
    filas = [
        {"Timestamp": "2026-01-01T01:00:01+01:00", "RecordID": 42,
         "Channel": "System", "EventID": 7045, "Computer": "equipo",
         "RuleID": "regla-b", "AllFieldInfo": {"AccountName": "SYSTEM"}},
        {"Timestamp": "2026-01-01T00:00:00Z", "RecordID": 41,
         "Channel": "System", "EventID": 7036, "Computer": "equipo",
         "RuleID": "regla-a", "AllFieldInfo": {"param1": "servicio"}},
    ]

    def ejecutar(args, **kwargs):
        if args[-1] == "help":
            return subprocess.CompletedProcess(args, 0, "Hayabusa v4.1.0\n", "")
        destino = Path(args[args.index("-o") + 1])
        fuente = args[args.index("-f") + 1]
        destino.write_text("\n".join(json.dumps({**f, "EvtxFile": fuente}) for f in filas))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", ejecutar)
    return entrada, ejecutable, filas


def modulo(tmp_path, ejecutable):
    return ModuloDeInvestigacion(
        motor_evidencia=EvidenciaHayabusa(ejecutable, tmp_path / "evidencia"),
        motor_inferencia=InferenciaNoDisponibleControlada(),
        repositorio=RepositorioSQLite(tmp_path / "casos.sqlite"),
    )


def test_importar_reabrir_y_rastrear_evento_hasta_el_original(tmp_path, entorno):
    entrada, ejecutable, _ = entorno
    original = entrada.read_bytes()
    esperado_sha = hashlib.sha256(original).hexdigest()
    creado = modulo(tmp_path, ejecutable).crear_caso(Origen(str(entrada), "fixture sintético"))
    entrada.unlink()  # La consulta no depende de la ruta de carga.

    nuevo = modulo(tmp_path, ejecutable)
    caso = nuevo.consultar_caso(creado.id)
    assert [e.tipo_evento for e in caso.eventos] == ["7036", "7045"]
    assert caso.eventos[1].timestamp_normalizado == "2026-01-01T00:00:01.0000000Z"
    assert caso.origen.sha256 == esperado_sha
    assert caso.origen.procedencia == "fixture sintético"
    assert caso.origen.versiones["hayabusa"] == "4.1.0"
    assert "reglas_sha256" in caso.origen.versiones
    assert Path(caso.origen.ruta).read_bytes() == original
    for evento in caso.eventos:
        assert evento.caso_id == caso.id
        assert evento.origen_sha256 == esperado_sha
        assert "EventRecordID=" in evento.localizador_original
        assert evento.referencia_original.startswith(Path(caso.origen.ruta).as_uri())
    degradado = nuevo.investigar_caso(caso.id)
    exportado = json.loads(nuevo.exportar_caso(caso.id, FormatoExportacion.JSON))
    assert exportado["modalidad_inferencia"] == "degradado"
    assert exportado["eventos"][0]["uid"] == caso.eventos[0].uid
    assert nuevo.consultar_caso(caso.id) == degradado


def test_preserva_precision_windows_y_no_duplica_registros_por_regla(tmp_path, entorno):
    entrada, ejecutable, filas = entorno
    filas[0]["Timestamp"] = "2026-01-01T00:00:00.1234567Z"
    filas[1]["Timestamp"] = "2026-01-01T00:00:00.1234566Z"
    filas.append({**filas[0], "RuleID": "otra-regla", "MitreTags": ["T1543.003"]})
    m = modulo(tmp_path, ejecutable)
    uno = m.crear_caso(Origen(str(entrada), "fixture"))
    filas.reverse()
    dos = m.crear_caso(Origen(str(entrada), "fixture"))
    assert len(uno.eventos) == 2
    assert [e.uid for e in uno.eventos] == [e.uid for e in dos.eventos]
    assert [e.timestamp_normalizado for e in uno.eventos] == [
        "2026-01-01T00:00:00.1234566Z", "2026-01-01T00:00:00.1234567Z",
    ]
    contenido = json.loads(uno.eventos[1].contenido)
    assert len(contenido["detecciones_hayabusa"]) == 2
    assert contenido["procedencia_mapeo"] == "heredado_de_regla"
    assert {e.caso_id for e in dos.eventos} == {dos.id}


@pytest.mark.parametrize("cambio", [
    {"RecordID": None}, {"RecordID": True}, {"Channel": ""},
    {"Timestamp": "2026-01-01T00:00:00"}, {"AllFieldInfo": "dato no estructurado"},
])
def test_rechaza_salida_sin_trazabilidad_o_tiempo_interpretable(tmp_path, entorno, cambio):
    entrada, ejecutable, filas = entorno
    filas[0].update(cambio)
    with pytest.raises(ErrorDeImportacion):
        modulo(tmp_path, ejecutable).crear_caso(Origen(str(entrada), "fixture"))


@pytest.mark.parametrize("timestamp", [
    "2026-01-01T00:00:00+00:60",
    "2026-01-01T00:00:00-00:99",
    "0001-01-01T00:00:00+01:00",
    "9999-12-31T23:59:59-01:00",
])
def test_rechaza_tiempos_invalidos_sin_dejar_evidencia_parcial(tmp_path, entorno, timestamp):
    entrada, ejecutable, filas = entorno
    filas[0]["Timestamp"] = timestamp
    with pytest.raises(ErrorDeImportacion):
        modulo(tmp_path, ejecutable).crear_caso(Origen(str(entrada), "fixture"))
    assert list((tmp_path / "evidencia").iterdir()) == []


@pytest.mark.parametrize("titulo", [None, "Título sin identificador"])
def test_regla_ausente_permanece_nula_y_conserva_la_deteccion(tmp_path, entorno, titulo):
    entrada, ejecutable, filas = entorno
    filas[0].pop("RuleID")
    filas[0]["RuleTitle"] = titulo
    investigacion = modulo(tmp_path, ejecutable)
    creado = investigacion.crear_caso(Origen(str(entrada), "fixture"))
    evento = investigacion.consultar_caso(creado.id).eventos[1]
    assert evento.regla_hayabusa is None
    assert json.loads(evento.contenido)["detecciones_hayabusa"][0]["RuleTitle"] == titulo


def test_campos_disponibles_no_se_ocultan_por_alias_ausentes(tmp_path, entorno):
    entrada, ejecutable, filas = entorno
    filas[0]["AllFieldInfo"] = {
        "User": "-", "AccountName": "SYSTEM",
        "Image": "-", "NewProcessName": r"C:\Windows\cmd.exe",
        "ParentImage": "-", "ParentProcessName": r"C:\Windows\explorer.exe",
    }
    investigacion = modulo(tmp_path, ejecutable)
    creado = investigacion.crear_caso(Origen(str(entrada), "fixture"))
    evento = investigacion.consultar_caso(creado.id).eventos[1]
    assert evento.usuario == "SYSTEM"
    assert evento.proceso == r"C:\Windows\cmd.exe"
    assert evento.proceso_padre == r"C:\Windows\explorer.exe"


def test_un_conflicto_en_el_mismo_record_no_se_oculta(tmp_path, entorno):
    entrada, ejecutable, filas = entorno
    filas.append({**filas[0], "Computer": "otro-equipo"})
    with pytest.raises(ErrorDeImportacion, match="contradictorios"):
        modulo(tmp_path, ejecutable).crear_caso(Origen(str(entrada), "fixture"))


def test_sha_esperado_incorrecto_y_archivo_incompatible_se_rechazan(tmp_path, entorno):
    entrada, ejecutable, _ = entorno
    with pytest.raises(ErrorDeImportacion, match="SHA-256"):
        modulo(tmp_path, ejecutable).crear_caso(Origen(str(entrada), "fixture", sha256="0" * 64))
    entrada.write_text("no es EVTX")
    with pytest.raises(ErrorDeImportacion, match="EVTX"):
        modulo(tmp_path, ejecutable).crear_caso(Origen(str(entrada), "fixture"))


@pytest.mark.parametrize("fallo", [
    subprocess.TimeoutExpired("hayabusa", 1), FileNotFoundError("hayabusa"),
    "json-invalido", "salida-ausente", "salida-no-cero",
])
def test_fallo_externo_es_un_error_de_importacion(tmp_path, entorno, monkeypatch, fallo):
    entrada, ejecutable, _ = entorno
    original_run = subprocess.run

    def ejecutar(args, **kwargs):
        if args[-1] == "help":
            return original_run(args, **kwargs)
        if isinstance(fallo, Exception):
            raise fallo
        if fallo == "json-invalido":
            Path(args[args.index("-o") + 1]).write_text("{roto")
        return subprocess.CompletedProcess(args, 2 if fallo == "salida-no-cero" else 0, "", "fallo")

    monkeypatch.setattr(subprocess, "run", ejecutar)
    with pytest.raises(ErrorDeImportacion):
        modulo(tmp_path, ejecutable).crear_caso(Origen(str(entrada), "fixture"))


def test_sqlite_conserva_hallazgos_y_revierte_guardado_invalido(tmp_path, entorno):
    from investigacion.adaptadores.controlados import InferenciaControlada
    from investigacion.modelos import PropuestaHallazgo

    entrada, ejecutable, _ = entorno
    repo = RepositorioSQLite(tmp_path / "casos.sqlite")
    m = modulo(tmp_path, ejecutable)
    caso = m.crear_caso(Origen(str(entrada), "fixture"))
    propuesta = PropuestaHallazgo("Hipótesis", (caso.eventos[0].uid,),
                                 explicaciones_alternativas=("Administración",))
    m2 = ModuloDeInvestigacion(EvidenciaHayabusa(ejecutable, tmp_path / "evidencia"),
                              InferenciaControlada((propuesta,)), repo)
    investigado = m2.investigar_caso(caso.id)
    assert modulo(tmp_path, ejecutable).consultar_caso(caso.id) == investigado
    # Un fallo a mitad de escritura no borra el estado anterior.
    with pytest.raises(sqlite3.IntegrityError):
        repo.guardar(replace(investigado, eventos=(caso.eventos[0], caso.eventos[0])))
    assert modulo(tmp_path, ejecutable).consultar_caso(caso.id) == investigado
