"""Motor de inferencia contra opencode Zen, un endpoint externo declarado.

Zen expone una API compatible con OpenAI chat/completions en
`https://opencode.ai/zen/v1`. A diferencia del nodo Ollama, este endpoint no
pertenece a la infraestructura del equipo: su uso es una decisión explícita
(`permitir_externo`) reservada al pre-procesado offline de fixtures públicos,
y la modalidad `modelo_externo` queda persistida en el caso junto con la
advertencia de soberanía (ADR-0016, ADR-0011). La credencial se lee de
`OPENCODE_API_KEY` y nunca se escribe en el repositorio.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from investigacion.adaptadores.ollama import (
    ESQUEMA_PROPUESTAS,
    PROMPT_SISTEMA,
    Transporte,
    construir_prompt,
    _propuestas_desde_json,
)
from investigacion.catalogo_attack import CatalogoAttack, cargar_catalogo
from investigacion.errores import InferenciaNoDisponible
from investigacion.modelos import Evento, ModalidadInferencia, PropuestaHallazgo
from investigacion.soberania import es_endpoint_controlado

URL_ZEN = "https://opencode.ai/zen/v1"
ENV_API_KEY = "OPENCODE_API_KEY"


def transporte_zen(api_key: str) -> Transporte:
    """Transporte chat/completions con autenticación Bearer."""

    def enviar(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        peticion = urllib.request.Request(
            url,
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                # El gateway rechaza el User-Agent por defecto de urllib (403).
                "User-Agent": "investigacion-local/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))  # type: ignore[no-any-return]

    return enviar


def _contenido_json(contenido: str) -> Any:
    """Decodifica el cuerpo del mensaje tolerando cercas de markdown."""
    texto = contenido.strip()
    if texto.startswith("```"):
        lineas = texto.splitlines()
        texto = "\n".join(lineas[1:-1] if lineas[-1].startswith("```") else lineas[1:])
    try:
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        raise InferenciaNoDisponible(
            f"la salida del modelo no es JSON válido: {exc}"
        ) from exc


class InferenciaZen:
    """Implementa `MotorDeInferencia` contra `/chat/completions` de Zen."""

    def __init__(
        self,
        modelo: str = "deepseek-v4-flash",
        *,
        base_url: str = URL_ZEN,
        api_key: str | None = None,
        catalogo: CatalogoAttack | None = None,
        timeout: float = 60.0,
        temperatura: float = 0.0,
        semilla: int = 7,
        permitir_externo: bool = False,
        transporte: Transporte | None = None,
    ) -> None:
        self.modelo = modelo
        self._base_url = base_url.rstrip("/")
        self._catalogo = catalogo if catalogo is not None else cargar_catalogo()
        self._timeout = timeout
        self._temperatura = temperatura
        self._semilla = semilla
        self._permitir_externo = permitir_externo
        self._externo = not es_endpoint_controlado(self._base_url)
        self._evidencia_enviada = False
        if transporte is not None:
            self._transporte = transporte
        else:
            clave = api_key if api_key is not None else os.environ.get(ENV_API_KEY, "")
            if not clave:
                raise InferenciaNoDisponible(
                    f"falta la credencial del endpoint externo: exportar {ENV_API_KEY}"
                )
            self._transporte = transporte_zen(clave)

    @property
    def modalidad(self) -> ModalidadInferencia:
        return ModalidadInferencia.MODELO_EXTERNO

    @property
    def advertencias(self) -> tuple[str, ...]:
        if self._evidencia_enviada:
            return (
                "la evidencia se envió a un endpoint fuera de la infraestructura "
                f"controlada: {self._base_url}",
            )
        return ()

    def proponer(
        self, caso_id: str, evidencia: tuple[Evento, ...]
    ) -> tuple[PropuestaHallazgo, ...]:
        if self._externo and not self._permitir_externo:
            raise InferenciaNoDisponible(
                "endpoint de inferencia fuera de la infraestructura "
                f"controlada: {self._base_url}; declarar el uso de endpoints "
                "externos de forma explícita para habilitarlo"
            )
        cuerpo = {
            "model": self.modelo,
            "stream": False,
            "temperature": self._temperatura,
            "seed": self._semilla,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "propuestas_hallazgos",
                    "strict": True,
                    "schema": ESQUEMA_PROPUESTAS,
                },
            },
            "messages": [
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": construir_prompt(evidencia, self._catalogo)},
            ],
        }
        datos = self._enviar(cuerpo)
        elecciones = datos.get("choices") if isinstance(datos, dict) else None
        contenido = None
        if isinstance(elecciones, list) and elecciones:
            primera = elecciones[0]
            mensaje = primera.get("message") if isinstance(primera, dict) else None
            if isinstance(mensaje, dict):
                contenido = mensaje.get("content")
        if not isinstance(contenido, str) or not contenido.strip():
            raise InferenciaNoDisponible("Zen no devolvió contenido de mensaje")
        self._evidencia_enviada = self._externo
        return _propuestas_desde_json(_contenido_json(contenido))

    def _enviar(self, cuerpo: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        try:
            return self._transporte(url, cuerpo, self._timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 400 and "response_format" in cuerpo:
                # Algunos modelos del gateway no soportan json_schema: se
                # reintenta pidiendo JSON por prompt; el validador decide.
                sin_esquema = {
                    clave: valor
                    for clave, valor in cuerpo.items()
                    if clave != "response_format"
                }
                return self._llamar(url, sin_esquema)
            raise InferenciaNoDisponible(
                f"error HTTP {exc.code} del endpoint Zen: {exc.reason}"
            ) from exc
        except (urllib.error.URLError, OSError, TimeoutError,
                json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InferenciaNoDisponible(
                f"error de comunicación con Zen '{self._base_url}': {exc}"
            ) from exc

    def _llamar(self, url: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._transporte(url, cuerpo, self._timeout)
        except urllib.error.HTTPError as exc:
            raise InferenciaNoDisponible(
                f"error HTTP {exc.code} del endpoint Zen: {exc.reason}"
            ) from exc
        except (urllib.error.URLError, OSError, TimeoutError,
                json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InferenciaNoDisponible(
                f"error de comunicación con Zen '{self._base_url}': {exc}"
            ) from exc
