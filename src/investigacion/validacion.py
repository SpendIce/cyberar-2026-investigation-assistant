"""Validación determinista de referencias de un hallazgo."""

from __future__ import annotations

import re

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
    "ataque confirmado",
    "actividad maliciosa confirmada",
    "intrusión confirmada",
    "compromiso confirmado",
    "malware confirmado",
)

_VERBOS_CONCLUSIVOS = (
    "se encuentra", "se encuentran", "ha sido", "han sido",
    "está", "están", "estuvo", "estuvieron", "fue", "fueron",
    "era", "eran", "quedó", "quedaron", "resultó", "resultaron",
    "permanece", "permanecen", "sigue", "siguen",
)

_SUJETOS_COMPROMISO = (
    "equipo", "equipos", "sistema", "sistemas", "host", "hosts",
    "servidor", "servidores", "máquina", "máquinas",
    "cuenta", "cuentas", "red", "entorno", "entornos",
)

_COMPROMISO_AFIRMATIVO = re.compile(
    r"(?:\b(?:"
    + "|".join(_VERBOS_CONCLUSIVOS)
    + r")\s+comprometid[oa]s?\b)"
    + r"|(?:\b(?:"
    + "|".join(_SUJETOS_COMPROMISO)
    + r")\s+comprometid[oa]s?\b(?!\s+(?:a|con|en|para)\b))"
)

_NEGADORES = frozenset(
    {"no", "nunca", "jamás", "tampoco", "sin", "ningún", "ninguna", "ninguno"}
)


def negado_en(normalizado: str, inicio: int) -> bool:
    """Detecta la negación inmediata antes de una formulación, en texto ya normalizado."""
    palabras = re.findall(r"[a-záéíóúñü]+", normalizado[:inicio])
    return bool(palabras) and palabras[-1] in _NEGADORES


def contiene_lenguaje_concluyente(texto: str) -> bool:
    """Detecta afirmaciones concluyentes no negadas en texto libre.

    Es una lista corta de formulaciones prohibidas, no un clasificador. La
    guarda de negación cubre la forma directa ("no está comprometido") y las
    formulaciones inciertas en subjuntivo ("esté comprometido") no coinciden
    con las afirmativas; una reformulación equivalente puede evadirla igual.
    """
    normalizado = texto.casefold()
    for frase in _AFIRMACIONES_CONCLUYENTES:
        inicio = normalizado.find(frase)
        while inicio >= 0:
            if not negado_en(normalizado, inicio):
                return True
            inicio = normalizado.find(frase, inicio + 1)
    return any(
        not negado_en(normalizado, coincidencia.start())
        for coincidencia in _COMPROMISO_AFIRMATIVO.finditer(normalizado)
    )


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
