"""Genera el mapa táctica→técnica ATT&CK desde las reglas Sigma del release.

Recorre los .yml del directorio de reglas de Hayabusa fijado y, para cada
técnica `attack.tXXXX` etiquetada, registra las tácticas `attack.<tactica>`
de la misma regla. El resultado es el asset de display de la matriz de
cobertura: qué técnicas tiene al menos una regla en el motor fijado.

    python scripts/generar_mapa_attack.py \
        --reglas ~/tools/hayabusa-4.1.0/rules \
        --salida src/investigacion/datos/mapa_attack.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_TAG = re.compile(r"attack\.(t\d{4}(?:\.\d{3})?|[a-z_-]+)", re.IGNORECASE)

_TACTICAS = frozenset(
    {
        "reconnaissance",
        "resource_development",
        "initial_access",
        "execution",
        "persistence",
        "privilege_escalation",
        "defense_evasion",
        "credential_access",
        "discovery",
        "lateral_movement",
        "collection",
        "command_and_control",
        "exfiltration",
        "impact",
    }
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reglas", required=True, type=Path)
    parser.add_argument("--salida", required=True, type=Path)
    args = parser.parse_args()

    mapa: dict[str, set[str]] = {}
    reglas = 0
    for archivo in sorted(args.reglas.rglob("*.yml")):
        texto = archivo.read_text(encoding="utf-8", errors="replace")
        tags = {m.lower() for m in _TAG.findall(texto)}
        tecnicas = {t.upper() for t in tags if re.fullmatch(r"T\d{4}(\.\d{3})?", t.upper())}
        tacticas = {t.replace("-", "_") for t in tags} & _TACTICAS
        if not tecnicas:
            continue
        reglas += 1
        for tecnica in tecnicas:
            mapa.setdefault(tecnica, set()).update(tacticas)

    salida = {
        "procedencia": "tags attack.t* y attack.<tactica> de las reglas del release fijado",
        "tecnicas": {
            tecnica: sorted(tacticas) for tecnica, tacticas in sorted(mapa.items())
        },
        "reglas_con_tags_attack": reglas,
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(mapa)} técnicas mapeadas desde {reglas} reglas -> {args.salida}")


if __name__ == "__main__":
    main()
