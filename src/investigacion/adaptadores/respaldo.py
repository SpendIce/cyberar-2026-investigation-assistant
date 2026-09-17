"""Motor de inferencia compuesto con respaldo ordenado (ADR-0011).

Prueba cada motor en orden: el primario (por ejemplo el nodo privado) y, si
declara `InferenciaNoDisponible`, el siguiente (el modelo local reducido). La
modalidad expuesta corresponde al último motor que produjo una respuesta, o a
`degradado` cuando la última llamada no produjo ninguna; si ningún motor
responde, la inferencia se declara no disponible y el módulo persiste el modo
degradado sin fingir conclusiones.
"""

from __future__ import annotations

from investigacion.errores import InferenciaNoDisponible
from investigacion.modelos import Evento, ModalidadInferencia, PropuestaHallazgo
from investigacion.puertos import MotorDeInferencia


class InferenciaConRespaldo:
    """Implementa `MotorDeInferencia` delegando en motores ordenados."""

    def __init__(self, *motores: MotorDeInferencia) -> None:
        if not motores:
            raise ValueError("se requiere al menos un motor de inferencia")
        self._motores = motores
        self._ultimo_exitoso: MotorDeInferencia | None = None
        self._advertencias: tuple[str, ...] = ()

    @property
    def modalidad(self) -> ModalidadInferencia:
        if self._ultimo_exitoso is None:
            return ModalidadInferencia.DEGRADADO
        return self._ultimo_exitoso.modalidad

    @property
    def advertencias(self) -> tuple[str, ...]:
        return self._advertencias

    def proponer(
        self, caso_id: str, evidencia: tuple[Evento, ...]
    ) -> tuple[PropuestaHallazgo, ...]:
        errores = []
        for motor in self._motores:
            try:
                propuestas = motor.proponer(caso_id, evidencia)
            except InferenciaNoDisponible as exc:
                errores.append(f"{motor.modalidad.value} no disponible: {exc}")
                continue
            self._ultimo_exitoso = motor
            self._advertencias = tuple(errores)
            return propuestas
        self._ultimo_exitoso = None
        self._advertencias = tuple(errores)
        raise InferenciaNoDisponible("; ".join(errores))
