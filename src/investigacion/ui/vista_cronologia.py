"""Pestaña Cronología: línea de tiempo visual y tabla navegable de eventos."""

from __future__ import annotations

import streamlit as st

from investigacion.modelos import Caso, Evento
from investigacion.ui.presentacion import cronologia, procedencia_evento
from investigacion.ui.servicio import ServicioDeCasos


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


def _abrir_evento(uid: str) -> None:
    st.session_state["evento_abierto"] = uid


def _cerrar_evento() -> None:
    st.session_state["evento_abierto"] = None


def _mostrar_timeline(caso: Caso) -> None:
    filas = [
        {
            "timestamp": evento.timestamp_normalizado,
            "canal": evento.canal or "sin canal",
            "tipo": evento.tipo_evento or "evento",
            "uid": evento.uid,
            "proceso": evento.proceso or "",
            "regla": "con detección" if evento.regla_hayabusa else "sin detección",
        }
        for evento in cronologia(caso)
        if evento.timestamp_normalizado
    ]
    if not filas:
        st.caption("Sin timestamps normalizados para dibujar la línea de tiempo.")
        return
    # Importación perezosa: pandas es pesado y encarecería cada arranque.
    import altair as alt
    import pandas as pd  # type: ignore[import-untyped]

    datos = pd.DataFrame(filas)
    datos["cuando"] = pd.to_datetime(datos["timestamp"], utc=True, errors="coerce")
    datos = datos.dropna(subset=["cuando"])
    if datos.empty:
        st.caption("Los timestamps no pudieron interpretarse como fechas.")
        return
    grafico = (
        alt.Chart(datos)
        .mark_circle(size=90)
        .encode(
            x=alt.X("cuando:T", title="Tiempo (UTC)"),
            y=alt.Y("canal:N", title="Canal"),
            color=alt.Color(
                "regla:N",
                title="Detección",
                scale=alt.Scale(
                    domain=["con detección", "sin detección"],
                    range=["#e5484d", "#8b8d98"],
                ),
            ),
            tooltip=["uid", "cuando:T", "canal", "tipo", "proceso", "regla"],
        )
        .properties(height=220)
        .interactive()
    )
    st.altair_chart(grafico, width="stretch")


def _mostrar_detalle_evento(caso: Caso) -> None:
    uid = st.session_state.get("evento_abierto")
    if not uid:
        return
    evento = next((item for item in caso.eventos if item.uid == uid), None)
    if evento is None:
        return
    st.divider()
    st.markdown(f"#### Evento {evento.uid}")
    st.button("Cerrar evento", key="cerrar-evento", on_click=_cerrar_evento)
    datos, procedencia = st.columns(2)
    with datos:
        st.markdown("**Datos normalizados**")
        for etiqueta, valor in _campos_evento(evento):
            st.markdown(f"- **{etiqueta}:** {valor}")
        st.markdown("- **Contenido:**")
        # Literal: contiene sintaxis de comandos que no debe interpretarse.
        st.code(evento.contenido or "sin contenido")
    with procedencia:
        st.markdown("**Procedencia**")
        for etiqueta, valor in procedencia_evento(caso, evento):
            st.markdown(f"- **{etiqueta}:** {valor}")


def mostrar(servicio: ServicioDeCasos, caso: Caso) -> None:
    _mostrar_timeline(caso)
    _mostrar_detalle_evento(caso)
    st.subheader(f"Eventos ({len(caso.eventos)})")
    for evento in cronologia(caso):
        columnas = st.columns([1, 2, 2, 2, 2, 1])
        columnas[0].markdown(f"`{evento.uid}`")
        columnas[1].markdown(evento.timestamp_normalizado or "sin timestamp")
        columnas[2].markdown(evento.canal or "sin canal")
        columnas[3].markdown(evento.tipo_evento or "evento")
        columnas[4].markdown(evento.proceso or "sin proceso")
        columnas[5].button(
            "Abrir",
            key=f"abrir-{evento.uid}",
            on_click=_abrir_evento,
            args=(evento.uid,),
        )
