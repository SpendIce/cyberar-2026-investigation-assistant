"""Andamiaje compartido por los scripts de evaluación reproducible.

`benchmark_modelos.py` y `evaluar_escenarios.py` corren el mismo pipeline
(motor Ollama + validador sobre el catálogo local) con criterios distintos;
lo común vive acá para que ambos midan contra exactamente el mismo montaje.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import subprocess
from pathlib import Path
from typing import Any

from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.adaptadores.sqlite import RepositorioSQLite
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


def calentar(motor: InferenciaOllama, eventos: tuple[Evento, ...]) -> bool:
    """Corrida descartada que carga el modelo en Ollama antes de medir latencia.

    Devuelve si la inferencia respondió; quien la ejecute puede usarlo para
    no repetir timeouts corridas que de todos modos van a fallar.
    """
    try:
        motor.proponer("calentamiento", eventos)
    except InferenciaNoDisponible:
        return False
    return True


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


def eventos_caso_a(datos: Path | None, caso_id: str | None) -> tuple[Evento, ...] | None:
    """Los eventos del caso real persistido por el tracer, si se indicaron."""
    if datos is None and caso_id is None:
        return None
    if datos is None or caso_id is None:
        raise SystemExit("--datos y --caso-sospechoso deben utilizarse juntos")
    caso = RepositorioSQLite(datos / "casos.sqlite").obtener(caso_id)
    if caso is None:
        raise SystemExit(f"caso sospechoso inexistente: {caso_id}")
    return caso.eventos


def memoria_reportada(modelo: str, comando: str = "ollama ps") -> str | None:
    """La línea de `ollama ps` (o equivalente) que reporta la memoria del modelo."""
    partes = shlex.split(comando)
    if not partes:
        return None
    try:
        salida = subprocess.run(
            partes, capture_output=True, text=True, timeout=15, check=False
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for linea in salida.splitlines()[1:]:
        columnas = linea.split()
        if columnas and columnas[0] == modelo:
            return linea.strip()
    return None


def _cpus_disponibles() -> int:
    if hasattr(os, "sched_getaffinity"):
        return len(os.sched_getaffinity(0))
    return os.cpu_count() or 0


def info_hardware() -> dict[str, str]:
    memoria_total = "desconocida"
    try:
        for linea in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if linea.startswith("MemTotal:"):
                memoria_total = linea.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {
        "plataforma": platform.platform(),
        "procesador": platform.processor() or platform.machine(),
        "cpus_logicas": str(_cpus_disponibles()),
        "memoria_total": memoria_total,
    }
