"""Pre-procesa una lista de EVTX contra el endpoint externo opencode Zen.

Uso offline para poblar la galería de la demo: importa cada EVTX con Hayabusa
y lo investiga con `InferenciaZen`, persistiendo en `--datos`. La modalidad
`modelo_externo` y la advertencia de soberanía quedan declaradas en cada caso.

El manifiesto es JSON: una lista de objetos con `evtx` (ruta), `procedencia`
y opcionalmente `nombre`, `contexto` y `solo_hayabusa` (true importa sin
inferir, para mostrar el modo degradado).

    OPENCODE_API_KEY=... python scripts/preprocesar_zen.py \
        --manifiesto seleccion.json --hayabusa ~/tools/hayabusa-4.1.0/hayabusa-4.1.0-lin-x64-musl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from investigacion.adaptadores.hayabusa import EvidenciaHayabusa
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.adaptadores.zen import InferenciaZen
from investigacion.errores import ErrorDeImportacion, InferenciaNoDisponible
from investigacion.modelos import Origen
from investigacion.modulo import ModuloDeInvestigacion


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-procesar EVTX con Zen")
    parser.add_argument("--manifiesto", required=True, type=Path)
    parser.add_argument("--hayabusa", required=True, type=Path)
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--modelo", default="deepseek-v4-flash")
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    entradas = json.loads(args.manifiesto.read_text(encoding="utf-8"))
    if not isinstance(entradas, list):
        parser.exit(1, "el manifiesto debe ser una lista de casos")

    repositorio = RepositorioSQLite(args.datos / "casos.sqlite")
    motor_inferencia = InferenciaZen(
        args.modelo,
        permitir_externo=True,
        timeout=args.timeout,
    )
    modulo = ModuloDeInvestigacion(
        EvidenciaHayabusa(args.hayabusa, args.datos / "evidencia"),
        motor_inferencia,
        repositorio,
    )

    resumen = []
    for entrada in entradas:
        evtx = Path(entrada["evtx"]).resolve()
        nombre = entrada.get("nombre") or evtx.stem
        solo_hayabusa = bool(entrada.get("solo_hayabusa"))
        registro = {"evtx": str(evtx), "nombre": nombre}
        try:
            caso = modulo.crear_caso(
                Origen(
                    ruta=str(evtx),
                    procedencia=entrada["procedencia"],
                    nombre=nombre,
                ),
                contexto=entrada.get("contexto", ""),
            )
            registro["caso_id"] = caso.id
            registro["eventos"] = len(caso.eventos)
            if solo_hayabusa:
                registro["modalidad"] = "sin inferencia (hayabusa solo)"
            else:
                caso = modulo.investigar_caso(caso.id)
                registro["hallazgos"] = len(caso.hallazgos)
                registro["modalidad"] = (
                    caso.modalidad_inferencia.value
                    if caso.modalidad_inferencia
                    else "no intentada"
                )
                registro["errores"] = list(caso.errores)
        except (ErrorDeImportacion, InferenciaNoDisponible, OSError) as exc:
            registro["error"] = str(exc)
        resumen.append(registro)
        print(json.dumps(registro, ensure_ascii=False), flush=True)

    fallidos = [r for r in resumen if "error" in r]
    print(
        json.dumps(
            {"procesados": len(resumen) - len(fallidos), "fallidos": len(fallidos)},
            ensure_ascii=False,
        )
    )
    if fallidos:
        sys.exit(1)


if __name__ == "__main__":
    main()
