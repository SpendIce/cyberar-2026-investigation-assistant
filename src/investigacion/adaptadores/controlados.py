"""Adaptadores controlados y deterministas para pruebas y demostración."""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from investigacion.errores import ErrorDeImportacion, InferenciaNoDisponible
from investigacion.modelos import (
    Evento,
    ModalidadInferencia,
    Origen,
    PropuestaHallazgo,
    ResultadoDeEvidencia,
)


class EvidenciaControlada:
    def __init__(
        self,
        eventos: tuple[Evento, ...] = (),
        *,
        sha256: str = "sha-controlado",
        nombre: str = "evidencia-controlada.evtx",
        versiones: Mapping[str, str] | None = None,
        fuentes_incompatibles: frozenset[str] = frozenset(),
    ) -> None:
        self._eventos = eventos
        self._sha256 = sha256
        self._nombre = nombre
        self._versiones = dict(versiones or {"hayabusa": "controlado"})
        self._fuentes_incompatibles = fuentes_incompatibles

    def analizar(self, caso_id: str, origen: Origen) -> ResultadoDeEvidencia:
        if origen.ruta in self._fuentes_incompatibles:
            raise ErrorDeImportacion(f"fuente incompatible: {origen.ruta}")
        return ResultadoDeEvidencia(
            origen=replace(
                origen,
                sha256=self._sha256,
                nombre=self._nombre,
                versiones=self._versiones,
            ),
            eventos=tuple(
                replace(evento, caso_id=caso_id, origen_sha256=self._sha256)
                for evento in self._eventos
            ),
        )


class InferenciaControlada:
    def __init__(
        self,
        propuestas: tuple[PropuestaHallazgo, ...] = (),
        *,
        modalidad: ModalidadInferencia = ModalidadInferencia.MODELO_LOCAL,
        falla: Exception | None = None,
    ) -> None:
        self._propuestas = propuestas
        self._modalidad = modalidad
        self._falla = falla

    @property
    def modalidad(self) -> ModalidadInferencia:
        return self._modalidad

    @property
    def advertencias(self) -> tuple[str, ...]:
        return ()

    def proponer(
        self, caso_id: str, evidencia: tuple[Evento, ...]
    ) -> tuple[PropuestaHallazgo, ...]:
        if self._falla is not None:
            raise self._falla
        return self._propuestas


class InferenciaNoDisponibleControlada(InferenciaControlada):
    def __init__(self, motivo: str = "sin inferencia disponible") -> None:
        super().__init__(modalidad=ModalidadInferencia.DEGRADADO, falla=InferenciaNoDisponible(motivo))
