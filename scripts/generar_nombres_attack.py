"""Genera el mapa id→nombre ATT&CK para display, desde el STIX oficial.

Descarga `enterprise-attack.json` del repositorio mitre-attack/attack-stix-data
y produce el asset que la interfaz usa para mostrar nombres legibles en los
chips de técnicas. Las sub-técnicas se formatean "Padre: Sub-técnica", la
misma convención del catálogo validado.

    curl -sL -o /tmp/enterprise-attack.json \
        https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json
    python scripts/generar_nombres_attack.py \
        --stix /tmp/enterprise-attack.json \
        --salida src/investigacion/datos/nombres_attack.json

Este archivo es sólo display: no amplía el catálogo validado
(`catalogo_attack.json`), que sigue siendo el subconjunto deliberado que el
validador acepta (ADR-0014).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _external_id(obj: dict[str, Any]) -> str | None:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            external_id = ref.get("external_id")
            return str(external_id) if external_id is not None else None
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stix", required=True, type=Path)
    parser.add_argument("--salida", required=True, type=Path)
    args = parser.parse_args()

    datos = json.loads(args.stix.read_text(encoding="utf-8"))
    nombres: dict[str, str] = {}
    for obj in datos.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        identificador = _external_id(obj)
        if identificador:
            nombres[identificador] = str(obj["name"])

    display: dict[str, str] = {}
    for identificador, nombre in sorted(nombres.items()):
        padre = (
            nombres.get(identificador.split(".")[0])
            if "." in identificador
            else None
        )
        display[identificador] = f"{padre}: {nombre}" if padre else nombre

    salida = {
        "procedencia": (
            "nombres extraídos de mitre-attack/attack-stix-data "
            "(enterprise-attack.json); sub-técnicas como 'Padre: Sub'"
        ),
        "nombres": display,
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(display)} técnicas con nombre -> {args.salida}")


if __name__ == "__main__":
    main()
