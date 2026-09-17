"""Un endpoint externo exige decisión explícita y deja advertencia en el caso.

La herramienta es local-first por diseño: la evidencia seleccionada solo puede
salir hacia un nodo fuera de la infraestructura controlada si quien opera lo
declara a sabiendas. Aun declarado, la advertencia queda persistida en el caso
y visible en el informe (la decisión es del usuario; el rastro es del sistema).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.adaptadores.respaldo import InferenciaConRespaldo
from investigacion.catalogo_attack import CatalogoAttack, Tecnica
from investigacion.errores import InferenciaNoDisponible
from investigacion.modelos import Evento, ModalidadInferencia
from investigacion.soberania import es_endpoint_controlado

_CATALOG0 = CatalogoAttack(
    version="prueba",
    fecha="2026-01-01",
    procedencia="fixture",
    tecnicas={"T1021.002": Tecnica("T1021.002", "SMB/Windows Admin Shares")},
)

_EVENTO = Evento(
    uid="ev-1",
    caso_id="caso-1",
    origen_sha256="sha",
    localizador_original="record-1",
)


def _transporte_ok(llamadas: list[str]) -> Any:
    def transporte(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        llamadas.append(url)
        return {"message": {"content": json.dumps({"hallazgos": []})}}

    return transporte


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://[::1]:11434",
        "http://10.0.0.5:11434",
        "http://172.16.3.9:11434",
        "http://192.168.1.20:11434",
        "http://169.254.10.10:11434",
        "http://100.64.7.8:11434",  # CGNAT: overlay tipo Tailscale del equipo
        "http://host.docker.internal:11434",
    ],
)
def test_los_endpoints_de_infraestructura_controlada_no_requieren_opt_in(url: str) -> None:
    assert es_endpoint_controlado(url)

    motor = InferenciaOllama(
        "modelo", base_url=url, catalogo=_CATALOG0, transporte=_transporte_ok([])
    )

    assert motor.proponer("caso-1", (_EVENTO,)) == ()
    assert motor.advertencias == ()


@pytest.mark.parametrize(
    "url",
    [
        "https://api.ejemplo-externo.com/v1",
        "http://151.101.2.132:11434",  # dirección pública (Fastly)
        "http://8.8.8.8:11434",
        "no-es-una-url",
        "http://:11434",
    ],
)
def test_los_endpoints_externos_se_rechazan_sin_opt_in(url: str) -> None:
    assert not es_endpoint_controlado(url)

    llamadas: list[str] = []
    motor = InferenciaOllama(
        "modelo", base_url=url, catalogo=_CATALOG0, transporte=_transporte_ok(llamadas)
    )

    with pytest.raises(InferenciaNoDisponible, match="infraestructura controlada"):
        motor.proponer("caso-1", (_EVENTO,))

    assert llamadas == []


def test_un_host_declarado_como_propio_cuenta_como_controlado() -> None:
    url = "http://8.8.8.8:11434"
    assert es_endpoint_controlado(url, hosts_declarados=frozenset({"8.8.8.8"}))

    motor = InferenciaOllama(
        "modelo",
        base_url=url,
        hosts_controlados=frozenset({"8.8.8.8"}),
        catalogo=_CATALOG0,
        transporte=_transporte_ok([]),
    )

    assert motor.proponer("caso-1", (_EVENTO,)) == ()
    assert motor.advertencias == ()


def test_el_opt_in_permite_el_endpoint_externo_y_deja_advertencia() -> None:
    llamadas: list[str] = []
    motor = InferenciaOllama(
        "modelo",
        base_url="http://8.8.8.8:11434",
        permitir_externo=True,
        catalogo=_CATALOG0,
        transporte=_transporte_ok(llamadas),
    )

    assert motor.advertencias == ()

    motor.proponer("caso-1", (_EVENTO,))

    assert llamadas == ["http://8.8.8.8:11434/api/chat"]
    assert any("8.8.8.8" in a for a in motor.advertencias)


def test_el_respaldo_cae_al_local_cuando_el_primario_es_externo_sin_opt_in() -> None:
    externo = InferenciaOllama(
        "grande",
        base_url="http://8.8.8.8:11434",
        modalidad=ModalidadInferencia.NODO_PRIVADO,
        catalogo=_CATALOG0,
        transporte=_transporte_ok([]),
    )
    local = InferenciaOllama(
        "chico",
        catalogo=_CATALOG0,
        transporte=_transporte_ok([]),
    )
    motor = InferenciaConRespaldo(externo, local)

    propuestas = motor.proponer("caso-1", (_EVENTO,))

    assert propuestas == ()
    assert motor.modalidad is ModalidadInferencia.MODELO_LOCAL
    assert any("infraestructura controlada" in a for a in motor.advertencias)


def test_el_respaldo_propaga_la_advertencia_del_motor_externo_que_respondio() -> None:
    externo = InferenciaOllama(
        "grande",
        base_url="http://8.8.8.8:11434",
        modalidad=ModalidadInferencia.NODO_PRIVADO,
        permitir_externo=True,
        catalogo=_CATALOG0,
        transporte=_transporte_ok([]),
    )
    motor = InferenciaConRespaldo(externo)

    motor.proponer("caso-1", (_EVENTO,))

    assert motor.modalidad is ModalidadInferencia.NODO_PRIVADO
    assert any("8.8.8.8" in a for a in motor.advertencias)
