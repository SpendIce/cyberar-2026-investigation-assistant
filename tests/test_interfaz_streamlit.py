from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "src" / "investigacion" / "ui" / "app.py"


def _textos(at: AppTest) -> str:
    elementos = (
        list(at.title)
        + list(at.header)
        + list(at.subheader)
        + list(at.markdown)
        + list(at.caption)
        + list(at.text)
    )
    return "\n".join(str(elemento.value) for elemento in elementos)


def test_la_interfaz_muestra_estado_cronologia_y_hallazgo() -> None:
    at = AppTest.from_file(str(APP))
    at.run()

    assert not at.exception
    textos = _textos(at)
    assert "Asistente privado de investigación" in textos
    assert "Estado del caso" in textos
    assert "Cronología" in textos
    assert "Hallazgos" in textos
    assert "Ejecución remota compatible con administración remota de servicios" in textos
    assert "T1021.002" in textos
    assert "ev-1" in textos
    assert any("adaptadores controlados" in aviso.value for aviso in at.info)

    metricas = {metrica.label: metrica.value for metrica in at.metric}
    assert metricas["Eventos"] == "4"
    assert metricas["Hallazgos"] == "1"

    assert not any(header.value.startswith("Evento ") for header in at.header)


def test_abrir_una_referencia_muestra_el_evento_y_su_procedencia() -> None:
    at = AppTest.from_file(str(APP))
    at.run()

    at.button(key="referencia-0-ev-3").click().run()

    assert not at.exception
    assert any(header.value == "Evento ev-3" for header in at.header)
    textos = _textos(at)
    assert "sha256-sembrado-determinista" in textos
    assert "evidence/WIN-CONTROL/Security/4103" in textos
    assert "hayabusa/smb_outbound_connection.yml" in textos


def test_la_cronologia_abre_eventos_y_se_puede_cerrar_el_detalle() -> None:
    at = AppTest.from_file(str(APP))
    at.run()

    at.button(key="abrir-ev-4").click().run()

    assert any(header.value == "Evento ev-4" for header in at.header)

    at.button(key="cerrar-evento").click().run()

    assert not any(header.value.startswith("Evento ") for header in at.header)


def test_el_caso_se_exporta_en_markdown_y_json_desde_la_interfaz() -> None:
    at = AppTest.from_file(str(APP))
    at.run()

    markdown = "\n".join(str(bloque.value) for bloque in at.code)
    assert "Ejecución remota compatible" in markdown
    assert len(at.download_button) == 1

    at.radio(key="formato-exportacion").set_value("JSON").run()

    assert not at.exception
    contenido_json = "\n".join(str(bloque.value) for bloque in at.code)
    assert '"id"' in contenido_json
