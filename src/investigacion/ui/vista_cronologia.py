"""Pestaña Cronología: línea de tiempo visual y tabla navegable de eventos."""

from __future__ import annotations

import streamlit as st

from investigacion.modelos import Caso, Evento
from investigacion.ui.metricas import detecciones_evento, severidad_evento
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


_SEVERIDADES = ("critical", "high", "medium", "low", "informational", "sin detección")

_COLORES_SEVERIDAD = ("#ff4d4f", "#ff7a45", "#faad14", "#ffd666", "#5b8def", "#4b4e57")


def _leer_seleccion(estado: object) -> str | None:
    """uid del punto seleccionado en el gráfico, tolerante a la forma del estado."""
    seleccion = getattr(estado, "selection", estado)
    if not isinstance(seleccion, dict):
        return None
    for valor in seleccion.values():
        if isinstance(valor, list):
            for item in valor:
                if isinstance(item, dict) and item.get("uid"):
                    return str(item["uid"])
    return None


def _mostrar_timeline(caso: Caso) -> None:
    filas = [
        {
            "timestamp": evento.timestamp_normalizado,
            "canal": evento.canal or "sin canal",
            "tipo": evento.tipo_evento or "evento",
            "uid": evento.uid,
            "uid_corto": evento.uid[:12],
            "proceso": evento.proceso or "",
            "severidad": severidad_evento(evento),
            "detecciones": detecciones_evento(evento),
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
    st.caption(
        "Cada punto es un evento con detección temporal: el color es la "
        "severidad máxima que disparó y el tamaño, cuántas reglas activó. "
        "Clic sobre un punto para abrir el evento."
    )
    puntos = alt.selection_point(name="pick", fields=["uid"])
    grafico = (
        alt.Chart(datos)
        .mark_circle()
        .encode(
            x=alt.X("cuando:T", title="Tiempo (UTC)"),
            y=alt.Y("canal:N", title="Canal"),
            color=alt.Color(
                "severidad:N",
                title="Severidad máxima",
                scale=alt.Scale(
                    domain=list(_SEVERIDADES), range=list(_COLORES_SEVERIDAD)
                ),
            ),
            size=alt.Size(
                "detecciones:Q",
                title="Detecciones",
                scale=alt.Scale(range=[80, 420]),
                legend=None,
            ),
            opacity=alt.condition(puntos, alt.value(1), alt.value(0.75)),
            tooltip=[
                alt.Tooltip("uid_corto", title="Evento"),
                alt.Tooltip("cuando:T", title="Timestamp"),
                alt.Tooltip("canal", title="Canal"),
                alt.Tooltip("tipo", title="EventID"),
                alt.Tooltip("proceso", title="Proceso"),
                alt.Tooltip("severidad", title="Severidad"),
                alt.Tooltip("detecciones", title="Detecciones"),
            ],
        )
        .add_params(puntos)
        .properties(height=240)
        .interactive(bind_y=False)
    )
    estado = st.altair_chart(
        grafico, width="stretch", on_select="rerun", key=f"timeline-{caso.id}"
    )
    uid = _leer_seleccion(estado)
    if uid:
        _abrir_evento(uid)


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
    encabezados = st.columns([1, 2, 2, 2, 2, 1])
    for columna, titulo in zip(
        encabezados, ("Evento", "Timestamp (UTC)", "Canal", "Tipo", "Proceso", "")
    ):
        columna.caption(f"**{titulo}**")
    for evento in cronologia(caso):
        columnas = st.columns([1, 2, 2, 2, 2, 1])
        uid_corto = evento.uid if len(evento.uid) <= 14 else f"{evento.uid[:13]}…"
        columnas[0].markdown(f"`{uid_corto}`")
        timestamp = (evento.timestamp_normalizado or "").replace("T", " ")[:19]
        columnas[1].markdown(timestamp or "sin timestamp")
        columnas[2].markdown(evento.canal or "sin canal")
        columnas[3].markdown(evento.tipo_evento or "evento")
        columnas[4].markdown(evento.proceso or "sin proceso")
        columnas[5].button(
            "Abrir",
            key=f"abrir-{evento.uid}",
            on_click=_abrir_evento,
            args=(evento.uid,),
        )
