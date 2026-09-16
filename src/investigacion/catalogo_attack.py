"""Catálogo local ATT&CK: subconjunto fijado con versión, fecha y procedencia.

El MVP limita las técnicas candidatas a este subconjunto local (ADR-0014),
distribuido como dato del paquete para que la ruta no dependa del árbol del
repositorio.
Validar que un identificador pertenece al catálogo no demuestra que la
técnica esté correctamente aplicada; esa pertinencia requiere evidencia y
revisión humana.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

RUTA_CATALOGO_DEFECTO = Path(__file__).resolve().parent / "datos" / "catalogo_attack.json"


@dataclass(frozen=True)
class Tecnica:
    id: str
    nombre: str


@dataclass(frozen=True)
class CatalogoAttack:
    version: str
    fecha: str
    procedencia: str
    tecnicas: Mapping[str, Tecnica]

    def contiene(self, id_tecnica: str) -> bool:
        return id_tecnica in self.tecnicas


def cargar_catalogo(ruta: Path = RUTA_CATALOGO_DEFECTO) -> CatalogoAttack:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    tecnicas = {
        tecnica["id"]: Tecnica(id=tecnica["id"], nombre=tecnica["nombre"])
        for tecnica in datos["tecnicas"]
    }
    return CatalogoAttack(
        version=datos["version"],
        fecha=datos["fecha"],
        procedencia=datos["procedencia"],
        tecnicas=tecnicas,
    )
