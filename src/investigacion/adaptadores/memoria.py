"""Repositorio en memoria para pruebas rápidas y deterministas."""

from __future__ import annotations

from investigacion.modelos import Caso


class RepositorioEnMemoria:
    def __init__(self) -> None:
        self._casos: dict[str, Caso] = {}

    def guardar(self, caso: Caso) -> None:
        self._casos[caso.id] = caso

    def obtener(self, caso_id: str) -> Caso | None:
        return self._casos.get(caso_id)
