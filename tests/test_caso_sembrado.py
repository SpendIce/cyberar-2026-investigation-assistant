import json

from investigacion.modelos import FormatoExportacion, ModalidadInferencia
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.sembrado import abrir_caso_sembrado


def test_el_caso_sembrado_se_abre_sin_servicios_externos() -> None:
    modulo, caso = abrir_caso_sembrado()

    assert isinstance(modulo, ModuloDeInvestigacion)
    assert caso.eventos
    assert caso.hallazgos
    assert caso.modalidad_inferencia is ModalidadInferencia.MODELO_LOCAL


def test_cada_referencia_del_hallazgo_sembrado_apunta_a_un_evento_existente() -> None:
    _, caso = abrir_caso_sembrado()

    uids = {evento.uid for evento in caso.eventos}
    for hallazgo in caso.hallazgos:
        assert hallazgo.referencias_eventos
        assert set(hallazgo.referencias_eventos) <= uids
        assert all(hallazgo.campos_citados)


def test_el_caso_sembrado_conserva_procedencia_y_versiones() -> None:
    _, caso = abrir_caso_sembrado()

    assert caso.origen.sha256
    assert caso.origen.procedencia
    assert caso.origen.versiones
    assert all(evento.localizador_original for evento in caso.eventos)


def test_el_caso_sembrado_exporta_markdown_y_json() -> None:
    modulo, caso = abrir_caso_sembrado()

    markdown = modulo.exportar_caso(caso.id, FormatoExportacion.MARKDOWN)
    contenido_json = modulo.exportar_caso(caso.id, FormatoExportacion.JSON)

    assert caso.id in markdown
    assert caso.hallazgos[0].hipotesis in markdown
    datos = json.loads(contenido_json)
    assert datos["id"] == caso.id
    assert datos["hallazgos"][0]["referencias_eventos"]
