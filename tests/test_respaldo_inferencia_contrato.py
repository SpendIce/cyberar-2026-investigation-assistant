"""Contrato del módulo con InferenciaConRespaldo: éxito remoto, caída con
respaldo local, y ausencia de ambos (issue #7, spec #1 "Modos de inferencia").

Cruza el contrato de `ModuloDeInvestigacion`, no la implementación interna de
`InferenciaConRespaldo` (esa vive en `test_inferencia_respaldo.py`).
"""

from __future__ import annotations

import os

import pytest

from investigacion.adaptadores.controlados import EvidenciaControlada, InferenciaControlada
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.adaptadores.respaldo import InferenciaConRespaldo
from investigacion.errores import InferenciaNoDisponible
from investigacion.modelos import Evento, ModalidadInferencia, Origen, PropuestaHallazgo
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.puertos import MotorDeInferencia


def _evento(uid: str) -> Evento:
    return Evento(
        uid=uid, caso_id="", origen_sha256="", localizador_original=f"record-{uid}",
        timestamp_normalizado="2026-01-01T00:00:00Z",
    )


def _propuesta() -> PropuestaHallazgo:
    return PropuestaHallazgo(
        hipotesis="Ejecución remota compatible con movimiento lateral",
        referencias_eventos=("ev-1",),
    )


def _modulo(motor_inferencia: MotorDeInferencia) -> ModuloDeInvestigacion:
    return ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(eventos=(_evento("ev-1"),)),
        motor_inferencia=motor_inferencia,
        repositorio=RepositorioEnMemoria(),
        generador_de_ids=lambda: "caso-1",
    )


def test_exito_remoto_no_deja_advertencias_de_respaldo() -> None:
    primario = InferenciaControlada(
        propuestas=(_propuesta(),), modalidad=ModalidadInferencia.NODO_PRIVADO
    )
    respaldo = InferenciaControlada(
        propuestas=(_propuesta(),), modalidad=ModalidadInferencia.MODELO_LOCAL
    )
    modulo = _modulo(InferenciaConRespaldo(primario, respaldo))
    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    assert investigado.modalidad_inferencia is ModalidadInferencia.NODO_PRIVADO
    assert len(investigado.hallazgos) == 1
    assert investigado.errores == ()


def test_caida_remota_con_exito_local_deja_constancia_del_motivo() -> None:
    primario = InferenciaControlada(
        modalidad=ModalidadInferencia.NODO_PRIVADO,
        falla=InferenciaNoDisponible("nodo privado caído: timeout"),
    )
    respaldo = InferenciaControlada(
        propuestas=(_propuesta(),), modalidad=ModalidadInferencia.MODELO_LOCAL
    )
    modulo = _modulo(InferenciaConRespaldo(primario, respaldo))
    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    # La transición es observable: modalidad y motivo quedan en el caso, no
    # sólo en un log que la interfaz no puede mostrar.
    assert investigado.modalidad_inferencia is ModalidadInferencia.MODELO_LOCAL
    assert len(investigado.hallazgos) == 1
    assert any(
        "nodo_privado no disponible: nodo privado caído" in error
        for error in investigado.errores
    )
    assert modulo.consultar_caso(caso.id).errores == investigado.errores


def test_sin_ambos_motores_conserva_cronologia_en_modo_degradado() -> None:
    primario = InferenciaControlada(
        modalidad=ModalidadInferencia.NODO_PRIVADO,
        falla=InferenciaNoDisponible("nodo privado caído: timeout"),
    )
    respaldo = InferenciaControlada(
        modalidad=ModalidadInferencia.MODELO_LOCAL,
        falla=InferenciaNoDisponible("modelo local ausente: conexión rechazada"),
    )
    modulo = _modulo(InferenciaConRespaldo(primario, respaldo))
    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    assert investigado.modalidad_inferencia is ModalidadInferencia.DEGRADADO
    assert investigado.hallazgos == ()
    assert investigado.eventos == caso.eventos
    assert any("nodo_privado no disponible" in error for error in investigado.errores)
    assert any("modelo_local no disponible" in error for error in investigado.errores)


MODELO = os.environ.get("OLLAMA_MODELO_PRUEBA")


@pytest.mark.skipif(not MODELO, reason="requiere OLLAMA_MODELO_PRUEBA y un servidor Ollama local")
def test_caida_real_del_nodo_privado_recae_en_el_modelo_local_real() -> None:
    """Mismo escenario que arriba, con InferenciaOllama real en ambos puestos.

    El "nodo privado" apunta a un puerto sin servidor: falla rápido por
    conexión rechazada, sin esperar el timeout completo.
    """
    nodo_privado_caido = InferenciaOllama(
        "modelo-inexistente", base_url="http://localhost:1", timeout=3.0,
        modalidad=ModalidadInferencia.NODO_PRIVADO,
    )
    modelo_local = InferenciaOllama(
        MODELO, base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        modalidad=ModalidadInferencia.MODELO_LOCAL,
    )
    modulo = _modulo(InferenciaConRespaldo(nodo_privado_caido, modelo_local))
    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    assert investigado.modalidad_inferencia is ModalidadInferencia.MODELO_LOCAL
    assert any("nodo_privado no disponible" in error for error in investigado.errores)
