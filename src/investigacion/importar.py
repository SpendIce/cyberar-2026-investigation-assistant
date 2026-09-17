"""CLI de importación EVTX, independiente de la demostración con dobles.

Con `--modelo` el mismo comando investiga el caso contra un endpoint Ollama:
importación, inferencia estructurada, validación y persistencia en un solo
recorrido sin adaptadores controlados (issue #6).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from investigacion.adaptadores.controlados import InferenciaNoDisponibleControlada
from investigacion.adaptadores.hayabusa import EvidenciaHayabusa
from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.adaptadores.respaldo import InferenciaConRespaldo
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.errores import ErrorDeImportacion
from investigacion.modelos import ModalidadInferencia, Origen
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.puertos import MotorDeInferencia


def main() -> None:
    parser = argparse.ArgumentParser(description="Importar un EVTX")
    parser.add_argument("--evtx", required=True, type=Path)
    parser.add_argument("--procedencia", required=True)
    parser.add_argument("--sha256", help="Hash esperado opcional para verificar procedencia")
    parser.add_argument("--hayabusa", required=True, type=Path, help="Ejecutable Hayabusa 4.1.0")
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--modelo", help="Modelo Ollama para investigar el caso importado")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument(
        "--modalidad",
        choices=[ModalidadInferencia.MODELO_LOCAL, ModalidadInferencia.NODO_PRIVADO],
        type=ModalidadInferencia,
        default=ModalidadInferencia.MODELO_LOCAL,
        help="Modalidad declarada del endpoint Ollama",
    )
    parser.add_argument(
        "--modelo-respaldo",
        help="Modelo local al que recurrir si el motor primario no está disponible",
    )
    parser.add_argument(
        "--ollama-url-respaldo", default="http://localhost:11434",
        help="Endpoint Ollama del modelo de respaldo",
    )
    parser.add_argument(
        "--permitir-externo",
        action="store_true",
        help="Permitir que la evidencia viaje a un endpoint fuera de la "
        "infraestructura controlada; la advertencia queda registrada en el caso",
    )
    parser.add_argument(
        "--host-controlado",
        action="append",
        default=[],
        metavar="HOST",
        help="Host adicional administrado por el equipo; repetible",
    )
    args = parser.parse_args()
    motor_inferencia: MotorDeInferencia
    if args.modelo:
        motor_inferencia = InferenciaOllama(
            args.modelo,
            base_url=args.ollama_url,
            modalidad=args.modalidad,
            permitir_externo=args.permitir_externo,
            hosts_controlados=frozenset(args.host_controlado),
        )
        if args.modelo_respaldo:
            motor_inferencia = InferenciaConRespaldo(
                motor_inferencia,
                InferenciaOllama(
                    args.modelo_respaldo,
                    base_url=args.ollama_url_respaldo,
                    modalidad=ModalidadInferencia.MODELO_LOCAL,
                    permitir_externo=args.permitir_externo,
                    hosts_controlados=frozenset(args.host_controlado),
                ),
            )
    else:
        motor_inferencia = InferenciaNoDisponibleControlada()
    modulo = ModuloDeInvestigacion(
        EvidenciaHayabusa(args.hayabusa, args.datos / "evidencia"),
        motor_inferencia, RepositorioSQLite(args.datos / "casos.sqlite"),
    )
    try:
        caso = modulo.crear_caso(Origen(str(args.evtx), args.procedencia, sha256=args.sha256))
    except ErrorDeImportacion as exc:
        parser.exit(1, f"Error de importación: {exc}\n")
    if args.modelo:
        caso = modulo.investigar_caso(caso.id)
    modalidad = (
        caso.modalidad_inferencia.value
        if caso.modalidad_inferencia
        else "no intentada"
    )
    print(json.dumps({
        "caso_id": caso.id, "eventos": len(caso.eventos),
        "hallazgos": len(caso.hallazgos), "modalidad_inferencia": modalidad,
        "errores": list(caso.errores),
        "sha256": caso.origen.sha256, "original_conservado": caso.origen.ruta,
        "sqlite": str((args.datos / "casos.sqlite").resolve()),
        "alcance": "Registros detectados por Hayabusa; no es todo el EVTX.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
