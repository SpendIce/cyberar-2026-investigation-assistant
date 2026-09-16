"""Prueba opt-in del tracer real EVTX → hallazgo → evidencia; ver docs/tracer.md.

Recorre el flujo completo sin dobles: importación Hayabusa real, persistencia
SQLite, inferencia estructurada contra Ollama real, validación y navegación en
Streamlit del hallazgo hasta la evidencia citada.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from investigacion.adaptadores.sqlite import RepositorioSQLite

APP = Path(__file__).resolve().parents[1] / "src" / "investigacion" / "ui" / "app.py"


@pytest.mark.skipif(
    not (os.environ.get("HAYABUSA_BIN") and os.environ.get("OLLAMA_MODELO_PRUEBA")),
    reason="requiere HAYABUSA_BIN, OLLAMA_MODELO_PRUEBA, Ollama corriendo y el fixture público",
)
def test_tracer_real_evtx_hallazgo_evidencia(tmp_path, monkeypatch):
    carpeta = Path(__file__).parent / "fixtures" / "publico"
    manifiesto = json.loads((carpeta / "manifest.json").read_text())
    entrada = carpeta / manifiesto["archivo"]
    assert entrada.is_file(), "Ejecutar uv run python scripts/descargar_fixture.py"
    datos = tmp_path / "datos"

    resultado = subprocess.run(
        [
            sys.executable, "-m", "investigacion.importar",
            "--evtx", str(entrada), "--procedencia", manifiesto["procedencia"],
            "--sha256", manifiesto["sha256"],
            "--hayabusa", os.environ["HAYABUSA_BIN"],
            "--datos", str(datos),
            "--modelo", os.environ["OLLAMA_MODELO_PRUEBA"],
            "--ollama-url", os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        ],
        capture_output=True, text=True, timeout=600, check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    resumen = json.loads(resultado.stdout)

    caso = RepositorioSQLite(datos / "casos.sqlite").obtener(resumen["caso_id"])
    assert caso is not None
    assert caso.eventos, "la importación real debe producir eventos detectados"
    assert caso.origen.sha256 == manifiesto["sha256"]
    assert caso.origen.versiones["hayabusa"] == "4.1.0"
    assert "salida_sha256" in caso.origen.versiones
    assert caso.modalidad_inferencia is not None
    existentes = {evento.uid for evento in caso.eventos}
    assert caso.hallazgos, "el tracer real debe validar al menos un hallazgo"
    for hallazgo in caso.hallazgos:
        assert hallazgo.referencias_eventos
        assert set(hallazgo.referencias_eventos) <= existentes

    monkeypatch.setenv("INVESTIGACION_DATOS", str(datos))
    at = AppTest.from_file(str(APP))
    at.run()
    assert not at.exception
    textos = "\n".join(
        str(elemento.value)
        for coleccion in (at.markdown, at.header, at.subheader, at.caption)
        for elemento in coleccion
    )
    assert caso.hallazgos[0].hipotesis in textos
    uid = caso.hallazgos[0].referencias_eventos[0]
    at.button(key=f"referencia-0-{uid}").click().run()
    assert not at.exception
    assert any(header.value == f"Evento {uid}" for header in at.header)
