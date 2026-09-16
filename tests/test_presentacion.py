from dataclasses import replace

from investigacion.adaptadores.controlados import EvidenciaControlada, InferenciaControlada
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.modelos import (
    Caso,
    Evento,
    ModalidadInferencia,
    Origen,
    PropuestaHallazgo,
)
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.ui.presentacion import (
    cronologia,
    estado_caso,
    eventos_referenciados,
    procedencia_evento,
    referencias_no_resueltas,
)


def _evento(uid: str, **campos: object) -> Evento:
    datos: dict[str, object] = {
        "uid": uid,
        "caso_id": "",
        "origen_sha256": "",
        "localizador_original": f"record-{uid}",
    }
    datos.update(campos)
    return Evento(**datos)  # type: ignore[arg-type]


def _caso() -> Caso:
    eventos = (
        _evento("ev-2", timestamp_normalizado="2026-01-01T10:00:05Z"),
        _evento("ev-1", timestamp_normalizado="2026-01-01T10:00:00Z"),
        _evento("ev-3", timestamp_normalizado=None),
    )
    propuesta = PropuestaHallazgo(
        hipotesis="Hipótesis de prueba",
        referencias_eventos=("ev-1", "ev-2"),
    )
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(
            eventos=eventos,
            sha256="sha-de-prueba",
            versiones={"hayabusa": "1.0", "catalogo_attack": "local"},
        ),
        motor_inferencia=InferenciaControlada(propuestas=(propuesta,)),
        repositorio=RepositorioEnMemoria(),
        generador_de_ids=lambda: "caso-ui",
    )
    creado = modulo.crear_caso(Origen(ruta="fixtures/x.evtx", procedencia="laboratorio"))
    return modulo.investigar_caso(creado.id)


def test_cronologia_ordena_por_timestamp_y_deja_los_ausentes_al_final() -> None:
    caso = _caso()

    ordenados = cronologia(caso)

    assert [evento.uid for evento in ordenados] == ["ev-1", "ev-2", "ev-3"]


def test_eventos_referenciados_resuelve_las_referencias_del_hallazgo() -> None:
    caso = _caso()
    hallazgo = caso.hallazgos[0]

    referenciados = eventos_referenciados(caso, hallazgo)

    assert [evento.uid for evento in referenciados] == ["ev-1", "ev-2"]


def test_eventos_referenciados_ignora_referencias_ausentes() -> None:
    caso = _caso()
    hallazgo = replace(caso.hallazgos[0], referencias_eventos=("ev-1", "ev-inexistente"))

    referenciados = eventos_referenciados(caso, hallazgo)

    assert [evento.uid for evento in referenciados] == ["ev-1"]


def test_referencias_no_resueltas_nombra_las_referencias_rotas() -> None:
    caso = _caso()
    hallazgo = replace(caso.hallazgos[0], referencias_eventos=("ev-1", "ev-inexistente"))

    assert referencias_no_resueltas(caso, hallazgo) == ("ev-inexistente",)


def test_procedencia_evento_expone_fuente_hash_y_localizador() -> None:
    caso = _caso()

    procedencia = dict(procedencia_evento(caso, caso.eventos[0]))

    assert procedencia["SHA-256"] == "sha-de-prueba"
    assert procedencia["Localizador original"] == "record-ev-2"
    assert procedencia["Procedencia"] == "laboratorio"
    assert "hayabusa 1.0" in procedencia["Versiones"]


def test_procedencia_evento_sin_regla_lo_declara_explicitamente() -> None:
    caso = _caso()

    procedencia = dict(procedencia_evento(caso, caso.eventos[0]))

    assert procedencia["Regla Hayabusa"] == "sin regla"


def test_estado_caso_resume_modalidad_y_conteos() -> None:
    caso = _caso()

    estado = dict(estado_caso(caso))

    assert estado["Identificador"] == "caso-ui"
    assert estado["Eventos"] == "3"
    assert estado["Hallazgos"] == "1"
    assert estado["Modalidad de inferencia"] == ModalidadInferencia.MODELO_LOCAL.value
    assert estado["SHA-256"] == "sha-de-prueba"


def test_estado_caso_sin_inferencia_lo_indica() -> None:
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(eventos=(_evento("ev-1"),)),
        motor_inferencia=InferenciaControlada(propuestas=()),
        repositorio=RepositorioEnMemoria(),
        generador_de_ids=lambda: "caso-sin-inferencia",
    )
    caso = modulo.crear_caso(Origen(ruta="fixtures/x.evtx", procedencia="laboratorio"))

    estado = dict(estado_caso(caso))

    assert estado["Modalidad de inferencia"] == "no intentada"
