"""La UI infiere sólo contra Ollama local/privado: Zen es pre-procesado offline.

El servicio de la interfaz no debe habilitar el endpoint externo Zen sólo
porque `OPENCODE_API_KEY` exista en el ambiente: la inferencia interactiva
usa el endpoint Ollama declarado (nodo privado o modelo local) y degrada
cuando el endpoint no responde. Un host `*.ts.net` tampoco es controlado
por defecto: entra sólo si el equipo lo declara o si el endpoint usa la
IP CGNAT de la tailnet.
"""

from __future__ import annotations

import pytest

from investigacion.errores import InferenciaNoDisponible
from investigacion.soberania import es_endpoint_controlado
from investigacion.ui.servicio import motor_inferencia

# Las variables que moldean el motor interactivo: se limpian por test para
# que el ambiente de la máquina no altere el resultado.
_VARS_MOTOR = (
    "OPENCODE_API_KEY",
    "OLLAMA_MODELO",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODELO_NODO",
    "OLLAMA_BASE_URL_NODO",
    "INVESTIGACION_HOST_CONTROLADO",
)


@pytest.fixture(autouse=True)
def _ambiente_limpio(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in _VARS_MOTOR:
        monkeypatch.delenv(variable, raising=False)


def _proponer_error(motor) -> str:
    # El motor real se ejercita contra endpoints inalcanzables de loopback o
    # DNS `.invalid`: fallan de forma determinista y el mensaje delata a qué
    # endpoint apuntó el adaptador elegido.
    with pytest.raises(InferenciaNoDisponible) as exc:
        motor.proponer("caso-1", ())
    return str(exc.value)


def test_la_ui_nunca_usa_zen_aunque_exista_la_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCODE_API_KEY", "sk-fake")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:1")

    error = _proponer_error(motor_inferencia())

    assert "http://127.0.0.1:1" in error
    assert "zen" not in error.lower()


def test_sin_ollama_modelo_configurado_se_intenta_el_modelo_fijado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:1")

    error = _proponer_error(motor_inferencia())

    assert "http://127.0.0.1:1" in error


def test_con_ollama_modelo_el_motor_apunta_al_endpoint_configurado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_MODELO", "qwen2.5:7b-instruct")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:1")

    error = _proponer_error(motor_inferencia())

    assert "http://127.0.0.1:1" in error


def test_el_nodo_privado_es_primario_y_el_local_es_respaldo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_MODELO_NODO", "qwen2.5:32b")
    monkeypatch.setenv("OLLAMA_BASE_URL_NODO", "http://127.0.0.1:1")
    monkeypatch.setenv("OLLAMA_MODELO", "qwen2.5:7b-instruct")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:2")

    error = _proponer_error(motor_inferencia())

    assert "http://127.0.0.1:1" in error
    assert "http://127.0.0.1:2" in error


def test_un_endpoint_publico_no_declarado_degrada_sin_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_MODELO", "qwen2.5:7b-instruct")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://8.8.8.8:11434")

    error = _proponer_error(motor_inferencia())

    assert "infraestructura controlada" in error


def test_un_endpoint_publico_declarado_como_controlado_intenta_conectar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_MODELO", "qwen2.5:7b-instruct")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://nodo-externo.invalid:1")
    monkeypatch.setenv("INVESTIGACION_HOST_CONTROLADO", "nodo-externo.invalid")

    error = _proponer_error(motor_inferencia())

    assert "infraestructura controlada" not in error
    assert "nodo-externo.invalid:1" in error


def test_un_nombre_ts_net_no_es_controlado_sin_declaracion() -> None:
    assert not es_endpoint_controlado("http://nodo.tail1234.ts.net:11434")
    assert es_endpoint_controlado(
        "http://nodo.tail1234.ts.net:11434",
        hosts_declarados=frozenset({"nodo.tail1234.ts.net"}),
    )
    # La IP CGNAT de la tailnet sigue contando como infraestructura propia.
    assert es_endpoint_controlado("http://100.64.7.8:11434")
