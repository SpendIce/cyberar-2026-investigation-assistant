"""Galería de casos persistidos: la entrada exploratoria de la interfaz."""

from __future__ import annotations

from typing import Literal

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from investigacion.modelos import Caso, ModalidadInferencia
from investigacion.ui.dialogos import dialogo_alta, dialogo_baja
from investigacion.ui.metricas import detecciones, hosts_del_caso
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

_OPCIONES_MODALIDAD = ("todas", "modelo externo", "modelo local", "modo degradado")


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
        hosts = hosts_del_caso(caso)
        st.caption(
            f"{len(caso.eventos)} eventos · {len(detecciones(caso))} detecciones · "
            f"{len(caso.hallazgos)} hallazgos"
        )
        st.caption(
            f"Host: {', '.join(hosts) if hosts else 'no declarado'}"
        )
        st.markdown(
            '<div class="abrir-hint">Abrir caso →</div>', unsafe_allow_html=True
        )
        st.markdown('<span class="card-open"></span>', unsafe_allow_html=True)
        st.button(
            "Abrir caso",
            key=f"abrir-{caso.id}",
            on_click=_abrir,
            args=(caso.id,),
        )
        st.markdown('<span class="card-del"></span>', unsafe_allow_html=True)
        st.button(
            "✕",
            key=f"baja-{caso.id}",
            help="Eliminar caso",
            on_click=lambda: st.session_state.update({"baja_pendiente": caso.id}),
        )


def _filtrar(servicio: ServicioDeCasos) -> tuple[Caso, ...]:
    casos = servicio.casos()
    busqueda = st.session_state.get("busqueda-casos", "").strip().casefold()
    modalidad = st.session_state.get("filtro-modalidad", "todas")
    if modalidad != "todas":
        casos = tuple(
            caso
            for caso in casos
            if caso.modalidad_inferencia is not None
            and _ETIQUETA_MODALIDAD.get(
                caso.modalidad_inferencia, (caso.modalidad_inferencia.value, "gray")
            )[0]
            == modalidad
        )
    if busqueda:
        casos = tuple(
            caso
            for caso in casos
            if busqueda in servicio.titulo_de(caso).casefold()
            or busqueda in " ".join(hosts_del_caso(caso)).casefold()
            or busqueda in caso.id.casefold()
        )
    return casos


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

    todos = servicio.casos()
    if not todos:
        st.info(
            "No hay casos persistidos. Importá un EVTX con “Nuevo caso” o por "
            "CLI con `python -m investigacion.importar`."
        )
        return

    busqueda, filtro, _ = st.columns([3, 2, 3])
    busqueda.text_input(
        "Buscar", placeholder="título, host o id…", key="busqueda-casos",
        label_visibility="collapsed",
    )
    filtro.segmented_control(
        "Modalidad",
        options=_OPCIONES_MODALIDAD,
        default="todas",
        key="filtro-modalidad",
        label_visibility="collapsed",
    )

    casos = _filtrar(servicio)
    if not casos:
        st.caption("Ningún caso coincide con el filtro.")
        return

    columnas = st.columns(4)
    for indice, caso in enumerate(casos):
        _tarjeta(servicio, caso, columnas[indice % 4])

    pendiente = st.session_state.pop("baja_pendiente", None)
    if pendiente:
        caso_baja = servicio.repositorio.obtener(pendiente)
        if caso_baja is not None:
            dialogo_baja(servicio, caso_baja)
