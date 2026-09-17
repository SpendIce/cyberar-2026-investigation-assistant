"""Sello de integridad y cadena de custodia del estado de un caso.

Cada escritura del repositorio agrega una entrada cuyo sello encadena el sello
anterior con el sello del estado persistido (append-only). El sello de la
cabeza viaja en el informe exportado: una edición posterior del estado, una
entrada eliminada o una cadena reescrita se detectan al verificar el caso.

Límite declarado: la cadena vive en la misma base que custodia, por lo que la
garantía se ancla en el sello publicado con el informe —comparable a un
registro de hash forense, no a una firma—. Un manifiesto firmado con clave del
equipo es la evolución prevista del campo `firma`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from investigacion.modelos import Caso


@dataclass(frozen=True)
class EntradaCustodia:
    """Una escritura registrada en la cadena append-only del caso."""

    seq: int
    sello_estado: str
    sello_anterior: str | None
    sello: str


@dataclass(frozen=True)
class SelloCustodia:
    """El resumen de custodia que viaja en el informe exportado."""

    sello: str
    escrituras: int


@dataclass(frozen=True)
class VerificacionCustodia:
    """Resultado de verificar la cadena persistida contra el estado del caso."""

    integro: bool
    sello: str | None
    discrepancias: tuple[str, ...]


def sello_de_caso(caso: Caso) -> str:
    """SHA-256 sobre la serialización canónica del caso completo."""
    contenido = json.dumps(
        asdict(caso), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def encadenar(sello_anterior: str | None, sello_estado: str) -> str:
    """Sello de la entrada: el sello previo encadenado al sello del estado."""
    base = f"{sello_anterior or ''}:{sello_estado}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def sello_de_exportacion(contenido: str) -> str:
    """SHA-256 del contenido exportado, tal como se escribe en disco (UTF-8)."""
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def entrada_custodia(
    caso: Caso, seq: int, sello_anterior: str | None
) -> EntradaCustodia:
    """La entrada que una escritura del caso agrega a la cadena."""
    sello_estado = sello_de_caso(caso)
    return EntradaCustodia(
        seq=seq,
        sello_estado=sello_estado,
        sello_anterior=sello_anterior,
        sello=encadenar(sello_anterior, sello_estado),
    )


def verificar_cadena(
    cadena: tuple[EntradaCustodia, ...], caso: Caso
) -> tuple[str, ...]:
    """Discrepancias entre la cadena persistida y el estado leído del caso."""
    if not cadena:
        return ("el caso no registra cadena de custodia",)
    discrepancias: list[str] = []
    anterior: EntradaCustodia | None = None
    for esperado, entrada in enumerate(cadena, start=1):
        if entrada.seq != esperado:
            discrepancias.append(
                f"la cadena de custodia tiene una discontinuidad en seq {entrada.seq}"
            )
        referencia = anterior.sello if anterior is not None else None
        if entrada.sello_anterior != referencia:
            discrepancias.append(
                f"la entrada {entrada.seq} no encadena con la anterior"
            )
        if entrada.sello != encadenar(entrada.sello_anterior, entrada.sello_estado):
            discrepancias.append(
                f"el sello de la entrada {entrada.seq} no corresponde a su contenido"
            )
        anterior = entrada
    if cadena[-1].sello_estado != sello_de_caso(caso):
        discrepancias.append(
            "el estado persistido difiere del último sello registrado"
        )
    return tuple(discrepancias)
