"""Diálogos modales de la interfaz: alta de caso y confirmación de baja."""

from __future__ import annotations

import streamlit as st

from investigacion.errores import CasoNoEncontrado, ErrorDeImportacion
from investigacion.modelos import Caso
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
