"""Validación determinista de referencias de un hallazgo."""

from __future__ import annotations

from investigacion.errores import HallazgoInvalido
from investigacion.modelos import (
    EstadoRevision,
    Evento,
    Hallazgo,
    ProcedenciaMapeo,
    PropuestaHallazgo,
)


class ValidadorDeReferencias:
    """Acepta un hallazgo sólo si cada referencia apunta a un evento existente."""

    def __init__(self, procedencia_mapeo: ProcedenciaMapeo = ProcedenciaMapeo.MODELO) -> None:
        self._procedencia_mapeo = procedencia_mapeo

    def validar(
        self, caso_id: str, propuesta: PropuestaHallazgo, eventos: tuple[Evento, ...]
    ) -> Hallazgo:
        existentes = {evento.uid for evento in eventos}
        faltantes = [ref for ref in propuesta.referencias_eventos if ref not in existentes]
        if faltantes:
            raise HallazgoInvalido(
                f"referencias inexistentes: {', '.join(faltantes)}"
            )
        return Hallazgo(
            caso_id=caso_id,
            hipotesis=propuesta.hipotesis,
            referencias_eventos=propuesta.referencias_eventos,
            campos_citados=propuesta.campos_citados,
            tecnicas_candidatas=propuesta.tecnicas_candidatas,
            razon_vinculo=propuesta.razon_vinculo,
            procedencia_mapeo=self._procedencia_mapeo,
            explicaciones_alternativas=propuesta.explicaciones_alternativas,
            evidencia_faltante=propuesta.evidencia_faltante,
            limitaciones=propuesta.limitaciones,
            estado_revision=EstadoRevision.PENDIENTE,
        )
