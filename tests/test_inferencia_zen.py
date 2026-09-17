"""Pruebas deterministas del adaptador Zen, con transporte HTTP sustituido.

No abren conexión de red: inyectan un `transporte` falso que devuelve
respuestas ya decodificadas con la forma OpenAI chat/completions.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any

import pytest

from investigacion.adaptadores.zen import InferenciaZen
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
        return {"choices": [{"message": {"role": "assistant", "content": contenido}}]}

    return transporte


def _motor(contenido: str, **kwargs: Any) -> InferenciaZen:
    kwargs.setdefault("permitir_externo", True)
    return InferenciaZen(
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
    assert propuestas[0].referencias_eventos == ("ev-1", "ev-2")
    assert propuestas[0].tecnicas_candidatas == ("T1021.002",)


def test_la_modalidad_es_modelo_externo() -> None:
    motor = _motor(json.dumps({"hallazgos": []}))

    assert motor.modalidad is ModalidadInferencia.MODELO_EXTERNO


def test_endpoint_externo_requiere_declaracion_explicita() -> None:
    motor = _motor(json.dumps({"hallazgos": []}), permitir_externo=False)

    with pytest.raises(InferenciaNoDisponible, match="fuera de la infraestructura"):
        motor.proponer("caso-1", (_evento("ev-1"),))


def test_endpoint_externo_declarado_deja_advertencia() -> None:
    motor = _motor(json.dumps({"hallazgos": []}), permitir_externo=True)

    motor.proponer("caso-1", (_evento("ev-1"),))

    assert motor.advertencias
    assert "opencode.ai" in motor.advertencias[0]


def test_sin_credencial_ni_transporte_la_construccion_falla() -> None:
    with pytest.raises(InferenciaNoDisponible, match="OPENCODE_API_KEY"):
        InferenciaZen(api_key="", catalogo=_catalogo())


def test_un_fallo_de_transporte_se_trata_como_inferencia_no_disponible() -> None:
    def transporte_roto(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        raise OSError("conexión rechazada")

    motor = InferenciaZen(
        catalogo=_catalogo(), transporte=transporte_roto, permitir_externo=True
    )

    with pytest.raises(InferenciaNoDisponible):
        motor.proponer("caso-1", (_evento("ev-1"),))


def test_http_400_reintenta_sin_response_format() -> None:
    llamadas: list[dict[str, Any]] = []

    def transporte_picky(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        llamadas.append(cuerpo)
        if "response_format" in cuerpo:
            raise urllib.error.HTTPError(url, 400, "Bad Request", {}, None)
        return {"choices": [{"message": {"content": json.dumps({"hallazgos": []})}}]}

    motor = InferenciaZen(
        catalogo=_catalogo(), transporte=transporte_picky, permitir_externo=True
    )

    assert motor.proponer("caso-1", (_evento("ev-1"),)) == ()
    assert len(llamadas) == 2
    assert "response_format" in llamadas[0]
    assert "response_format" not in llamadas[1]


def test_http_500_se_trata_como_inferencia_no_disponible() -> None:
    def transporte_500(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        raise urllib.error.HTTPError(url, 500, "Server Error", {}, None)

    motor = InferenciaZen(
        catalogo=_catalogo(), transporte=transporte_500, permitir_externo=True
    )

    with pytest.raises(InferenciaNoDisponible, match="HTTP 500"):
        motor.proponer("caso-1", (_evento("ev-1"),))


def test_contenido_no_json_se_rechaza_como_inferencia_no_disponible() -> None:
    motor = _motor("esto no es json", permitir_externo=True)

    with pytest.raises(InferenciaNoDisponible):
        motor.proponer("caso-1", (_evento("ev-1"),))


def test_contenido_con_cerca_markdown_se_decodifica() -> None:
    motor = _motor(
        "```json\n" + json.dumps({"hallazgos": []}) + "\n```", permitir_externo=True
    )

    assert motor.proponer("caso-1", (_evento("ev-1"),)) == ()


def test_el_mensaje_ausente_se_rechaza_como_inferencia_no_disponible() -> None:
    def transporte_sin_mensaje(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        return {"choices": []}

    motor = InferenciaZen(
        catalogo=_catalogo(), transporte=transporte_sin_mensaje, permitir_externo=True
    )

    with pytest.raises(InferenciaNoDisponible):
        motor.proponer("caso-1", (_evento("ev-1"),))


def test_el_cuerpo_declara_el_esquema_y_el_prompt_compartido() -> None:
    capturado: dict[str, Any] = {}

    def transporte_espia(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        capturado["url"] = url
        capturado["cuerpo"] = cuerpo
        return {"choices": [{"message": {"content": json.dumps({"hallazgos": []})}}]}

    motor = InferenciaZen(
        catalogo=_catalogo(), transporte=transporte_espia, permitir_externo=True
    )
    motor.proponer("caso-1", (_evento("ev-1"),))

    assert capturado["url"].endswith("/chat/completions")
    cuerpo = capturado["cuerpo"]
    assert cuerpo["response_format"]["json_schema"]["schema"]["required"] == ["hallazgos"]
    mensaje_usuario = cuerpo["messages"][1]["content"]
    datos = json.loads(mensaje_usuario)
    assert [e["uid"] for e in datos["eventos"]] == ["ev-1"]
    assert [t["id"] for t in datos["tecnicas_permitidas"]] == ["T1021.002"]
