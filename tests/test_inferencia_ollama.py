"""Pruebas deterministas del adaptador Ollama, con transporte HTTP sustituido.

No abren conexión de red: inyectan un `transporte` falso que devuelve
respuestas ya decodificadas. La prueba de contrato contra un Ollama real
vive en `test_inferencia_ollama_real.py` y es opt-in.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.catalogo_attack import CatalogoAttack, Tecnica
from investigacion.errores import InferenciaNoDisponible
from investigacion.modelos import Evento, ModalidadInferencia


def _evento(uid: str) -> Evento:
    return Evento(
        uid=uid,
        caso_id="caso-1",
        origen_sha256="sha",
        localizador_original=f"record-{uid}",
        tipo_evento="ProcessCreated",
    )


def _catalogo() -> CatalogoAttack:
    return CatalogoAttack(
        version="prueba",
        fecha="2026-01-01",
        procedencia="fixture de prueba",
        tecnicas={"T1021.002": Tecnica("T1021.002", "SMB/Windows Admin Shares")},
    )


def _transporte_fijo(contenido: str) -> Any:
    def transporte(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        return {"message": {"role": "assistant", "content": contenido}}

    return transporte


def _motor(contenido: str, **kwargs: Any) -> InferenciaOllama:
    return InferenciaOllama(
        "modelo-de-prueba",
        catalogo=_catalogo(),
        transporte=_transporte_fijo(contenido),
        **kwargs,
    )


def test_una_respuesta_valida_se_convierte_en_propuestas_de_hallazgo() -> None:
    contenido = json.dumps(
        {
            "hallazgos": [
                {
                    "hipotesis": "Ejecución remota compatible con administración de servicios",
                    "referencias_eventos": ["ev-1", "ev-2"],
                    "tecnicas_candidatas": ["T1021.002"],
                    "razon_vinculo": "Instalación de servicio seguida de PowerShell",
                    "explicaciones_alternativas": ["Administración legítima"],
                }
            ]
        }
    )
    motor = _motor(contenido)

    propuestas = motor.proponer("caso-1", (_evento("ev-1"), _evento("ev-2")))

    assert len(propuestas) == 1
    propuesta = propuestas[0]
    assert propuesta.referencias_eventos == ("ev-1", "ev-2")
    assert propuesta.tecnicas_candidatas == ("T1021.002",)
    assert propuesta.explicaciones_alternativas == ("Administración legítima",)


def test_el_modelo_puede_abstenerse_devolviendo_una_lista_vacia() -> None:
    motor = _motor(json.dumps({"hallazgos": []}))

    propuestas = motor.proponer("caso-1", (_evento("ev-1"),))

    assert propuestas == ()


def test_un_fallo_de_transporte_se_trata_como_inferencia_no_disponible() -> None:
    def transporte_roto(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        raise OSError("conexión rechazada")

    motor = InferenciaOllama(
        "modelo-de-prueba", catalogo=_catalogo(), transporte=transporte_roto
    )

    with pytest.raises(InferenciaNoDisponible):
        motor.proponer("caso-1", (_evento("ev-1"),))


def test_contenido_no_json_se_rechaza_como_inferencia_no_disponible() -> None:
    motor = _motor("esto no es json")

    with pytest.raises(InferenciaNoDisponible):
        motor.proponer("caso-1", (_evento("ev-1"),))


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"hallazgos": "no es una lista"},
        {"hallazgos": [{"referencias_eventos": ["ev-1"], "razon_vinculo": "x"}]},
        {"hallazgos": [{"hipotesis": "  ", "referencias_eventos": [], "razon_vinculo": "x"}]},
        {"hallazgos": [{"hipotesis": "h", "referencias_eventos": "ev-1", "razon_vinculo": "x"}]},
    ],
)
def test_una_salida_que_no_cumple_el_esquema_se_rechaza(cuerpo: dict[str, Any]) -> None:
    motor = _motor(json.dumps(cuerpo))

    with pytest.raises(InferenciaNoDisponible):
        motor.proponer("caso-1", (_evento("ev-1"),))


def test_el_mensaje_ausente_se_rechaza_como_inferencia_no_disponible() -> None:
    def transporte_sin_mensaje(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        return {"done": True}

    motor = InferenciaOllama(
        "modelo-de-prueba", catalogo=_catalogo(), transporte=transporte_sin_mensaje
    )

    with pytest.raises(InferenciaNoDisponible):
        motor.proponer("caso-1", (_evento("ev-1"),))


def test_la_modalidad_configurada_se_expone_en_el_puerto() -> None:
    motor = _motor(json.dumps({"hallazgos": []}), modalidad=ModalidadInferencia.NODO_PRIVADO)

    assert motor.modalidad is ModalidadInferencia.NODO_PRIVADO


def test_el_prompt_solo_incluye_evidencia_entregada_y_tecnicas_del_catalogo() -> None:
    capturado: dict[str, Any] = {}

    def transporte_espia(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        capturado["cuerpo"] = cuerpo
        return {"message": {"content": json.dumps({"hallazgos": []})}}

    motor = InferenciaOllama(
        "modelo-de-prueba", catalogo=_catalogo(), transporte=transporte_espia
    )
    evento = _evento("ev-1")

    motor.proponer("caso-1", (evento,))

    mensaje_usuario = capturado["cuerpo"]["messages"][1]["content"]
    datos = json.loads(mensaje_usuario)
    assert [e["uid"] for e in datos["eventos"]] == ["ev-1"]
    assert [t["id"] for t in datos["tecnicas_permitidas"]] == ["T1021.002"]
    assert capturado["cuerpo"]["format"]["required"] == ["hallazgos"]
    assert capturado["cuerpo"]["options"]["temperature"] == 0.0
