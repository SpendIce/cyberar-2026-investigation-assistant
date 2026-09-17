"""CLI de informe: exporta un caso persistido a Markdown o JSON.

Lee exclusivamente el estado validado en `casos.sqlite`; los motores de
evidencia e inferencia quedan fuera del recorrido, por lo que exportar nunca
vuelve a ejecutar el modelo (issue #10).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from investigacion.adaptadores.controlados import (
    EvidenciaControlada,
    InferenciaNoDisponibleControlada,
)
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.errores import CasoNoEncontrado
from investigacion.modelos import FormatoExportacion
from investigacion.modulo import ModuloDeInvestigacion


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exportar el informe reproducible de un caso persistido"
    )
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument(
        "--caso",
        help="Identificador del caso; obligatorio si el repositorio tiene varios",
    )
    parser.add_argument(
        "--formato",
        choices=tuple(FormatoExportacion),
        type=FormatoExportacion,
        default=FormatoExportacion.MARKDOWN,
    )
    parser.add_argument(
        "--salida",
        type=Path,
        help="Archivo de destino; sin él el informe sale por stdout",
    )
    args = parser.parse_args()

    repositorio = RepositorioSQLite(args.datos / "casos.sqlite")
    modulo = ModuloDeInvestigacion(
        EvidenciaControlada(), InferenciaNoDisponibleControlada(), repositorio
    )

    caso_id = args.caso
    if caso_id is None:
        identificadores = repositorio.listar()
        if not identificadores:
            parser.exit(1, "Sin casos persistidos; importar un EVTX primero.\n")
        if len(identificadores) > 1:
            parser.exit(
                1,
                "Varios casos persistidos; indicar --caso con uno de: "
                + ", ".join(identificadores)
                + "\n",
            )
        caso_id = identificadores[0]

    try:
        contenido = modulo.exportar_caso(caso_id, args.formato)
    except CasoNoEncontrado:
        parser.exit(1, f"Caso inexistente: {caso_id}\n")

    if args.salida is None:
        sys.stdout.write(contenido)
        return
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(contenido, encoding="utf-8")
    print(str(args.salida))


if __name__ == "__main__":
    main()
