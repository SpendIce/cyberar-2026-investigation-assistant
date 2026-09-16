"""CLI de importación EVTX, independiente de la demostración con dobles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from investigacion.adaptadores.controlados import InferenciaNoDisponibleControlada
from investigacion.adaptadores.hayabusa import EvidenciaHayabusa
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.errores import ErrorDeImportacion
from investigacion.modelos import Origen
from investigacion.modulo import ModuloDeInvestigacion


def main() -> None:
    parser = argparse.ArgumentParser(description="Importar un EVTX sin inferencia")
    parser.add_argument("--evtx", required=True, type=Path)
    parser.add_argument("--procedencia", required=True)
    parser.add_argument("--sha256", help="Hash esperado opcional para verificar procedencia")
    parser.add_argument("--hayabusa", required=True, type=Path, help="Ejecutable Hayabusa 4.1.0")
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    args = parser.parse_args()
    modulo = ModuloDeInvestigacion(
        EvidenciaHayabusa(args.hayabusa, args.datos / "evidencia"),
        InferenciaNoDisponibleControlada(), RepositorioSQLite(args.datos / "casos.sqlite"),
    )
    try:
        caso = modulo.crear_caso(Origen(str(args.evtx), args.procedencia, sha256=args.sha256))
    except ErrorDeImportacion as exc:
        parser.exit(1, f"Error de importación: {exc}\n")
    print(json.dumps({
        "caso_id": caso.id, "eventos": len(caso.eventos),
        "sha256": caso.origen.sha256, "original_conservado": caso.origen.ruta,
        "sqlite": str((args.datos / "casos.sqlite").resolve()),
        "alcance": "Registros detectados por Hayabusa; no es todo el EVTX. Sin inferencia.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
