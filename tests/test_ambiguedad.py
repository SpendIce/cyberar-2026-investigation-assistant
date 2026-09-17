"""Criterios deterministas de la demostración de ambigüedad (#8)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from streamlit.testing.v1 import AppTest

from investigacion.adaptadores.controlados import InferenciaControlada
from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.catalogo_attack import CatalogoAttack, Tecnica
from investigacion.escenarios import (
    ARCHIVO_COMPARACION,
    ESCENARIO_LEGITIMO,
    ESCENARIO_SOSPECHOSO,
    EscenarioComparacion,
    evidencia_control_legitimo,
    eventos_control_legitimo,
    guardar_comparacion,
    origen_control_legitimo,
)
from investigacion.modelos import (
    Caso,
    EstadoRevision,
    Hallazgo,
    ModalidadInferencia,
    ProcedenciaMapeo,
    PropuestaHallazgo,
)
from investigacion.modulo import ModuloDeInvestigacion

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "src" / "investigacion" / "ui" / "app.py"
VERDAD_REFERENCIA = RAIZ / "docs" / "evaluacion" / "verdad-referencia-escenarios.json"


def _catalogo() -> CatalogoAttack:
    return CatalogoAttack(
        version="prueba", fecha="2026-01-01", procedencia="prueba",
        tecnicas={"T1021.002": Tecnica("T1021.002", "SMB/Windows Admin Shares")},
    )


def _hallazgo(caso_id: str, hipotesis: str = "Actividad de doble uso a revisar") -> Hallazgo:
    return Hallazgo(
        caso_id=caso_id,
        hipotesis=hipotesis,
        referencias_eventos=("ctl-2", "ctl-3"),
        campos_citados=("proceso",),
        tecnicas_candidatas=("T1021.002",),
        razon_vinculo="PSEXESVC seguido de PowerShell",
        procedencia_mapeo=ProcedenciaMapeo.MODELO,
        explicaciones_alternativas=(),
        evidencia_faltante=(),
        limitaciones=(),
        estado_revision=EstadoRevision.PENDIENTE,
    )


def _caso(caso_id: str, *, hallazgo: Hallazgo | None = None) -> Caso:
    origen = origen_control_legitimo()
    eventos = tuple(
        replace(evento, caso_id=caso_id, origen_sha256=origen.sha256 or "")
        for evento in eventos_control_legitimo()
    )
    return Caso(
        id=caso_id,
        origen=origen,
        eventos=eventos,
        hallazgos=(hallazgo or _hallazgo(caso_id),),
        modalidad_inferencia=ModalidadInferencia.MODELO_LOCAL,
    )


def _textos(at: AppTest) -> str:
    colecciones = (at.title, at.header, at.subheader, at.markdown, at.caption, at.info,
                   at.warning, at.error)
    return "\n".join(str(elemento.value) for grupo in colecciones for elemento in grupo)


def test_verdad_de_referencia_permanece_fuera_de_la_solicitud_al_modelo() -> None:
    verdad = json.loads(VERDAD_REFERENCIA.read_text(encoding="utf-8"))
    capturado: dict[str, Any] = {}

    def transporte_espia(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        capturado["cuerpo"] = cuerpo
        return {"message": {"content": json.dumps({"hallazgos": []})}}

    motor = InferenciaOllama(
        "modelo-de-prueba", catalogo=_catalogo(), transporte=transporte_espia
    )
    motor.proponer("caso-b", eventos_control_legitimo())

    mensaje_usuario = capturado["cuerpo"]["messages"][1]["content"]
    assert set(json.loads(mensaje_usuario)) == {
        "eventos", "uids_citables", "tecnicas_permitidas"
    }
    solicitud = json.dumps(capturado["cuerpo"], ensure_ascii=False).casefold()
    reveladores = (
        "escenario_id", "contexto_esperado", "fundamento",
        "contexto_operador_conocido", "procedencia",
    )
    for escenario in verdad["escenarios"]:
        for clave in escenario:
            assert clave.casefold() not in solicitud
        for clave in reveladores:
            assert str(escenario[clave]).casefold() not in solicitud


def test_control_legitimo_conserva_verdad_de_referencia_separada() -> None:
    caso = _caso("caso-b")
    serializado_eventos = json.dumps(
        [evento.__dict__ for evento in caso.eventos], default=dict
    ).casefold()

    assert caso.origen.versiones["captura"] == "sintetica"
    assert "contexto_esperado" not in serializado_eventos
    assert "legitimo" not in serializado_eventos
    assert ESCENARIO_LEGITIMO in VERDAD_REFERENCIA.read_text(encoding="utf-8")


def test_dos_escenarios_persistidos_se_comparan_desde_la_misma_interfaz(
    tmp_path: Path, monkeypatch,
) -> None:
    repositorio = RepositorioSQLite(tmp_path / "casos.sqlite")
    repositorio.guardar(_caso("caso-a"))
    repositorio.guardar(_caso("caso-b"))
    guardar_comparacion(
        tmp_path / ARCHIVO_COMPARACION,
        (
            EscenarioComparacion(
                ESCENARIO_SOSPECHOSO, "caso-a", "Escenario A — evidencia pública",
                "Actividad a investigar", "EVTX público real",
            ),
            EscenarioComparacion(
                ESCENARIO_LEGITIMO, "caso-b", "Escenario B — control documentado",
                "Operación administrativa", "control sintético/documentado",
            ),
        ),
    )
    monkeypatch.setenv("INVESTIGACION_DATOS", str(tmp_path))

    at = AppTest.from_file(str(APP)).run()
    assert not at.exception
    assert "Escenario A — evidencia pública" in _textos(at)
    assert "Evidencia observada" in _textos(at)
    at.selectbox(key="caso-persistido").set_value("caso-b").run()

    textos = _textos(at)
    assert not at.exception
    assert "Escenario B — control documentado" in textos
    assert "Explicaciones alternativas:** No declarada por el modelo" in textos
    assert "Evidencia faltante / incertidumbre:** No especificada" in textos
    assert "Limitaciones:** No especificada" in textos
    assert "Estado de revisión:** pendiente" in textos
    assert "pendientes de revisión humana" in textos
    for caso_id in ("caso-a", "caso-b"):
        caso = repositorio.obtener(caso_id)
        assert caso is not None
        existentes = {evento.uid for evento in caso.eventos}
        assert all(
            set(hallazgo.referencias_eventos) <= existentes
            for hallazgo in caso.hallazgos
        )


def test_lenguaje_concluyente_no_se_persiste_ni_se_muestra(
    tmp_path: Path, monkeypatch,
) -> None:
    concluyente = PropuestaHallazgo(
        hipotesis="Ataque confirmado por PowerShell",
        referencias_eventos=("ctl-2",),
        razon_vinculo="PSEXESVC presente",
    )
    concluyente_en_otro_campo = PropuestaHallazgo(
        hipotesis="Ejecución de servicio remoto a revisar",
        referencias_eventos=("ctl-2",),
        razon_vinculo="PSEXESVC seguido de PowerShell",
        explicaciones_alternativas=("Ninguna: la intrusión confirmada es evidente",),
    )
    origen = origen_control_legitimo()
    repositorio = RepositorioSQLite(tmp_path / "casos.sqlite")
    modulo = ModuloDeInvestigacion(
        evidencia_control_legitimo(),
        InferenciaControlada((concluyente, concluyente_en_otro_campo)),
        repositorio,
        generador_de_ids=lambda: "caso-rechazado",
    )
    caso = modulo.investigar_caso(modulo.crear_caso(origen).id)
    assert caso.hallazgos == ()
    assert any("lenguaje concluyente" in error for error in caso.errores)

    legado = _caso(
        "caso-legado",
        hallazgo=_hallazgo("caso-legado", "Equipo comprometido por PsExec"),
    )
    repositorio.guardar(legado)
    monkeypatch.setenv("INVESTIGACION_DATOS", str(tmp_path))
    at = AppTest.from_file(str(APP)).run()
    at.selectbox(key="caso-persistido").set_value("caso-legado").run()
    textos = _textos(at)
    assert "Equipo comprometido por PsExec" not in textos
    assert "Formulación no mostrada" in textos


def test_abstencion_no_se_transforma_en_ataque(tmp_path: Path) -> None:
    origen = origen_control_legitimo()
    repositorio = RepositorioSQLite(tmp_path / "casos.sqlite")
    modulo = ModuloDeInvestigacion(
        evidencia_control_legitimo(),
        InferenciaControlada(()),
        repositorio,
        generador_de_ids=lambda: "caso-sin-hallazgos",
    )

    caso = modulo.investigar_caso(modulo.crear_caso(origen).id)

    assert caso.hallazgos == ()
    assert caso.modalidad_inferencia is ModalidadInferencia.MODELO_LOCAL
