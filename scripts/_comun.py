"""Andamiaje compartido por los scripts de evaluación reproducible.

`benchmark_modelos.py` y `evaluar_escenarios.py` corren el mismo pipeline
(motor Ollama + validador sobre el catálogo local) con criterios distintos;
lo común vive acá para que ambos midan contra exactamente el mismo montaje.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.catalogo_attack import CatalogoAttack, cargar_catalogo
from investigacion.errores import InferenciaNoDisponible
from investigacion.modelos import Evento
from investigacion.validacion import ValidadorDeReferencias

RAIZ = Path(__file__).resolve().parents[1]
MODELOS_DEFECTO = ["llama3.2:3b", "qwen2.5:7b-instruct"]


def montar(modelo: str, base_url: str) -> tuple[InferenciaOllama, ValidadorDeReferencias, CatalogoAttack]:
    """Motor, validador y catálogo compartiendo el mismo subconjunto ATT&CK."""
    catalogo = cargar_catalogo()
    motor = InferenciaOllama(modelo, base_url=base_url, catalogo=catalogo)
    return motor, ValidadorDeReferencias(catalogo=catalogo), catalogo


def calentar(motor: InferenciaOllama, eventos: tuple[Evento, ...]) -> None:
    """Corrida descartada que carga el modelo en Ollama antes de medir latencia."""
    try:
        motor.proponer("calentamiento", eventos)
    except InferenciaNoDisponible:
        pass


def parser_base(descripcion: str | None, salida_defecto: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=descripcion)
    parser.add_argument("--modelos", nargs="+", default=MODELOS_DEFECTO)
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--salida", type=Path, default=salida_defecto)
    return parser


def escribir_reporte(salida: Path, reporte: Any, markdown: str) -> None:
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.with_suffix(".json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    salida.with_suffix(".md").write_text(markdown, encoding="utf-8")
