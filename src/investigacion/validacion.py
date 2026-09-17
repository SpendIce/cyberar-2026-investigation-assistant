"""Validación determinista de referencias de un hallazgo."""

from __future__ import annotations

from investigacion.catalogo_attack import CatalogoAttack, cargar_catalogo
from investigacion.errores import HallazgoInvalido
from investigacion.modelos import (
    EstadoRevision,
    Evento,
    Hallazgo,
    ProcedenciaMapeo,
    PropuestaHallazgo,
)


_AFIRMACIONES_CONCLUYENTES = (
    "comprometid",
    "ataque confirmado",
    "actividad maliciosa confirmada",
    "intrusión confirmada",
    "compromiso confirmado",
    "malware confirmado",
)


def contiene_lenguaje_concluyente(texto: str) -> bool:
    """Detecta las afirmaciones concluyentes prohibidas por el contrato del MVP."""
    normalizado = texto.casefold()
    return any(frase in normalizado for frase in _AFIRMACIONES_CONCLUYENTES)


def prosa_revisable(propuesta: PropuestaHallazgo | Hallazgo) -> str:
    """Todo el texto libre de una propuesta o hallazgo, para revisarlo junto."""
    return "\n".join(
        (
            propuesta.hipotesis,
            propuesta.razon_vinculo,
            *propuesta.explicaciones_alternativas,
            *propuesta.evidencia_faltante,
            *propuesta.limitaciones,
        )
    )


class ValidadorDeReferencias:
    """Acepta un hallazgo sólo si cada referencia y cada técnica existen."""

    def __init__(
        self,
        procedencia_mapeo: ProcedenciaMapeo = ProcedenciaMapeo.MODELO,
        catalogo: CatalogoAttack | None = None,
    ) -> None:
        self._procedencia_mapeo = procedencia_mapeo
        self._catalogo = catalogo if catalogo is not None else cargar_catalogo()

    def validar(
        self, caso_id: str, propuesta: PropuestaHallazgo, eventos: tuple[Evento, ...]
    ) -> Hallazgo:
        if contiene_lenguaje_concluyente(prosa_revisable(propuesta)):
            raise HallazgoInvalido(
                "lenguaje concluyente incompatible con una hipótesis revisable"
            )
        existentes = {evento.uid for evento in eventos}
        faltantes = [ref for ref in propuesta.referencias_eventos if ref not in existentes]
        if faltantes:
            raise HallazgoInvalido(
                f"referencias inexistentes: {', '.join(faltantes)}"
            )
        fuera_de_catalogo = [
            tecnica
            for tecnica in propuesta.tecnicas_candidatas
            if not self._catalogo.contiene(tecnica)
        ]
        if fuera_de_catalogo:
            raise HallazgoInvalido(
                f"técnicas fuera del catálogo local ({self._catalogo.version}): "
                f"{', '.join(fuera_de_catalogo)}"
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
