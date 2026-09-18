"""Diálogos modales de la interfaz: alta de caso, baja y detalle de evento."""

from __future__ import annotations

import json

import streamlit as st

from investigacion.errores import CasoNoEncontrado, ErrorDeImportacion
from investigacion.modelos import Caso, Evento
from investigacion.ui.presentacion import procedencia_evento
from investigacion.ui.servicio import ServicioDeCasos


@st.dialog("Nuevo caso", width="large")
def dialogo_alta(servicio: ServicioDeCasos) -> None:
    st.caption(
        "El EVTX se procesa con Hayabusa (detección defensiva) y luego con el "
        "motor de inferencia configurado. La investigación puede demorar; el "
        "caso queda persistido aunque la inferencia falle (modo degradado)."
    )
    archivo = st.file_uploader(
        "Archivo EVTX",
        type=["evtx"],
        help="Arrastrá un registro de eventos Windows exportado (.evtx)",
    )
    procedencia = st.text_input(
        "Procedencia",
        help="De dónde sale el archivo: qué host, quién lo exportó, cuándo.",
    )
    contexto = st.text_area(
        "Contexto del ambiente",
        help=(
            "Lo que el operador sabe del ambiente: rol del host, actividad "
            "esperada, herramientas autorizadas. Viaja al prompt del modelo "
            "declarado como contexto, no como instrucción."
        ),
        placeholder="Ej.: WIN-FS01 es un fileserver de producción; no corre PsExec en horario laboral…",
    )
    if not servicio.puede_importar:
        st.warning(
            "La importación está deshabilitada: no se encontró el ejecutable "
            "Hayabusa (variable `HAYABUSA` o `~/tools/hayabusa-4.1.0/`)."
        )
        return
    if st.button(
        "Importar e investigar",
        type="primary",
        disabled=archivo is None or not procedencia.strip(),
    ):
        assert archivo is not None
        with st.spinner("Importando: Hayabusa procesa el EVTX y luego corre la inferencia…"):
            try:
                caso = servicio.importar_upload(
                    archivo.name, archivo.getvalue(), procedencia, contexto
                )
            except (ErrorDeImportacion, RuntimeError, OSError) as exc:
                st.error(f"No se pudo importar: {exc}")
                return
        st.session_state["caso_abierto"] = caso.id
        st.rerun()


@st.dialog("Eliminar caso")
def dialogo_baja(servicio: ServicioDeCasos, caso: Caso) -> None:
    st.warning(
        f"Vas a eliminar **{servicio.titulo_de(caso)}** (`{caso.id}`). "
        "El caso y su cadena de custodia dejan de existir en el repositorio. "
        "Los artefactos de evidencia en disco se conservan."
    )
    confirmar, cancelar = st.columns(2)
    if confirmar.button("Eliminar definitivamente", type="primary"):
        try:
            servicio.modulo.eliminar_caso(caso.id)
        except CasoNoEncontrado:
            st.error("El caso ya no existe.")
            return
        st.session_state.pop("caso_abierto", None)
        st.rerun()
    if cancelar.button("Cancelar"):
        st.rerun()


def _campos_evento(evento: Evento) -> tuple[tuple[str, str], ...]:
    return (
        ("Timestamp original", evento.timestamp_original or "no declarado"),
        ("Timestamp normalizado", evento.timestamp_normalizado or "no declarado"),
        ("Host", evento.host or "no declarado"),
        ("Usuario", evento.usuario or "no declarado"),
        ("Canal", evento.canal or "no declarado"),
        ("Tipo de evento", evento.tipo_evento or "no declarado"),
        ("Proceso", evento.proceso or "no declarado"),
        ("Proceso padre", evento.proceso_padre or "no declarado"),
    )


def _contenido_legible(contenido: str | None) -> tuple[str, str]:
    """(texto, lenguaje) para mostrar `contenido` de forma legible.

    El adaptador Hayabusa persiste JSON compacto en una sola línea (ver
    `hayabusa.py`); reformatearlo con indentación es sólo presentación, no
    toca el dato persistido. Si no es JSON (por ejemplo el caso sembrado, con
    texto plano), se muestra tal cual.
    """
    if not contenido:
        return "sin contenido", "text"
    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError:
        return contenido, "text"
    return json.dumps(datos, indent=2, ensure_ascii=False), "json"


def _cerrar_evento() -> None:
    st.session_state.pop("evento_abierto", None)


@st.dialog("Evento", width="large", on_dismiss=_cerrar_evento)
def dialogo_evento(caso: Caso, evento: Evento) -> None:
    """Detalle de un evento citado, como pantalla modal en vez de panel inline.

    Un panel inline al final de la cronología o de un hallazgo obligaba a
    hacer scroll para verlo, y sólo existía si la pestaña activa lo dibujaba
    explícitamente. El modal aparece centrado sin importar el scroll ni la
    pestaña, y `on_dismiss` limpia `evento_abierto` al cerrarlo con la X, un
    clic afuera o Esc: si no, la próxima vez que este caso se renderice
    volvería a abrirse solo.
    """
    st.markdown(f"#### Evento {evento.uid}")
    datos, procedencia = st.columns(2)
    with datos:
        st.markdown("**Datos normalizados**")
        for etiqueta, valor in _campos_evento(evento):
            st.markdown(f"- **{etiqueta}:** {valor}")
    with procedencia:
        st.markdown("**Procedencia**")
        for etiqueta, valor in procedencia_evento(caso, evento):
            st.markdown(f"- **{etiqueta}:** {valor}")
    st.markdown("**Contenido**")
    texto, lenguaje = _contenido_legible(evento.contenido)
    # Literal: contiene sintaxis de comandos que no debe interpretarse.
    st.code(texto, language=lenguaje, wrap_lines=True)
    if st.button("Cerrar", key="cerrar-evento"):
        _cerrar_evento()
        st.rerun()
