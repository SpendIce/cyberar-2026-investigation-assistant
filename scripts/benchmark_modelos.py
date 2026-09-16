"""Benchmark reproducible de modelos locales candidatos para el fallback Ollama.

Ejecuta el mismo caso sembrado, el mismo hardware y los mismos criterios de
calidad y latencia contra cada modelo candidato (issue #4). No decide el
modelo por reputación o tamaño nominal (ADR-0009): mide esquema, citas,
técnicas y latencia, y dejar constancia de las mediciones en
docs/benchmarks/resultados-modelos.{json,md}. Es una evaluación reproducible
separada de la suite de pruebas unitarias; no debe convertirse en una prueba
determinista (ver AGENTS.md / spec #1, "Testing Decisions").

Uso:
    uv run python scripts/benchmark_modelos.py
    uv run python scripts/benchmark_modelos.py --modelos llama3.2:3b qwen2.5:7b-instruct --repeticiones 5
"""

from __future__ import annotations

import os
import platform
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from _comun import RAIZ, calentar, escribir_reporte, montar, parser_base
from investigacion.catalogo_attack import cargar_catalogo
from investigacion.errores import HallazgoInvalido, InferenciaNoDisponible
from investigacion.sembrado import eventos_sembrados


@dataclass
class MedicionCorrida:
    corrida: int
    exito_esquema: bool
    latencia_segundos: float | None
    hallazgos_propuestos: int
    hallazgos_aceptados: int
    referencias_citadas: int
    referencias_resolubles: int
    tecnicas_citadas: int
    tecnicas_en_catalogo: int
    error: str | None


@dataclass
class ResultadoModelo:
    modelo: str
    memoria_ollama_ps: str | None
    corridas: list[MedicionCorrida]


def _memoria_reportada(modelo: str) -> str | None:
    try:
        salida = subprocess.run(
            ["ollama", "ps"], capture_output=True, text=True, timeout=10, check=False
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


def _info_hardware() -> dict[str, str]:
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


def _correr_modelo(modelo: str, repeticiones: int, base_url: str) -> ResultadoModelo:
    eventos = eventos_sembrados()
    motor, validador, catalogo = montar(modelo, base_url)
    referencias_existentes = {evento.uid for evento in eventos}
    calentar(motor, eventos)

    corridas: list[MedicionCorrida] = []
    for indice in range(1, repeticiones + 1):
        inicio = time.monotonic()
        try:
            propuestas = motor.proponer(f"benchmark-{indice}", eventos)
            latencia = time.monotonic() - inicio
        except InferenciaNoDisponible as exc:
            corridas.append(
                MedicionCorrida(
                    corrida=indice, exito_esquema=False, latencia_segundos=None,
                    hallazgos_propuestos=0, hallazgos_aceptados=0, referencias_citadas=0,
                    referencias_resolubles=0, tecnicas_citadas=0, tecnicas_en_catalogo=0,
                    error=str(exc),
                )
            )
            continue

        referencias_citadas = sum(len(p.referencias_eventos) for p in propuestas)
        referencias_resolubles = sum(
            1
            for p in propuestas
            for ref in p.referencias_eventos
            if ref in referencias_existentes
        )
        tecnicas_citadas = sum(len(p.tecnicas_candidatas) for p in propuestas)
        tecnicas_en_catalogo = sum(
            1
            for p in propuestas
            for tecnica in p.tecnicas_candidatas
            if catalogo.contiene(tecnica)
        )
        aceptados = 0
        for propuesta in propuestas:
            try:
                validador.validar(f"benchmark-{indice}", propuesta, eventos)
                aceptados += 1
            except HallazgoInvalido:
                pass

        corridas.append(
            MedicionCorrida(
                corrida=indice, exito_esquema=True, latencia_segundos=round(latencia, 3),
                hallazgos_propuestos=len(propuestas), hallazgos_aceptados=aceptados,
                referencias_citadas=referencias_citadas,
                referencias_resolubles=referencias_resolubles,
                tecnicas_citadas=tecnicas_citadas, tecnicas_en_catalogo=tecnicas_en_catalogo,
                error=None,
            )
        )
    return ResultadoModelo(modelo=modelo, memoria_ollama_ps=_memoria_reportada(modelo), corridas=corridas)


def _resumen_markdown(hardware: dict[str, str], resultados: list[ResultadoModelo]) -> str:
    lineas = [
        "# Resultados del benchmark de modelos locales candidatos",
        "",
        f"Generado: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "",
        "## Hardware",
        "",
        *(f"- {clave}: {valor}" for clave, valor in hardware.items()),
        "",
        "## Resumen por modelo",
        "",
        "| Modelo | Corridas OK | Latencia media (s) | Hallazgos aceptados/propuestos "
        "| Referencias resolubles/citadas | Técnicas en catálogo/citadas | Memoria (ollama ps) |",
        "|---|---|---|---|---|---|---|",
    ]
    for resultado in resultados:
        exitosas = [c for c in resultado.corridas if c.exito_esquema]
        latencias = [c.latencia_segundos for c in exitosas if c.latencia_segundos is not None]
        latencia_media = f"{statistics.mean(latencias):.2f}" if latencias else "sin datos"
        propuestos = sum(c.hallazgos_propuestos for c in exitosas)
        aceptados = sum(c.hallazgos_aceptados for c in exitosas)
        ref_citadas = sum(c.referencias_citadas for c in exitosas)
        ref_resolubles = sum(c.referencias_resolubles for c in exitosas)
        tec_citadas = sum(c.tecnicas_citadas for c in exitosas)
        tec_catalogo = sum(c.tecnicas_en_catalogo for c in exitosas)
        lineas.append(
            f"| {resultado.modelo} | {len(exitosas)}/{len(resultado.corridas)} | {latencia_media} "
            f"| {aceptados}/{propuestos} | {ref_resolubles}/{ref_citadas} "
            f"| {tec_catalogo}/{tec_citadas} | {resultado.memoria_ollama_ps or 'sin datos'} |"
        )
    lineas.append("")
    lineas.append(
        "Numeradores y denominadores, no porcentajes de confianza inventados "
        "(ADR-0006). El detalle corrida por corrida está en "
        "`resultados-modelos.json`."
    )
    return "\n".join(lineas) + "\n"


def main() -> None:
    argumentos = parser_base(
        __doc__, RAIZ / "docs" / "benchmarks" / "resultados-modelos"
    ).parse_args()

    hardware = _info_hardware()
    resultados = [
        _correr_modelo(modelo, argumentos.repeticiones, argumentos.base_url)
        for modelo in argumentos.modelos
    ]

    catalogo_usado = cargar_catalogo()
    reporte = {
        "hardware": hardware,
        "caso": "caso sembrado (investigacion.sembrado.eventos_sembrados)",
        "repeticiones": argumentos.repeticiones,
        "catalogo": {
            "version": catalogo_usado.version,
            "procedencia": catalogo_usado.procedencia,
        },
        "modelos": [
            {"modelo": r.modelo, "memoria_ollama_ps": r.memoria_ollama_ps,
             "corridas": [asdict(c) for c in r.corridas]}
            for r in resultados
        ],
    }
    markdown = _resumen_markdown(hardware, resultados)
    escribir_reporte(argumentos.salida, reporte, markdown)
    print(markdown)


if __name__ == "__main__":
    main()
