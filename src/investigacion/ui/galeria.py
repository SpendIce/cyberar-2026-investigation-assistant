"""Galería de casos persistidos: la entrada exploratoria de la interfaz."""

from __future__ import annotations

from typing import Literal

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from investigacion.modelos import Caso, ModalidadInferencia
from investigacion.ui.dialogos import dialogo_alta, dialogo_baja
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


def _abrir(caso_id: str) -> None:
    st.session_state["caso_abierto"] = caso_id


def _tarjeta(servicio: ServicioDeCasos, caso: Caso, columna: DeltaGenerator) -> None:
    escenario = servicio.escenario_de(caso)
    with columna.container(border=True):
        st.markdown(f"**{servicio.titulo_de(caso)}**")
        modalidad = caso.modalidad_inferencia
        if modalidad is not None:
            etiqueta, color = _ETIQUETA_MODALIDAD.get(
                modalidad, (modalidad.value, "gray")
            )
            st.badge(etiqueta, color=color)
        if escenario is not None:
            st.badge(escenario.tipo_evidencia, color="blue")
        st.caption(
            f"{len(caso.eventos)} eventos · {len(caso.hallazgos)} hallazgos · "
            f"`{caso.id[:12]}`"
        )
        st.caption(f"Procedencia: {caso.origen.procedencia}")
        abrir, baja = st.columns(2)
        abrir.button(
            "Abrir caso",
            key=f"abrir-{caso.id}",
            type="primary",
            on_click=_abrir,
            args=(caso.id,),
        )
        baja.button(
            "Eliminar",
            key=f"baja-{caso.id}",
            on_click=lambda: st.session_state.update({"baja_pendiente": caso.id}),
        )


def mostrar(servicio: ServicioDeCasos) -> None:
    st.title("Asistente privado de investigación")
    st.warning(
        "Los hallazgos son hipótesis pendientes de revisión humana. PsExec, "
        "PowerShell, SMB y una técnica ATT&CK candidata no confirman por sí "
        "solos un compromiso."
    )
    if not servicio.puede_importar:
        st.info(
            "Sin ejecutable Hayabusa configurado la interfaz funciona en modo "
            "lectura sobre los casos persistidos."
        )
    encabezado, accion = st.columns([4, 1])
    encabezado.subheader("Casos")
    if accion.button("＋ Nuevo caso", type="primary", width="stretch"):
        dialogo_alta(servicio)

    casos = servicio.casos()
    if not casos:
        st.info(
            "No hay casos persistidos. Importá un EVTX con “Nuevo caso” o por "
            "CLI con `python -m investigacion.importar`."
        )
        return

    columnas = st.columns(3)
    for indice, caso in enumerate(casos):
        _tarjeta(servicio, caso, columnas[indice % 3])

    pendiente = st.session_state.pop("baja_pendiente", None)
    if pendiente:
        caso_baja = servicio.repositorio.obtener(pendiente)
        if caso_baja is not None:
            dialogo_baja(servicio, caso_baja)
