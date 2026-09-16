"""Motor de inferencia compuesto con respaldo ordenado (ADR-0011).

Prueba cada motor en orden: el primario (por ejemplo el nodo privado) y, si
declara `InferenciaNoDisponible`, el siguiente (el modelo local reducido). La
modalidad expuesta corresponde al último motor que produjo una respuesta; si
ninguno responde, la inferencia se declara no disponible y el módulo persiste
el modo degradado sin fingir conclusiones.
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
        self._ultimo_exitoso = motores[0]

    @property
    def modalidad(self) -> ModalidadInferencia:
        return self._ultimo_exitoso.modalidad

    def proponer(
        self, caso_id: str, evidencia: tuple[Evento, ...]
    ) -> tuple[PropuestaHallazgo, ...]:
        errores = []
        for motor in self._motores:
            try:
                propuestas = motor.proponer(caso_id, evidencia)
            except InferenciaNoDisponible as exc:
                errores.append(str(exc))
                continue
            self._ultimo_exitoso = motor
            return propuestas
        raise InferenciaNoDisponible("; ".join(errores))
