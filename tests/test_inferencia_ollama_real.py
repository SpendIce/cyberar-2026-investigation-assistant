"""Prueba de contrato end-to-end opt-in contra un Ollama real; ver docs/inferencia.md.

Ejecuta una inferencia determinista (temperatura 0, semilla fija) sobre el
caso sembrado y comprueba que el hallazgo validado queda disponible a través
del contrato del módulo de investigación (crear → investigar → consultar).
"""

from __future__ import annotations

import os

import pytest

from investigacion.adaptadores.controlados import EvidenciaControlada
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.modelos import EstadoRevision, ModalidadInferencia, Origen, ProcedenciaMapeo
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.sembrado import (
    PROCEDENCIA_SEMBRADA,
    RUTA_SEMBRADA,
    SHA_SEMBRADO,
    VERSIONES_SEMBRADAS,
    eventos_sembrados,
)

MODELO = os.environ.get("OLLAMA_MODELO_PRUEBA")


@pytest.mark.skipif(not MODELO, reason="requiere OLLAMA_MODELO_PRUEBA y un servidor Ollama local")
def test_inferencia_determinista_sobre_el_caso_sembrado_queda_consultable() -> None:
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(
            eventos=eventos_sembrados(), sha256=SHA_SEMBRADO,
            nombre=RUTA_SEMBRADA, versiones=VERSIONES_SEMBRADAS,
        ),
        motor_inferencia=InferenciaOllama(
            MODELO,
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            modalidad=ModalidadInferencia.MODELO_LOCAL,
        ),
        repositorio=RepositorioEnMemoria(),
        generador_de_ids=lambda: "caso-inferencia-real",
    )
    creado = modulo.crear_caso(Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA))
    referencias_existentes = {evento.uid for evento in creado.eventos}

    investigado = modulo.investigar_caso(creado.id)

    assert investigado.modalidad_inferencia is ModalidadInferencia.MODELO_LOCAL
    consultado = modulo.consultar_caso(creado.id)
    assert consultado.hallazgos == investigado.hallazgos
    for hallazgo in investigado.hallazgos:
        assert hallazgo.hipotesis.strip()
        assert set(hallazgo.referencias_eventos) <= referencias_existentes
        assert hallazgo.referencias_eventos, "cada hallazgo aceptado debe citar evidencia"
        assert hallazgo.procedencia_mapeo is ProcedenciaMapeo.MODELO
        assert hallazgo.estado_revision is EstadoRevision.PENDIENTE
    if not investigado.hallazgos:
        assert investigado.errores, "sin hallazgos, el motivo debe quedar explícito"
