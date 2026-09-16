import json

import pytest

from investigacion.adaptadores.controlados import (
    EvidenciaControlada,
    InferenciaControlada,
    InferenciaNoDisponibleControlada,
)
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.errores import CasoNoEncontrado, ErrorDeImportacion
from investigacion.modelos import (
    EstadoRevision,
    Evento,
    FormatoExportacion,
    ModalidadInferencia,
    Origen,
    ProcedenciaMapeo,
    PropuestaHallazgo,
)
from investigacion.modulo import ModuloDeInvestigacion


def _evento(uid: str, **campos: object) -> Evento:
    datos: dict[str, object] = {
        "uid": uid,
        "caso_id": "",
        "origen_sha256": "",
        "localizador_original": f"record-{uid}",
        "timestamp_normalizado": "2026-01-01T00:00:00Z",
    }
    datos.update(campos)
    return Evento(**datos)  # type: ignore[arg-type]


def _propuesta(**campos: object) -> PropuestaHallazgo:
    datos: dict[str, object] = {
        "hipotesis": "Ejecución remota compatible con movimiento lateral",
        "referencias_eventos": ("ev-1",),
    }
    datos.update(campos)
    return PropuestaHallazgo(**datos)  # type: ignore[arg-type]


def _modulo(
    eventos: tuple[Evento, ...] = (),
    *,
    propuestas: tuple[PropuestaHallazgo, ...] = (),
    motor_inferencia: InferenciaControlada | None = None,
    fuentes_incompatibles: frozenset[str] = frozenset(),
) -> ModuloDeInvestigacion:
    return ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(
            eventos=eventos, fuentes_incompatibles=fuentes_incompatibles
        ),
        motor_inferencia=motor_inferencia or InferenciaControlada(propuestas=propuestas),
        repositorio=RepositorioEnMemoria(),
        generador_de_ids=lambda: "caso-1",
    )


def test_crear_y_consultar_un_caso_devuelve_eventos_con_referencias_estables() -> None:
    modulo = _modulo((_evento("ev-1"), _evento("ev-2")))

    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))

    consultado = modulo.consultar_caso(caso.id)
    assert consultado.id == "caso-1"
    assert consultado.origen.sha256 == "sha-controlado"
    assert consultado.modalidad_inferencia is None
    assert [evento.uid for evento in consultado.eventos] == ["ev-1", "ev-2"]
    assert {evento.caso_id for evento in consultado.eventos} == {"caso-1"}


def test_una_fuente_incompatible_produce_un_error_de_importacion_explicito() -> None:
    modulo = _modulo(fuentes_incompatibles=frozenset({"fixtures/roto.bin"}))

    with pytest.raises(ErrorDeImportacion):
        modulo.crear_caso(Origen(ruta="fixtures/roto.bin", procedencia="laboratorio"))


def test_consultar_un_caso_inexistente_es_un_fallo_explicito() -> None:
    modulo = _modulo()

    with pytest.raises(CasoNoEncontrado):
        modulo.consultar_caso("caso-inexistente")


def test_investigar_incorpora_un_hallazgo_validado_y_lo_hace_consultable() -> None:
    propuesta = _propuesta(
        referencias_eventos=("ev-1", "ev-2"),
        tecnicas_candidatas=("T1021.002",),
        explicaciones_alternativas=("Administración legítima",),
        evidencia_faltante=("Origen del binario remoto",),
    )
    modulo = _modulo((_evento("ev-1"), _evento("ev-2")), propuestas=(propuesta,))
    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    assert investigado.modalidad_inferencia is ModalidadInferencia.MODELO_LOCAL
    assert len(investigado.hallazgos) == 1
    hallazgo = investigado.hallazgos[0]
    assert hallazgo.caso_id == "caso-1"
    assert hallazgo.referencias_eventos == ("ev-1", "ev-2")
    assert hallazgo.tecnicas_candidatas == ("T1021.002",)
    assert hallazgo.procedencia_mapeo is ProcedenciaMapeo.MODELO
    assert hallazgo.estado_revision is EstadoRevision.PENDIENTE
    assert modulo.consultar_caso(caso.id).hallazgos == investigado.hallazgos


def test_una_referencia_inexistente_rechaza_el_hallazgo_y_no_lo_persiste() -> None:
    propuesta = _propuesta(referencias_eventos=("ev-inexistente",))
    modulo = _modulo((_evento("ev-1"),), propuestas=(propuesta,))
    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    assert investigado.hallazgos == ()
    assert any("ev-inexistente" in error for error in investigado.errores)
    assert modulo.consultar_caso(caso.id).hallazgos == ()


def test_un_hallazgo_invalido_no_descarta_los_hallazgos_validos() -> None:
    valida = _propuesta(hipotesis="Válida", referencias_eventos=("ev-1",))
    invalida = _propuesta(hipotesis="Inventada", referencias_eventos=("ev-inexistente",))
    modulo = _modulo((_evento("ev-1"),), propuestas=(valida, invalida))
    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    assert [hallazgo.hipotesis for hallazgo in investigado.hallazgos] == ["Válida"]
    assert any("ev-inexistente" in error for error in investigado.errores)


def test_sin_inferencia_conserva_la_cronologia_y_queda_en_modo_degradado() -> None:
    modulo = _modulo(
        (_evento("ev-1"), _evento("ev-2")),
        motor_inferencia=InferenciaNoDisponibleControlada("nodo privado caído"),
    )
    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))

    investigado = modulo.investigar_caso(caso.id)

    assert investigado.modalidad_inferencia is ModalidadInferencia.DEGRADADO
    assert investigado.eventos == caso.eventos
    assert investigado.hallazgos == ()
    assert any("nodo privado caído" in error for error in investigado.errores)


def test_exportar_produce_json_y_markdown_desde_el_estado_validado() -> None:
    propuesta = _propuesta(
        referencias_eventos=("ev-1",),
        tecnicas_candidatas=("T1021.002",),
        limitaciones=("No se observó el binario original",),
    )
    modulo = _modulo((_evento("ev-1"),), propuestas=(propuesta,))
    caso = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))
    modulo.investigar_caso(caso.id)

    contenido_json = modulo.exportar_caso(caso.id, FormatoExportacion.JSON)
    datos = json.loads(contenido_json)
    assert datos["id"] == "caso-1"
    assert datos["modalidad_inferencia"] == "modelo_local"
    assert datos["eventos"][0]["uid"] == "ev-1"
    assert datos["hallazgos"][0]["tecnicas_candidatas"] == ["T1021.002"]

    contenido_markdown = modulo.exportar_caso(caso.id, FormatoExportacion.MARKDOWN)
    assert "# Caso caso-1" in contenido_markdown
    assert "ev-1" in contenido_markdown
    assert "T1021.002" in contenido_markdown
    assert "No se observó el binario original" in contenido_markdown


def test_recorrido_completo_crear_investigar_consultar_exportar() -> None:
    propuesta = _propuesta(referencias_eventos=("ev-1", "ev-2"))
    modulo = _modulo((_evento("ev-1"), _evento("ev-2")), propuestas=(propuesta,))

    creado = modulo.crear_caso(Origen(ruta="fixtures/psexec.evtx", procedencia="laboratorio"))
    investigado = modulo.investigar_caso(creado.id)
    consultado = modulo.consultar_caso(creado.id)
    exportado = modulo.exportar_caso(creado.id, FormatoExportacion.JSON)

    assert consultado.id == investigado.id == creado.id
    assert consultado.eventos == investigado.eventos == creado.eventos
    assert consultado.hallazgos == investigado.hallazgos
    datos = json.loads(exportado)
    assert len(datos["hallazgos"]) == 1
    assert datos["hallazgos"][0]["hipotesis"] == propuesta.hipotesis
