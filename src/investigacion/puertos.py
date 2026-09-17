"""Costuras internas del módulo de investigación."""

from __future__ import annotations

from typing import Protocol

from investigacion.custodia import EntradaCustodia
from investigacion.modelos import (
    Caso,
    Evento,
    Hallazgo,
    ModalidadInferencia,
    Origen,
    PropuestaHallazgo,
    ResultadoDeEvidencia,
)


class MotorDeEvidencia(Protocol):
    def analizar(self, caso_id: str, origen: Origen) -> ResultadoDeEvidencia: ...


class MotorDeInferencia(Protocol):
    @property
    def modalidad(self) -> ModalidadInferencia: ...

    @property
    def advertencias(self) -> tuple[str, ...]:
        """Advertencias de la última llamada a `proponer`.

        Motivos por los que un motor previo no se usó (issue #7: la transición
        remoto → local → degradado debe ser observable) y advertencias del
        motor que respondió (por ejemplo, evidencia enviada a un endpoint
        externo declarado). Vacío si no hubo respaldo ni advertencias.
        """
        ...

    def proponer(
        self, caso_id: str, evidencia: tuple[Evento, ...], contexto: str = ""
    ) -> tuple[PropuestaHallazgo, ...]: ...


class ValidadorDeHallazgos(Protocol):
    def validar(
        self, caso_id: str, propuesta: PropuestaHallazgo, eventos: tuple[Evento, ...]
    ) -> Hallazgo: ...


class RepositorioDeCasos(Protocol):
    def guardar(self, caso: Caso) -> None: ...

    def obtener(self, caso_id: str) -> Caso | None: ...

    def listar(self) -> tuple[str, ...]:
        """Los identificadores de los casos persistidos, en orden estable."""
        ...

    def cadena_custodia(self, caso_id: str) -> tuple[EntradaCustodia, ...]:
        """Las entradas append-only registradas por cada `guardar` del caso."""
        ...

    def eliminar(self, caso_id: str) -> None:
        """Borra el caso y su cadena de custodia. La baja es una decisión del
        operador y desaparece con el caso; no se representa como escritura."""
        ...
