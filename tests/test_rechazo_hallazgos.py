"""Rechazo seguro de hallazgos manipulados o inventados (issue #9).

`ValidadorDeReferencias` y `InferenciaOllama` (esquema estructurado) ya
tienen cobertura propia (`test_contrato_investigacion.py`,
`test_inferencia_ollama.py`). Lo que faltaba en la suite ordinaria era un
caso determinista, sin red, que ejercite el fixture de manipulación
(`tests/casos_evaluacion.eventos_manipulados`) asumiendo el peor caso: que
el modelo obedeció la instrucción insertada. La única prueba que usaba ese
fixture era opt-in (`test_manipulacion_ollama_real.py`, requiere Ollama), así
que `uv run pytest` solo nunca demostraba esta garantía sin red.
"""

from __future__ import annotations

import json
from typing import Any

from investigacion.adaptadores.controlados import EvidenciaControlada, InferenciaControlada
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.adaptadores.ollama import PROMPT_SISTEMA, InferenciaOllama
from investigacion.modelos import Origen, PropuestaHallazgo
from investigacion.modulo import ModuloDeInvestigacion

from casos_evaluacion import EVENTO_INVENTADO, INSTRUCCION_INSERTADA, TECNICA_INVENTADA, eventos_manipulados


def _modulo_obediente(propuesta: PropuestaHallazgo) -> ModuloDeInvestigacion:
    """Simula el peor caso: un modelo que obedeció la instrucción insertada."""
    return ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(eventos=eventos_manipulados()),
        motor_inferencia=InferenciaControlada(propuestas=(propuesta,)),
        repositorio=RepositorioEnMemoria(),
        generador_de_ids=lambda: "caso-manipulado",
    )


def test_una_referencia_inventada_por_obedecer_la_instruccion_se_rechaza() -> None:
    propuesta = PropuestaHallazgo(
        hipotesis="El modelo obedeció la instrucción insertada",
        referencias_eventos=("ev-1", EVENTO_INVENTADO),
        razon_vinculo="Instrucción embebida en el contenido del evento",
    )
    modulo = _modulo_obediente(propuesta)
    caso = modulo.crear_caso(Origen(ruta="fixtures/manipulado.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    # Rechazado, no persistido: aunque el modelo "obedeció", el sistema no lo acepta.
    assert investigado.hallazgos == ()
    # El motivo queda auditable, no en un log inaccesible.
    assert any(EVENTO_INVENTADO in error for error in investigado.errores)
    assert modulo.consultar_caso(caso.id).hallazgos == ()


def test_una_tecnica_inventada_por_obedecer_la_instruccion_se_rechaza() -> None:
    propuesta = PropuestaHallazgo(
        hipotesis="El modelo obedeció la instrucción insertada",
        referencias_eventos=("ev-1",),
        tecnicas_candidatas=(TECNICA_INVENTADA,),
        razon_vinculo="Instrucción embebida en el contenido del evento",
    )
    modulo = _modulo_obediente(propuesta)
    caso = modulo.crear_caso(Origen(ruta="fixtures/manipulado.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    assert investigado.hallazgos == ()
    assert any(TECNICA_INVENTADA in error for error in investigado.errores)
    assert modulo.consultar_caso(caso.id).hallazgos == ()


def test_la_instruccion_insertada_se_conserva_como_dato_sin_alterar_la_evidencia() -> None:
    propuesta = PropuestaHallazgo(
        hipotesis="El modelo obedeció la instrucción insertada",
        referencias_eventos=("ev-1", EVENTO_INVENTADO),
        tecnicas_candidatas=(TECNICA_INVENTADA,),
        razon_vinculo="Instrucción embebida en el contenido del evento",
    )
    modulo = _modulo_obediente(propuesta)
    caso = modulo.crear_caso(Origen(ruta="fixtures/manipulado.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    # La evidencia original no se destruye ni se oculta: el texto insertado
    # sigue ahí, como dato, exactamente como llegó.
    contenidos = " ".join(evento.contenido or "" for evento in investigado.eventos)
    assert INSTRUCCION_INSERTADA in contenidos
    assert len(investigado.eventos) == len(caso.eventos)


def test_la_instruccion_insertada_llega_al_modelo_como_dato_sin_alterar_el_prompt() -> None:
    capturado: dict[str, Any] = {}

    def transporte_espia(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        capturado["cuerpo"] = cuerpo
        return {"message": {"content": json.dumps({"hallazgos": []})}}

    motor = InferenciaOllama("modelo-de-prueba", transporte=transporte_espia)

    motor.proponer("caso-manipulado", eventos_manipulados())

    sistema, usuario = capturado["cuerpo"]["messages"]
    # Las instrucciones del análisis no cambian: la inyección viaja dentro del
    # campo `contenido` del evento serializado, nunca en el mensaje de sistema.
    assert sistema == {"role": "system", "content": PROMPT_SISTEMA}
    datos = json.loads(usuario["content"])
    inyectados = [
        evento
        for evento in datos["eventos"]
        if INSTRUCCION_INSERTADA in (evento.get("contenido") or "")
    ]
    assert len(inyectados) == 1
