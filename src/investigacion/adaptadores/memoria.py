"""Repositorio en memoria para pruebas rápidas y deterministas."""

from __future__ import annotations

from investigacion.custodia import EntradaCustodia, entrada_custodia
from investigacion.modelos import Caso


class RepositorioEnMemoria:
    def __init__(self) -> None:
        self._casos: dict[str, Caso] = {}
        self._custodia: dict[str, list[EntradaCustodia]] = {}

    def guardar(self, caso: Caso) -> None:
        self._casos[caso.id] = caso
        cadena = self._custodia.setdefault(caso.id, [])
        anterior = cadena[-1].sello if cadena else None
        cadena.append(entrada_custodia(caso, len(cadena) + 1, anterior))

    def obtener(self, caso_id: str) -> Caso | None:
        return self._casos.get(caso_id)

    def listar(self) -> tuple[str, ...]:
        return tuple(sorted(self._casos))

    def cadena_custodia(self, caso_id: str) -> tuple[EntradaCustodia, ...]:
        return tuple(self._custodia.get(caso_id, ()))
