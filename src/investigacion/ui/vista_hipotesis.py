"""Pestaña Hipótesis IA: la interpretación del modelo, siempre marcada como tal.

Todo lo que esta pestaña muestra fue generado por el modelo y validado por
código antes de persistir. La marca "generado por IA" es persistente y las
interpretaciones permanecen pendientes de revisión humana.
"""

from __future__ import annotations

from typing import Literal

import streamlit as st

from investigacion.modelos import Caso, EstadoRevision
from investigacion.ui.metricas import nombre_tecnica
from investigacion.ui.presentacion import (
    eventos_referenciados,
    referencias_no_resueltas,
)
from investigacion.ui.servicio import ServicioDeCasos
from investigacion.validacion import contiene_lenguaje_concluyente, prosa_revisable

_MARCA_IA = "generado por IA"

_COLORES_REVISION: dict[EstadoRevision, Literal["gray", "green", "red"]] = {
    EstadoRevision.PENDIENTE: "gray",
    EstadoRevision.ACEPTADA: "green",
    EstadoRevision.RECHAZADA: "red",
}


def _abrir_evento(uid: str) -> None:
    st.session_state["evento_abierto"] = uid


def mostrar(servicio: ServicioDeCasos, caso: Caso) -> None:
    st.badge(_MARCA_IA, color="violet")
    st.caption(
        "Todo el contenido de esta pestaña lo produjo el modelo de lenguaje y "
        "quedó pendiente de revisión humana. Las referencias a eventos fueron "
        "verificadas por código; el sentido del texto, no."
    )
    if caso.contexto.strip():
        st.markdown(f"**Contexto declarado que alimentó esta narrativa:** {caso.contexto}")

    if not caso.hallazgos:
        st.info(
            "Sin hipótesis del modelo para este caso (abstención o modo "
            "degradado). La evidencia sigue navegable en Cronología y Hallazgos."
        )
        return

    for indice, hallazgo in enumerate(caso.hallazgos):
        with st.expander(f"Hipótesis {indice + 1} · revisión: {hallazgo.estado_revision.value}", expanded=True):
            st.badge(_MARCA_IA, color="violet")
            revision, aceptar, rechazar, _ = st.columns([2, 1, 1, 3])
            estado = hallazgo.estado_revision
            revision.badge(f"Revisión: {estado.value}", color=_COLORES_REVISION[estado])
            if aceptar.button("Aceptar", key=f"aceptar-{indice}"):
                servicio.modulo.revisar_hallazgo(
                    caso.id, indice, EstadoRevision.ACEPTADA
                )
                st.rerun()
            if rechazar.button("Rechazar", key=f"rechazar-{indice}"):
                servicio.modulo.revisar_hallazgo(
                    caso.id, indice, EstadoRevision.RECHAZADA
                )
                st.rerun()
            if contiene_lenguaje_concluyente(prosa_revisable(hallazgo)):
                st.error(
                    "Formulación no mostrada: utilizó lenguaje concluyente "
                    "incompatible con una hipótesis pendiente de revisión."
                )
                continue
            st.markdown(
                f"**Interpretación propuesta** "
                f"<span title='Texto producido por el modelo' style='cursor:help'>ⓘ</span>: "
                f"{hallazgo.hipotesis}",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Razón del vínculo:** {hallazgo.razon_vinculo}")
            if hallazgo.tecnicas_candidatas:
                chips = " ".join(
                    f"`{t}` {nombre_tecnica(t)}"
                    if nombre_tecnica(t) != t
                    else f"`{t}`"
                    for t in hallazgo.tecnicas_candidatas
                )
                st.markdown(f"**Técnicas candidatas sugeridas:** {chips}")
            st.caption(f"Procedencia del mapeo: {hallazgo.procedencia_mapeo}")
            for etiqueta, valores, vacio in (
                (
                    "Explicaciones alternativas",
                    hallazgo.explicaciones_alternativas,
                    "No declarada por el modelo",
                ),
                (
                    "Evidencia faltante / incertidumbre",
                    hallazgo.evidencia_faltante,
                    "No especificada",
                ),
                ("Limitaciones", hallazgo.limitaciones, "No especificada"),
            ):
                st.markdown(
                    f"**{etiqueta}:** " + ("; ".join(valores) if valores else vacio)
                )
            referenciados = eventos_referenciados(caso, hallazgo)
            if referenciados:
                st.markdown("**Evidencia observada** (referencias verificadas por código):")
                for evento in referenciados:
                    columnas = st.columns([2, 3, 1])
                    uid_corto = (
                        evento.uid
                        if len(evento.uid) <= 16
                        else f"{evento.uid[:15]}…"
                    )
                    columnas[0].markdown(f"`{uid_corto}`")
                    timestamp = (evento.timestamp_normalizado or "").replace(
                        "T", " "
                    )[:19]
                    columnas[1].markdown(timestamp or "sin timestamp")
                    columnas[2].button(
                        "Abrir",
                        key=f"referencia-{indice}-{evento.uid}",
                        on_click=_abrir_evento,
                        args=(evento.uid,),
                        help=f"Abrir evento {evento.uid}",
                    )
            for referencia in referencias_no_resueltas(caso, hallazgo):
                st.error(f"Referencia sin evento asociado: {referencia}")
