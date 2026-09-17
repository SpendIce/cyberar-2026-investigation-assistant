"""Puntuación determinista de la comparación de enfoques (issue #11).

La verdad de referencia vive fuera del paquete, en
``docs/evaluacion/verdad-referencia-escenarios.json``: este módulo sólo la
consume como criterio mecánico de puntuación sobre la salida de cada
enfoque (Hayabusa solo, LLM directo y pipeline completo). Nunca llega al
prompt ni al caso. Todas las medidas se expresan como numeradores y
denominadores; ninguna es un porcentaje de confianza.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from investigacion.modelos import Evento
from investigacion.validacion import contiene_lenguaje_concluyente, negado_en

ENFOQUE_HAYABUSA = "hayabusa"
ENFOQUE_LLM_DIRECTO = "llm_directo"
ENFOQUE_PIPELINE = "pipeline"
ENFOQUES = (ENFOQUE_HAYABUSA, ENFOQUE_LLM_DIRECTO, ENFOQUE_PIPELINE)


@dataclass(frozen=True)
class EvidenciaEsperada:
    """Un ítem de evidencia esencial con criterios mecánicos de cobertura.

    ``campo``+``contiene`` se verifican contra los eventos que el enfoque
    pone sobre la mesa; ``en_texto`` contra la prosa que produce. Cualquiera
    de las alternativas basta (subcadena, sin distinción de mayúsculas).
    """

    item: str
    campo: str | None
    contiene: tuple[str, ...]
    en_texto: tuple[str, ...]


@dataclass(frozen=True)
class VerdadEscenario:
    escenario_id: str
    contexto_esperado: str
    evidencia_esperada: tuple[EvidenciaEsperada, ...]
    tecnicas_respaldadas: tuple[str, ...]
    conclusiones_prohibidas: tuple[str, ...]
    fundamento: str = ""
    procedencia: str = ""


@dataclass(frozen=True)
class ReferenciaCitada:
    """Una mención a evidencia dentro de la salida de un enfoque."""

    mencion: str
    resoluble: bool
    uid_resuelto: str | None = None


@dataclass(frozen=True)
class Afirmacion:
    """Una afirmación evaluable: hipótesis, detección, técnica o veredicto."""

    texto: str
    referencias: tuple[ReferenciaCitada, ...]
    tecnicas: tuple[str, ...]
    bloqueada: bool = False  # True: el pipeline la rechazó; no es salida visible


@dataclass(frozen=True)
class SalidaEnfoque:
    """La salida de un enfoque sobre un caso y una corrida concretos."""

    enfoque: str
    escenario_id: str
    corrida: int
    eventos_superficie: tuple[Evento, ...]
    texto: str
    afirmaciones: tuple[Afirmacion, ...]
    referencias: tuple[ReferenciaCitada, ...]
    tecnicas: tuple[str, ...]
    latencia_segundos: float | None = None
    memoria: str | None = None
    inferencia_disponible: bool = True
    obedecio_instruccion: bool | None = None
    persistio_inventado: bool | None = None


@dataclass(frozen=True)
class Puntuacion:
    esperados: int
    aciertos: int
    omisiones: int
    referencias_generadas: int
    referencias_invalidas: int
    tecnicas_sugeridas: int
    tecnicas_respaldadas: int
    afirmaciones_revisadas: int
    falsas_afirmaciones: int
    afirmaciones_bloqueadas: int


def cargar_verdad(ruta: Path) -> dict[str, VerdadEscenario]:
    """Carga la verdad de referencia con sus criterios mecánicos."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    escenarios: dict[str, VerdadEscenario] = {}
    for item in datos.get("escenarios", []):
        esperadas = tuple(
            EvidenciaEsperada(
                item=espera["item"],
                campo=espera.get("campo"),
                contiene=tuple(espera.get("contiene", ())),
                en_texto=(
                    tuple(espera["en_texto"])
                    if "en_texto" in espera
                    else tuple(espera.get("contiene", ()))
                ),
            )
            for espera in item.get("evidencia_esperada", [])
        )
        verdad = VerdadEscenario(
            escenario_id=item["escenario_id"],
            contexto_esperado=item["contexto_esperado"],
            evidencia_esperada=esperadas,
            tecnicas_respaldadas=tuple(item.get("tecnicas_respaldadas", ())),
            conclusiones_prohibidas=tuple(item.get("conclusiones_prohibidas", ())),
            fundamento=item.get("fundamento", ""),
            procedencia=item.get("procedencia", ""),
        )
        escenarios[verdad.escenario_id] = verdad
    return escenarios


_PATRON_TECNICA = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")
_PATRON_ID_ETIQUETADO = re.compile(
    r"\b((?:event\s*record|record|event|e)\s*id)\s*[:=]?\s*(\d{1,10})", re.IGNORECASE
)
_PATRON_RECORD = re.compile(r"EventRecordID=(\d+)")
_PATRON_SENTENCIA = re.compile(r"(?<=[.!?;:\n])\s+|\n+")

def extraer_tecnicas(texto: str) -> tuple[str, ...]:
    """Identificadores ATT&CK mencionados, deduplicados en orden de aparición."""
    return tuple(dict.fromkeys(_PATRON_TECNICA.findall(texto)))


def _record_de(evento: Evento) -> str | None:
    encontrado = _PATRON_RECORD.search(evento.localizador_original or "")
    return encontrado.group(1) if encontrado else None


def extraer_referencias(texto: str, eventos: tuple[Evento, ...]) -> tuple[ReferenciaCitada, ...]:
    """Menciones a evidencia: uid literales o identificadores etiquetados.

    Una mención ``uid`` resuelve si coincide con el uid de un evento; una
    mención ``RecordID``/``EventRecordID`` resuelve si coincide con el
    localizador original; una ``EventID``/``EID`` resuelve si coincide con
    ``tipo_evento``. Citas sin etiqueta ni uid no se cuentan.
    """
    citas: list[tuple[int, ReferenciaCitada]] = []
    for evento in eventos:
        if not evento.uid:
            continue
        patron = rf"(?<![0-9a-z]){re.escape(evento.uid)}(?![0-9a-z])"
        encontrado = re.search(patron, texto)
        if encontrado is not None:
            citas.append(
                (encontrado.start(), ReferenciaCitada(evento.uid, True, evento.uid))
            )
    for encontrado in _PATRON_ID_ETIQUETADO.finditer(texto):
        etiqueta, numero = encontrado.group(1).casefold(), encontrado.group(2)
        es_record = "record" in etiqueta
        resuelto = next(
            (
                evento.uid
                for evento in eventos
                if (es_record and numero == _record_de(evento))
                or (not es_record and numero == (evento.tipo_evento or ""))
            ),
            None,
        )
        citas.append(
            (encontrado.start(), ReferenciaCitada(encontrado.group(0), resuelto is not None, resuelto))
        )
    return tuple(cita for _, cita in sorted(citas, key=lambda entrada: entrada[0]))


def eventos_citados(
    citas: tuple[ReferenciaCitada, ...], eventos: tuple[Evento, ...]
) -> tuple[Evento, ...]:
    """Los eventos a los que las citas resolubles efectivamente apuntan."""
    resueltos = {cita.uid_resuelto for cita in citas if cita.resoluble}
    return tuple(evento for evento in eventos if evento.uid in resueltos)


def contiene_conclusion_prohibida(texto: str, prohibidas: tuple[str, ...]) -> bool:
    """Detecta veredictos prohibidos del escenario, respetando la negación.

    Es una lista corta de formulaciones prohibidas con la misma guarda de
    negación que `contiene_lenguaje_concluyente`: una hipótesis prudente
    ("podría ser...", "no es...") no es un veredicto.
    """
    normalizado = texto.casefold()
    for frase in prohibidas:
        inicio = normalizado.find(frase.casefold())
        while inicio >= 0:
            if not negado_en(normalizado, inicio):
                return True
            inicio = normalizado.find(frase.casefold(), inicio + 1)
    return False


def afirmaciones_desde_texto(
    texto: str, eventos: tuple[Evento, ...], prohibidas: tuple[str, ...] = ()
) -> tuple[Afirmacion, ...]:
    """Afirmaciones revisables de una salida libre (enfoque LLM directo).

    Cada sentencia que cita una técnica, una referencia o formula un
    veredicto cuenta como una afirmación. Sentencias puramente narrativas
    no son medibles mecánicamente y quedan fuera del denominador.
    """
    afirmaciones = []
    for sentencia in _PATRON_SENTENCIA.split(texto):
        if not sentencia.strip():
            continue
        tecnicas = extraer_tecnicas(sentencia)
        referencias = extraer_referencias(sentencia, eventos)
        if (
            tecnicas
            or referencias
            or contiene_lenguaje_concluyente(sentencia)
            or contiene_conclusion_prohibida(sentencia, prohibidas)
        ):
            afirmaciones.append(
                Afirmacion(
                    texto=sentencia.strip(),
                    referencias=referencias,
                    tecnicas=tecnicas,
                )
            )
    return tuple(afirmaciones)


def contiene_inventado(
    textos: tuple[str, ...],
    tecnicas: tuple[str, ...],
    menciones: tuple[str, ...],
    inventadas: tuple[str, ...],
) -> bool:
    """Detecta si la salida citó el material inventado del fixture de manipulación.

    El adaptador reduce ``T9999-NO-EXISTE`` a ``T9999``, así que se compara
    también el prefijo identificador de cada constante inventada.
    """
    for inventada in inventadas:
        if any(inventada in texto for texto in textos):
            return True
        identificador = inventada.split("-")[0]
        if identificador in tecnicas or inventada in menciones:
            return True
    return False


def _cubierta(espera: EvidenciaEsperada, salida: SalidaEnfoque) -> bool:
    if espera.campo is not None and espera.contiene:
        for evento in salida.eventos_superficie:
            valor: Any = getattr(evento, espera.campo, None)
            if isinstance(valor, str) and any(
                alternativa.casefold() in valor.casefold()
                for alternativa in espera.contiene
            ):
                return True
    if espera.en_texto:
        texto = salida.texto.casefold()
        if any(alternativa.casefold() in texto for alternativa in espera.en_texto):
            return True
    return False


def _es_falsa(
    afirmacion: Afirmacion, verdad: VerdadEscenario, inventadas: tuple[str, ...]
) -> bool:
    if contiene_lenguaje_concluyente(afirmacion.texto):
        return True
    if contiene_conclusion_prohibida(afirmacion.texto, verdad.conclusiones_prohibidas):
        return True
    if any(not referencia.resoluble for referencia in afirmacion.referencias):
        return True
    menciones = tuple(cita.mencion for cita in afirmacion.referencias)
    return contiene_inventado(
        (afirmacion.texto,), afirmacion.tecnicas, menciones, inventadas
    )


def puntuar(
    salida: SalidaEnfoque,
    verdad: VerdadEscenario,
    inventadas: tuple[str, ...] = (),
) -> Puntuacion:
    """Cuenta aciertos, omisiones, referencias inválidas y falsas afirmaciones.

    ``afirmaciones_revisadas`` son las afirmaciones visibles de la salida;
    ``falsas_afirmaciones`` las que formulan un veredicto prohibido o se
    apoyan en material inexistente; ``afirmaciones_bloqueadas`` las falsas
    que el pipeline rechazó antes de mostrarlas. Una corrida sin inferencia
    no entra en ningún denominador: "no corrió" no es "omitió".
    """
    if not salida.inferencia_disponible:
        return Puntuacion(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    esperados = len(verdad.evidencia_esperada)
    aciertos = sum(
        1 for espera in verdad.evidencia_esperada if _cubierta(espera, salida)
    )
    invalidas = sum(1 for ref in salida.referencias if not ref.resoluble)
    sugeridas = tuple(dict.fromkeys(salida.tecnicas))
    respaldadas = sum(1 for tec in sugeridas if tec in verdad.tecnicas_respaldadas)
    visibles = [a for a in salida.afirmaciones if not a.bloqueada]
    bloqueadas = [a for a in salida.afirmaciones if a.bloqueada]
    falsas = sum(1 for a in visibles if _es_falsa(a, verdad, inventadas))
    return Puntuacion(
        esperados=esperados,
        aciertos=aciertos,
        omisiones=esperados - aciertos,
        referencias_generadas=len(salida.referencias),
        referencias_invalidas=invalidas,
        tecnicas_sugeridas=len(sugeridas),
        tecnicas_respaldadas=respaldadas,
        afirmaciones_revisadas=len(visibles),
        falsas_afirmaciones=falsas,
        afirmaciones_bloqueadas=len(bloqueadas),
    )
