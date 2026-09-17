"""Pruebas deterministas del motor compuesto con respaldo (ADR-0011)."""

from __future__ import annotations

import pytest

from investigacion.adaptadores.respaldo import InferenciaConRespaldo
from investigacion.errores import InferenciaNoDisponible
from investigacion.modelos import Evento, ModalidadInferencia, PropuestaHallazgo


class _MotorFalso:
    def __init__(
        self,
        modalidad: ModalidadInferencia,
        *,
        disponible: bool,
        mensaje: str = "caído",
    ) -> None:
        self._modalidad = modalidad
        self._disponible = disponible
        self._mensaje = mensaje
        self.llamadas = 0

    @property
    def modalidad(self) -> ModalidadInferencia:
        return self._modalidad

    @property
    def advertencias(self) -> tuple[str, ...]:
        return ()

    def proponer(
        self, caso_id: str, evidencia: tuple[Evento, ...], contexto: str = ""
    ) -> tuple[PropuestaHallazgo, ...]:
        self.llamadas += 1
        if not self._disponible:
            raise InferenciaNoDisponible(self._mensaje)
        return (
            PropuestaHallazgo(
                hipotesis="h", referencias_eventos=("ev-1",), razon_vinculo="v"
            ),
        )


def _evento(uid: str) -> Evento:
    return Evento(
        uid=uid, caso_id="caso-1", origen_sha256="sha", localizador_original=f"r-{uid}"
    )


def test_el_respaldo_responde_cuando_el_primario_no_esta_disponible() -> None:
    primario = _MotorFalso(ModalidadInferencia.NODO_PRIVADO, disponible=False)
    respaldo = _MotorFalso(ModalidadInferencia.MODELO_LOCAL, disponible=True)
    motor = InferenciaConRespaldo(primario, respaldo)

    propuestas = motor.proponer("caso-1", (_evento("ev-1"),))

    assert len(propuestas) == 1
    assert primario.llamadas == 1
    assert respaldo.llamadas == 1
    assert motor.modalidad is ModalidadInferencia.MODELO_LOCAL


def test_la_modalidad_es_la_del_primario_cuando_responde() -> None:
    primario = _MotorFalso(ModalidadInferencia.NODO_PRIVADO, disponible=True)
    respaldo = _MotorFalso(ModalidadInferencia.MODELO_LOCAL, disponible=True)
    motor = InferenciaConRespaldo(primario, respaldo)

    propuestas = motor.proponer("caso-1", (_evento("ev-1"),))

    assert len(propuestas) == 1
    assert respaldo.llamadas == 0
    assert motor.modalidad is ModalidadInferencia.NODO_PRIVADO


def test_sin_motor_disponible_la_inferencia_reporta_ambos_errores() -> None:
    motor = InferenciaConRespaldo(
        _MotorFalso(ModalidadInferencia.NODO_PRIVADO, disponible=False, mensaje="nodo caído"),
        _MotorFalso(ModalidadInferencia.MODELO_LOCAL, disponible=False, mensaje="local ausente"),
    )

    with pytest.raises(InferenciaNoDisponible, match="nodo caído.*local ausente"):
        motor.proponer("caso-1", (_evento("ev-1"),))

    assert motor.advertencias == (
        "nodo_privado no disponible: nodo caído",
        "modelo_local no disponible: local ausente",
    )
    assert motor.modalidad is ModalidadInferencia.DEGRADADO


def test_un_fallo_inesperado_no_deja_advertencias_de_la_llamada_anterior() -> None:
    class _MotorQueRompe:
        @property
        def modalidad(self) -> ModalidadInferencia:
            return ModalidadInferencia.NODO_PRIVADO

        @property
        def advertencias(self) -> tuple[str, ...]:
            return ()

        def proponer(
            self, caso_id: str, evidencia: tuple[Evento, ...], contexto: str = ""
        ) -> tuple[PropuestaHallazgo, ...]:
            raise ValueError("defecto de programación, no indisponibilidad")

    primario = _MotorFalso(ModalidadInferencia.NODO_PRIVADO, disponible=False, mensaje="nodo caído")
    motor = InferenciaConRespaldo(
        primario, _MotorFalso(ModalidadInferencia.MODELO_LOCAL, disponible=True)
    )
    motor.proponer("caso-1", (_evento("ev-1"),))
    assert motor.advertencias == ("nodo_privado no disponible: nodo caído",)

    # Un error que no es InferenciaNoDisponible se propaga: no debe quedar
    # como advertencia de esta llamada ni conservar la de la anterior.
    roto = InferenciaConRespaldo(_MotorQueRompe())
    with pytest.raises(ValueError):
        roto.proponer("caso-1", (_evento("ev-1"),))

    assert roto.advertencias == ()
    assert roto.modalidad is ModalidadInferencia.DEGRADADO
