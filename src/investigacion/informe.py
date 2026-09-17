"""CLI de informe: exporta un caso persistido a Markdown o JSON.

Lee exclusivamente el estado validado en `casos.sqlite`; los motores de
evidencia e inferencia quedan fuera del recorrido, por lo que exportar nunca
vuelve a ejecutar el modelo (issue #10).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from investigacion.adaptadores.controlados import (
    EvidenciaControlada,
    InferenciaNoDisponibleControlada,
)
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.custodia import sello_de_exportacion
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
    parser.add_argument(
        "--verificar",
        type=Path,
        metavar="INFORME",
        help="Verificar un informe exportado contra su archivo .sha256",
    )
    args = parser.parse_args()

    if args.verificar is not None:
        parser.exit(_verificar_informe(args.verificar))

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
    if args.salida.resolve() == repositorio.ruta:
        parser.exit(1, "La salida no puede sobrescribir casos.sqlite.\n")
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(contenido, encoding="utf-8")
    lado = args.salida.with_name(args.salida.name + ".sha256")
    lado.write_text(
        f"{sello_de_exportacion(contenido)}  {args.salida.name}\n",
        encoding="utf-8",
    )
    print(str(args.salida))


def _verificar_informe(ruta: Path) -> int:
    """Compara el SHA-256 del informe con el declarado en su `.sha256`."""
    lado = ruta.with_name(ruta.name + ".sha256")
    try:
        declarado = lado.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(ruta.read_bytes()).hexdigest()
    except (OSError, IndexError) as exc:
        sys.stderr.write(f"No se pudo verificar el informe: {exc}\n")
        return 1
    if actual != declarado:
        sys.stderr.write(f"El informe fue alterado: {ruta}\n")
        return 1
    print(f"Informe íntegro: {ruta}")
    return 0


if __name__ == "__main__":
    main()
