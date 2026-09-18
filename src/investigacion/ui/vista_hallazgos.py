"""Pestaña Hallazgos: números Sigma, matriz ATT&CK y hallazgos con evidencia."""

from __future__ import annotations

import html

import streamlit as st

from investigacion.adaptadores.hayabusa import detecciones_de
from investigacion.modelos import Caso
from investigacion.ui.metricas import (
    mapa_attack,
    nombre_tecnica,
    numeros_sigma,
    tacticas_orden,
    tecnicas_heredadas,
)
from investigacion.ui.presentacion import cronologia
from investigacion.ui.servicio import ServicioDeCasos


def _abrir_evento(uid: str) -> None:
    st.session_state["evento_abierto"] = uid


def _mostrar_numeros_sigma(caso: Caso) -> None:
    numeros = numeros_sigma(caso)
    st.subheader("Detección defensiva (Sigma/Hayabusa)")
    columnas = st.columns(4)
    columnas[0].metric(
        "Eventos con detección",
        f"{numeros['eventos_con_deteccion']}/{numeros['eventos_total']}",
    )
    columnas[1].metric("Detecciones", numeros["detecciones"])
    columnas[2].metric("Reglas que activaron", numeros["reglas_distintas"])
    columnas[3].metric("Técnicas heredadas de regla", numeros["tecnicas_heredadas"])
    st.caption(
        "Los números los calcula código desde la salida de Hayabusa preservada "
        "en cada evento; ningún conteo proviene del modelo."
    )


def _chip(tecnica: str, color: str, titulo: str) -> str:
    return (
        f'<span title="{html.escape(titulo)}" style="display:inline-block;'
        f"background:{color};color:#fff;padding:2px 7px;margin:2px;"
        f'border-radius:4px;font-size:.8em;font-family:monospace">'
        f"{html.escape(tecnica)}</span>"
    )


def _mostrar_matriz(caso: Caso) -> None:
    st.subheader("Matriz ATT&CK del caso")
    heredadas = tecnicas_heredadas(caso)
    mapa = mapa_attack()
    por_tactica: dict[str, list[str]] = {t: [] for t in tacticas_orden()}
    for tecnica, tacticas in mapa["tecnicas"].items():
        if tecnica not in heredadas:
            continue
        for tactica in tacticas:
            if tactica in por_tactica:
                por_tactica[tactica].append(tecnica)

    filas = []
    for tactica in tacticas_orden():
        tecnicas = por_tactica[tactica]
        chips = [
            _chip(
                nombre_tecnica(tecnica),
                "#2563eb",
                f"{tecnica} · regla: {heredadas[tecnica]}",
            )
            for tecnica in tecnicas
        ]
        if chips:
            filas.append(
                f"<div style='margin:.35em 0'><b>{html.escape(tactica)}</b>: "
                + " ".join(chips)
                + "</div>"
            )
    if filas:
        st.markdown("".join(filas), unsafe_allow_html=True)
    else:
        st.caption("Ninguna técnica del caso coincide con la cobertura del release fijado.")
    st.caption(
        "Sólo se dibujan las técnicas que las reglas observaron en el caso; "
        "el id exacto y la regla de origen quedan en el tooltip de cada chip. "
        "Que una técnica aparezca no implica compromiso: es un candidato "
        "sujeto a revisión. Las técnicas sugeridas por el modelo están en "
        "la pestaña Hipótesis IA."
    )


_COLORES_NIVEL = {
    "critical": "red",
    "high": "orange",
    "medium": "yellow",
    "low": "blue",
    "informational": "violet",
}


def _mostrar_incidentes(caso: Caso) -> None:
    """Los incidentes que las reglas Hayabusa reconocieron en la evidencia."""
    filas = [
        (evento, fila)
        for evento in cronologia(caso)
        for fila in detecciones_de(evento)
    ]
    st.subheader(f"Incidentes reconocidos por Hayabusa ({len(filas)})")
    if not filas:
        st.caption(
            "Ningún evento del caso disparó reglas: no implica actividad "
            "legítima ni compromiso, sólo ausencia de detecciones."
        )
        return
    encabezados = st.columns([1, 4, 2, 2, 1])
    for columna, titulo in zip(
        encabezados, ("Señal", "Regla", "Timestamp", "Evento", "")
    ):
        columna.caption(f"**{titulo}**")
    for indice, (evento, fila) in enumerate(filas):
        columnas = st.columns([1, 4, 2, 2, 1])
        nivel = str(fila.get("Level") or "informational")
        color = _COLORES_NIVEL.get(nivel, "gray")
        columnas[0].markdown(f":{color}[{nivel}]")
        columnas[1].markdown(
            str(fila.get("RuleTitle") or fila.get("RuleFile") or "regla")
        )
        timestamp = (evento.timestamp_normalizado or "").replace("T", " ")[:19]
        columnas[2].markdown(timestamp or "sin timestamp")
        uid_corto = (
            evento.uid if len(evento.uid) <= 16 else f"{evento.uid[:15]}…"
        )
        columnas[3].markdown(f"`{uid_corto}`")
        columnas[4].button(
            "Abrir",
            key=f"incidente-{indice}-{evento.uid}",
            on_click=_abrir_evento,
            args=(evento.uid,),
            help=f"Abrir evento {evento.uid}",
        )


def mostrar(servicio: ServicioDeCasos, caso: Caso) -> None:
    _mostrar_numeros_sigma(caso)
    _mostrar_matriz(caso)
    _mostrar_incidentes(caso)
