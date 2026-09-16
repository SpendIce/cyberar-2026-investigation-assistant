"""Descarga explícita del único fixture público fijado, con verificación SHA-256."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


def main() -> None:
    carpeta = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "publico"
    manifiesto = json.loads((carpeta / "manifest.json").read_text(encoding="utf-8"))
    destino = carpeta / manifiesto["archivo"]
    if destino.exists():
        contenido = destino.read_bytes()
    else:
        with urlopen(manifiesto["url"], timeout=60) as respuesta:
            contenido = respuesta.read(manifiesto["bytes"] + 1)
    if len(contenido) != manifiesto["bytes"] or hashlib.sha256(contenido).hexdigest() != manifiesto["sha256"]:
        raise SystemExit("Fixture diferente del manifiesto: no se guarda ni se utiliza.")
    if not destino.exists():
        with destino.open("xb") as archivo:
            archivo.write(contenido)
    print(f"Fixture verificado: {destino} ({len(contenido)} bytes)")


if __name__ == "__main__":
    main()
