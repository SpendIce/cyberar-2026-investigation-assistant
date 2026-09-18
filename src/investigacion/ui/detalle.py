"""Detalle de un caso: encabezado, procedencia y navegación por pestañas."""

from __future__ import annotations

from typing import Literal

import streamlit as st

from investigacion.errores import CasoNoEncontrado
from investigacion.modelos import ModalidadInferencia
from investigacion.ui import (
    vista_cronologia,
    vista_exportar,
    vista_hallazgos,
    vista_hipotesis,
    vista_resumen,
)
from investigacion.ui.servicio import ServicioDeCasos

_ColorBadge = Literal[
    "red", "orange", "yellow", "blue", "green", "violet", "gray", "grey", "primary"
]

_ETIQUETA_MODALIDAD: dict[ModalidadInferencia, tuple[str, _ColorBadge]] = {
    ModalidadInferencia.NODO_PRIVADO: ("nodo privado", "green"),
    ModalidadInferencia.MODELO_LOCAL: ("modelo local", "green"),
    ModalidadInferencia.MODELO_EXTERNO: ("modelo externo", "orange"),
    ModalidadInferencia.DEGRADADO: ("modo degradado", "gray"),
}


def _volver() -> None:
    st.session_state.pop("caso_abierto", None)
    st.session_state.pop("evento_abierto", None)


def mostrar(servicio: ServicioDeCasos, caso_id: str) -> None:
    try:
        caso = servicio.modulo.consultar_caso(caso_id)
    except CasoNoEncontrado:
        st.session_state.pop("caso_abierto", None)
        st.error("El caso ya no existe.")
        st.rerun()
        return

    with st.container(horizontal=True):
        if st.button("← Casos", key="volver"):
            _volver()
            st.rerun()
        vista_exportar.boton_exportar(servicio, caso)

    st.title(servicio.titulo_de(caso))
    modalidad = caso.modalidad_inferencia
    if modalidad is not None:
        etiqueta, color = _ETIQUETA_MODALIDAD.get(modalidad, (modalidad.value, "gray"))
        st.badge(f"Inferencia: {etiqueta}", color=color)
    escenario = servicio.escenario_de(caso)
    if escenario is not None:
        st.badge(f"Escenario: {escenario.tipo_evidencia}", color="blue")
        st.caption(escenario.descripcion)

    tabs = st.tabs(["Resumen", "Cronología", "Hallazgos", "Hipótesis IA"])
    with tabs[0]:
        vista_resumen.mostrar(servicio, caso)
    with tabs[1]:
        vista_cronologia.mostrar(servicio, caso)
    with tabs[2]:
        vista_hallazgos.mostrar(servicio, caso)
    with tabs[3]:
        vista_hipotesis.mostrar(servicio, caso)
