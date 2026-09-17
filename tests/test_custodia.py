"""Cadena de custodia: sello de integridad del caso y verificación del informe.

Cada escritura del repositorio encadena un sello nuevo al anterior (registro
append-only); el sello de la cabeza viaja en el informe exportado, de modo que
una edición posterior del estado persistido —o una reescritura de la propia
cadena— se detecta al verificar el caso contra el sello publicado.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from investigacion.adaptadores.controlados import (
    EvidenciaControlada,
    InferenciaControlada,
)
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.custodia import encadenar, sello_de_caso, sello_de_exportacion
from investigacion.modelos import FormatoExportacion, Origen
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.sembrado import (
    PROCEDENCIA_SEMBRADA,
    RUTA_SEMBRADA,
    SHA_SEMBRADO,
    VERSIONES_SEMBRADAS,
    eventos_sembrados,
    propuesta_sembrada,
)


def _modulo_sqlite(tmp_path: Path) -> tuple[ModuloDeInvestigacion, RepositorioSQLite]:
    repositorio = RepositorioSQLite(tmp_path / "casos.sqlite")
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(
            eventos=eventos_sembrados(),
            sha256=SHA_SEMBRADO,
            nombre=RUTA_SEMBRADA,
            versiones=VERSIONES_SEMBRADAS,
        ),
        motor_inferencia=InferenciaControlada(propuestas=(propuesta_sembrada(),)),
        repositorio=repositorio,
        generador_de_ids=lambda: "caso-custodia",
    )
    return modulo, repositorio


def _caso_investigado(tmp_path: Path) -> tuple[ModuloDeInvestigacion, str]:
    modulo, _ = _modulo_sqlite(tmp_path)
    caso = modulo.crear_caso(Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA))
    modulo.investigar_caso(caso.id)
    return modulo, caso.id


def test_el_sello_es_determinista_y_cambia_con_el_estado(tmp_path: Path) -> None:
    modulo, caso_id = _caso_investigado(tmp_path)
    caso = modulo.consultar_caso(caso_id)

    assert sello_de_caso(caso) == sello_de_caso(caso)
    alterado = replace(caso, errores=(*caso.errores, "manipulado"))
    assert sello_de_caso(alterado) != sello_de_caso(caso)


def test_cada_guardado_encadena_un_sello_nuevo_al_anterior(tmp_path: Path) -> None:
    modulo, repositorio = _modulo_sqlite(tmp_path)
    caso = modulo.crear_caso(
        Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA)
    )
    modulo.investigar_caso(caso.id)

    cadena = repositorio.cadena_custodia(caso.id)

    assert len(cadena) == 2
    primera, segunda = cadena
    assert primera.sello_anterior is None
    assert primera.sello == encadenar(None, primera.sello_estado)
    assert segunda.sello_anterior == primera.sello
    assert segunda.sello == encadenar(primera.sello, segunda.sello_estado)
    assert segunda.sello_estado == sello_de_caso(modulo.consultar_caso(caso.id))


def test_verificar_caso_integro_sobre_el_estado_persistido(tmp_path: Path) -> None:
    modulo, caso_id = _caso_investigado(tmp_path)

    verificacion = modulo.verificar_caso(caso_id)

    assert verificacion.integro
    assert verificacion.discrepancias == ()
    assert verificacion.sello is not None


def test_la_edicion_directa_del_estado_persistido_se_detecta(tmp_path: Path) -> None:
    modulo, caso_id = _caso_investigado(tmp_path)
    with sqlite3.connect(tmp_path / "casos.sqlite") as db:
        (datos,) = db.execute(
            "SELECT datos FROM casos WHERE id = ?", (caso_id,)
        ).fetchone()
        alterado = json.loads(datos)
        alterado["hallazgos"][0]["hipotesis"] = "Conclusión manipulada a mano"
        db.execute(
            "UPDATE casos SET datos = ? WHERE id = ?",
            (json.dumps(alterado, ensure_ascii=False), caso_id),
        )

    verificacion = modulo.verificar_caso(caso_id)

    assert not verificacion.integro
    assert any("estado" in d for d in verificacion.discrepancias)


def test_la_eliminacion_de_una_entrada_de_la_cadena_se_detecta(tmp_path: Path) -> None:
    modulo, caso_id = _caso_investigado(tmp_path)
    with sqlite3.connect(tmp_path / "casos.sqlite") as db:
        db.execute(
            "DELETE FROM custodia WHERE caso_id = ? AND seq = 1", (caso_id,)
        )

    verificacion = modulo.verificar_caso(caso_id)

    assert not verificacion.integro
    assert any("cadena" in d for d in verificacion.discrepancias)


def test_el_sello_publicado_detecta_una_cadena_reescrita(tmp_path: Path) -> None:
    modulo, caso_id = _caso_investigado(tmp_path)
    sello_publicado = modulo.verificar_caso(caso_id).sello
    with sqlite3.connect(tmp_path / "casos.sqlite") as db:
        db.execute("DELETE FROM custodia WHERE caso_id = ?", (caso_id,))
    modulo.investigar_caso(caso_id)

    verificacion = modulo.verificar_caso(caso_id, sello_publicado=sello_publicado)

    assert not verificacion.integro
    assert any("sello publicado" in d for d in verificacion.discrepancias)


def test_el_informe_publica_el_sello_de_custodia(tmp_path: Path) -> None:
    modulo, caso_id = _caso_investigado(tmp_path)
    sello = modulo.verificar_caso(caso_id).sello

    markdown = modulo.exportar_caso(caso_id, FormatoExportacion.MARKDOWN)
    datos = json.loads(modulo.exportar_caso(caso_id, FormatoExportacion.JSON))

    assert sello is not None and sello in markdown
    assert "## Integridad" in markdown
    assert datos["custodia"] == {"sello": sello, "escrituras": 2}


def test_el_repositorio_en_memoria_tambien_registra_custodia() -> None:
    repositorio = RepositorioEnMemoria()
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(
            eventos=eventos_sembrados(), sha256=SHA_SEMBRADO, nombre=RUTA_SEMBRADA
        ),
        motor_inferencia=InferenciaControlada(propuestas=(propuesta_sembrada(),)),
        repositorio=repositorio,
        generador_de_ids=lambda: "caso-memoria",
    )
    caso = modulo.crear_caso(
        Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA)
    )
    modulo.investigar_caso(caso.id)

    assert modulo.verificar_caso(caso.id).integro
    assert len(repositorio.cadena_custodia(caso.id)) == 2


def test_el_cli_sella_el_informe_y_verifica_el_artefacto(tmp_path: Path) -> None:
    _, caso_id = _caso_investigado(tmp_path)
    salida = tmp_path / "informe.md"

    resultado = subprocess.run(
        [
            sys.executable, "-m", "investigacion.informe",
            "--datos", str(tmp_path), "--caso", caso_id, "--salida", str(salida),
        ],
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr

    lado = tmp_path / "informe.md.sha256"
    assert lado.read_text(encoding="utf-8").split()[0] == sello_de_exportacion(
        salida.read_text(encoding="utf-8")
    )

    verificacion = subprocess.run(
        [
            sys.executable, "-m", "investigacion.informe",
            "--datos", str(tmp_path), "--verificar", str(salida),
        ],
        capture_output=True,
        text=True,
    )
    assert verificacion.returncode == 0, verificacion.stderr

    salida.write_text(
        salida.read_text(encoding="utf-8") + "\nAlterado a mano.\n",
        encoding="utf-8",
    )
    verificacion = subprocess.run(
        [
            sys.executable, "-m", "investigacion.informe",
            "--datos", str(tmp_path), "--verificar", str(salida),
        ],
        capture_output=True,
        text=True,
    )
    assert verificacion.returncode == 1
    assert "alterado" in verificacion.stderr.lower()
