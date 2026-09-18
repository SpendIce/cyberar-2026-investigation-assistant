"""Casos fijados al frente de la galería: pin persistente y orden."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from investigacion.escenarios import (
    eventos_control_legitimo,
    origen_control_legitimo,
)
from investigacion.modelos import Caso, ModalidadInferencia
from investigacion.ui.galeria import ordenar_para_galeria
from investigacion.ui.servicio import servicio_persistido


def _caso(caso_id: str, titulo: str) -> Caso:
    origen = replace(origen_control_legitimo(), nombre=titulo)
    eventos = tuple(
        replace(evento, caso_id=caso_id, origen_sha256=origen.sha256 or "")
        for evento in eventos_control_legitimo()
    )
    return Caso(
        id=caso_id,
        origen=origen,
        eventos=eventos,
        hallazgos=(),
        modalidad_inferencia=ModalidadInferencia.MODELO_LOCAL,
    )


def test_el_fijado_persiste_entre_cargas_del_servicio(tmp_path: Path) -> None:
    servicio = servicio_persistido(tmp_path)

    servicio.alternar_fijado("caso-demo")
    assert servicio_persistido(tmp_path).fijados == {"caso-demo"}

    servicio.alternar_fijado("caso-demo")
    assert servicio_persistido(tmp_path).fijados == set()


def test_la_galeria_ordena_fijados_primero(tmp_path: Path) -> None:
    servicio = servicio_persistido(tmp_path)
    servicio.alternar_fijado("caso-zulu")
    casos = (
        _caso("caso-alfa", "Alfa"),
        _caso("caso-zulu", "Zulu"),
        _caso("caso-medio", "Medio"),
    )

    ordenados = ordenar_para_galeria(servicio, casos)

    assert [caso.id for caso in ordenados] == [
        "caso-zulu",
        "caso-alfa",
        "caso-medio",
    ]
