"""Prepara en un mismo SQLite los escenarios sospechoso y legítimo de #8.

El caso sospechoso debe existir previamente y provenir del tracer real de #6.
Este comando agrega el control sintético/documentado, lo investiga con el
modelo local y genera sólo metadatos de presentación. Nunca carga la verdad de
referencia de ``docs/evaluacion``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from investigacion.adaptadores.controlados import EvidenciaControlada
from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.escenarios import (
    ARCHIVO_COMPARACION,
    ESCENARIO_LEGITIMO,
    ESCENARIO_SOSPECHOSO,
    EscenarioComparacion,
    eventos_control_legitimo,
    guardar_comparacion,
    origen_control_legitimo,
)
from investigacion.modulo import ModuloDeInvestigacion

ID_CONTROL = "control-legitimo-documentado"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--caso-sospechoso", required=True)
    parser.add_argument("--modelo", default="qwen2.5:7b-instruct")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    args = parser.parse_args()

    repositorio = RepositorioSQLite(args.datos / "casos.sqlite")
    sospechoso = repositorio.obtener(args.caso_sospechoso)
    if sospechoso is None:
        parser.error(f"caso sospechoso inexistente: {args.caso_sospechoso}")
    if sospechoso.origen.versiones.get("hayabusa") != "4.1.0":
        parser.error(
            "el caso sospechoso debe provenir del tracer real con Hayabusa 4.1.0"
        )
    if not sospechoso.origen.sha256 or not sospechoso.eventos:
        parser.error("el caso sospechoso no conserva hash y eventos verificables")

    origen = origen_control_legitimo()
    modulo = ModuloDeInvestigacion(
        EvidenciaControlada(
            eventos_control_legitimo(),
            sha256=origen.sha256 or "",
            nombre=origen.nombre or "control-legitimo-sintetico",
            versiones=origen.versiones,
        ),
        InferenciaOllama(args.modelo, base_url=args.ollama_url),
        repositorio,
        generador_de_ids=lambda: ID_CONTROL,
    )
    control = modulo.investigar_caso(modulo.crear_caso(origen).id)

    guardar_comparacion(
        args.datos / ARCHIVO_COMPARACION,
        (
            EscenarioComparacion(
                scenario_id=ESCENARIO_SOSPECHOSO,
                caso_id=sospechoso.id,
                titulo="Escenario A — actividad PsExec/PowerShell a investigar",
                descripcion=(
                    "EVTX público real procesado por Hayabusa. Las detecciones y "
                    "las hipótesis no constituyen un veredicto de compromiso."
                ),
                tipo_evidencia="EVTX público real",
            ),
            EscenarioComparacion(
                scenario_id=ESCENARIO_LEGITIMO,
                caso_id=control.id,
                titulo="Escenario B — operación administrativa documentada",
                descripcion=(
                    "Control sintético/documentado con PsExec, PowerShell y SMB. "
                    "No es una captura EVTX real; esa validación queda pendiente."
                ),
                tipo_evidencia="control sintético/documentado",
            ),
        ),
    )
    print(
        f"Comparación preparada: {sospechoso.id} / {control.id}; "
        f"control con {len(control.hallazgos)} hallazgos, "
        f"modalidad={control.modalidad_inferencia}"
    )


if __name__ == "__main__":
    main()
