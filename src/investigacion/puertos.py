"""Costuras internas del módulo de investigación."""

from __future__ import annotations

from typing import Protocol

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
        """Motivos por los que un motor previo no se usó en la última llamada a `proponer`.

        Vacío si `proponer` no tuvo que recurrir a ningún respaldo (issue #7:
        la transición remoto → local → degradado debe ser observable, no sólo
        un cambio silencioso de modalidad).
        """
        ...

    def proponer(
        self, caso_id: str, evidencia: tuple[Evento, ...]
    ) -> tuple[PropuestaHallazgo, ...]: ...


class ValidadorDeHallazgos(Protocol):
    def validar(
        self, caso_id: str, propuesta: PropuestaHallazgo, eventos: tuple[Evento, ...]
    ) -> Hallazgo: ...


class RepositorioDeCasos(Protocol):
    def guardar(self, caso: Caso) -> None: ...

    def obtener(self, caso_id: str) -> Caso | None: ...
