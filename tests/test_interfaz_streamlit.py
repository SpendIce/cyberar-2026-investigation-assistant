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


def _abrir_primer_caso(at: AppTest) -> None:
    # La tarjeta es un componente CCv2: su click corre en el navegador, así
    # que el test abre el caso por el mismo canal que usa el trigger. El id
    # se deriva de la key del componente montado (card-<id>).
    clave = next(k for k in at.session_state.keys() if k.startswith("card-"))
    at.session_state["caso_abierto"] = clave.removeprefix("card-")
    at.run()


def test_la_interfaz_muestra_galeria_y_detalle_del_caso_sembrado() -> None:
    at = AppTest.from_file(str(APP))
    at.run()

    assert not at.exception
    textos = _textos(at)
    assert "Asistente privado de investigación" in textos
    # La tarjeta CCv2 monta su contenido en el navegador; en AppTest se
    # verifica la instancia por la key de estado del componente.
    assert any(k.startswith("card-") for k in at.session_state.keys())

    _abrir_primer_caso(at)

    assert not at.exception
    textos = _textos(at)
    assert "Custodia" in textos
    assert "Eventos (4)" in textos
    assert "Evidencia observada" in textos
    assert "Ejecución remota compatible con administración remota de servicios" in textos
    assert "T1021.002" in textos
    assert "ev-1" in textos
    assert "adaptadores controlados" in textos

    metricas = {metrica.label: metrica.value for metrica in at.metric}
    assert metricas["Eventos"] == "4"
    assert metricas["Hallazgos"] == "1"

    assert not any(header.value.startswith("Evento ") for header in at.header)


def test_abrir_una_referencia_muestra_el_evento_y_su_procedencia() -> None:
    at = AppTest.from_file(str(APP))
    at.run()
    _abrir_primer_caso(at)

    at.button(key="referencia-0-ev-3").click().run()

    assert not at.exception
    textos = _textos(at)
    assert "Evento ev-3" in textos
    assert "sha256-sembrado-determinista" in textos
    assert "evidence/WIN-CONTROL/Security/4103" in textos
    assert "hayabusa/smb_outbound_connection.yml" in textos


def test_la_cronologia_abre_eventos_y_se_puede_cerrar_el_detalle() -> None:
    at = AppTest.from_file(str(APP))
    at.run()
    _abrir_primer_caso(at)

    at.button(key="abrir-ev-4").click().run()

    assert "Evento ev-4" in _textos(at)

    at.button(key="cerrar-evento").click().run()

    assert "Evento ev-4" not in _textos(at)


def test_el_caso_se_exporta_desde_el_modal_de_la_interfaz() -> None:
    at = AppTest.from_file(str(APP))
    at.run()
    _abrir_primer_caso(at)

    at.button(key="abrir-exportar").click().run()

    assert not at.exception
    assert len(at.download_button) >= 2

    at.radio(key="formato-informe").set_value("JSON").run()

    assert not at.exception
