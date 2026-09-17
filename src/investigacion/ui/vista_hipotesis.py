"""Pestaña Hipótesis IA: la interpretación del modelo, siempre marcada como tal.

Todo lo que esta pestaña muestra fue generado por el modelo y validado por
código antes de persistir. La marca "generado por IA" es persistente y las
interpretaciones permanecen pendientes de revisión humana.
"""

from __future__ import annotations

import streamlit as st

from investigacion.modelos import Caso
from investigacion.ui.presentacion import eventos_referenciados
from investigacion.ui.servicio import ServicioDeCasos
from investigacion.validacion import contiene_lenguaje_concluyente, prosa_revisable

_MARCA_IA = "generado por IA"


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
                st.caption(
                    "Eventos citados (verificados por código): "
                    + ", ".join(f"`{e.uid}`" for e in referenciados)
                )
