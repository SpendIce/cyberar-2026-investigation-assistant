"""Pestaña Hallazgos: números Sigma, matriz ATT&CK y hallazgos con evidencia."""

from __future__ import annotations

import html
from typing import Literal

import streamlit as st

from investigacion.modelos import Caso, EstadoRevision
from investigacion.ui.metricas import (
    mapa_attack,
    numeros_sigma,
    tacticas_orden,
    tecnicas_del_modelo,
    tecnicas_heredadas,
)
from investigacion.ui.presentacion import (
    eventos_referenciados,
    referencias_no_resueltas,
)
from investigacion.ui.servicio import ServicioDeCasos
from investigacion.validacion import contiene_lenguaje_concluyente, prosa_revisable


def _abrir_evento(uid: str) -> None:
    st.session_state["evento_abierto"] = uid


def _mostrar_numeros_sigma(caso: Caso) -> None:
    numeros = numeros_sigma(caso)
    st.subheader("Detección defensiva (Sigma/Hayabusa)")
    columnas = st.columns(5)
    columnas[0].metric(
        "Eventos con detección",
        f"{numeros['eventos_con_deteccion']}/{numeros['eventos_total']}",
    )
    columnas[1].metric("Detecciones", numeros["detecciones"])
    columnas[2].metric("Reglas que activaron", numeros["reglas_distintas"])
    columnas[3].metric("Técnicas heredadas de regla", numeros["tecnicas_heredadas"])
    columnas[4].metric(
        "Técnicas sugeridas por el modelo", len(tecnicas_del_modelo(caso))
    )
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
    del_modelo = tecnicas_del_modelo(caso)
    mapa = mapa_attack()
    por_tactica: dict[str, list[str]] = {t: [] for t in tacticas_orden()}
    for tecnica, tacticas in mapa["tecnicas"].items():
        for tactica in tacticas:
            if tactica in por_tactica:
                por_tactica[tactica].append(tecnica)

    filas = []
    for tactica in tacticas_orden():
        tecnicas = por_tactica[tactica]
        if not tecnicas:
            continue
        chips = []
        for tecnica in tecnicas:
            if tecnica in heredadas and tecnica in del_modelo:
                chips.append(
                    _chip(tecnica, "#7c3aed", f"regla + modelo: {heredadas[tecnica]}")
                )
            elif tecnica in heredadas:
                chips.append(_chip(tecnica, "#2563eb", f"regla: {heredadas[tecnica]}"))
            elif tecnica in del_modelo:
                chips.append(
                    _chip(tecnica, "#9333ea", f"modelo: {del_modelo[tecnica]}")
                )
        if chips:
            filas.append(
                f"<div style='margin:.35em 0'><b>{html.escape(tactica)}</b>: "
                + " ".join(chips)
                + "</div>"
            )
    if filas:
        st.markdown(
            " ".join(
                [
                    "<span style='background:#2563eb;color:#fff;padding:1px 6px;"
                    "border-radius:4px;font-size:.75em'>heredado de regla</span>",
                    "<span style='background:#9333ea;color:#fff;padding:1px 6px;"
                    "border-radius:4px;font-size:.75em'>sugerida por el modelo</span>",
                    "<span style='background:#7c3aed;color:#fff;padding:1px 6px;"
                    "border-radius:4px;font-size:.75em'>ambas</span>",
                ]
            ),
            unsafe_allow_html=True,
        )
        st.markdown("".join(filas), unsafe_allow_html=True)
    else:
        st.caption("Ninguna técnica del caso coincide con la cobertura del release fijado.")
    st.caption(
        f"La cobertura de fondo son las {len(mapa['tecnicas'])} técnicas con al "
        "menos una regla en la distribución Hayabusa fijada; sólo se dibujan las "
        "tácticas donde el caso tiene actividad. Que una técnica aparezca no "
        "implica compromiso: es un candidato sujeto a revisión."
    )
    with st.expander("Ver la cobertura completa del release (todas las tácticas)"):
        lineas = []
        for tactica in tacticas_orden():
            tecnicas = por_tactica[tactica]
            if not tecnicas:
                continue
            chips = []
            for tecnica in tecnicas:
                if tecnica in heredadas or tecnica in del_modelo:
                    chips.append(_chip(tecnica, "#2563eb", tecnica))
                else:
                    chips.append(
                        f'<span style="display:inline-block;background:#3a3b3f;'
                        f'color:#9d9da8;padding:2px 7px;margin:2px;border-radius:4px;'
                        f'font-size:.75em;font-family:monospace">{tecnica}</span>'
                    )
            lineas.append(
                f"<div style='margin:.3em 0'><b>{html.escape(tactica)}</b> "
                f"({len(tecnicas)}): " + " ".join(chips) + "</div>"
            )
        st.markdown("".join(lineas), unsafe_allow_html=True)


def _mostrar_hallazgo(servicio: ServicioDeCasos, caso: Caso, indice: int) -> None:
    hallazgo = caso.hallazgos[indice]
    concluyente = contiene_lenguaje_concluyente(prosa_revisable(hallazgo))
    encabezado, revision = st.columns([3, 2])
    encabezado.markdown(f"### Hipótesis {indice + 1}")
    estado = hallazgo.estado_revision
    colores: dict[EstadoRevision, Literal["gray", "green", "red"]] = {
        EstadoRevision.PENDIENTE: "gray",
        EstadoRevision.ACEPTADA: "green",
        EstadoRevision.RECHAZADA: "red",
    }
    color = colores[estado]
    revision.badge(f"Revisión: {estado.value}", color=color)
    aceptar, rechazar, _ = revision.columns(3)
    if aceptar.button("Aceptar", key=f"aceptar-{indice}"):
        servicio.modulo.revisar_hallazgo(caso.id, indice, EstadoRevision.ACEPTADA)
        st.rerun()
    if rechazar.button("Rechazar", key=f"rechazar-{indice}"):
        servicio.modulo.revisar_hallazgo(caso.id, indice, EstadoRevision.RECHAZADA)
        st.rerun()

    if concluyente:
        st.error(
            "Formulación no mostrada: utilizó lenguaje concluyente incompatible "
            "con una hipótesis pendiente de revisión."
        )
    else:
        st.markdown(f"**{hallazgo.hipotesis}**")
    st.markdown(
        "**Técnicas candidatas:** "
        + (", ".join(hallazgo.tecnicas_candidatas) or "ninguna")
    )
    st.markdown(f"**Procedencia del mapeo:** {hallazgo.procedencia_mapeo.value}")
    st.markdown("**Evidencia observada:**")
    for evento in eventos_referenciados(caso, hallazgo):
        columnas = st.columns([3, 3, 3])
        columnas[0].markdown(f"`{evento.uid}`")
        columnas[1].markdown(evento.timestamp_normalizado or "sin timestamp")
        columnas[2].button(
            f"Abrir {evento.uid}",
            key=f"referencia-{indice}-{evento.uid}",
            on_click=_abrir_evento,
            args=(evento.uid,),
        )
    for referencia in referencias_no_resueltas(caso, hallazgo):
        st.error(f"Referencia sin evento asociado: {referencia}")


def mostrar(servicio: ServicioDeCasos, caso: Caso) -> None:
    _mostrar_numeros_sigma(caso)
    _mostrar_matriz(caso)
    st.subheader(f"Hallazgos ({len(caso.hallazgos)})")
    if not caso.hallazgos:
        st.info(
            "El modelo no formuló hipótesis validadas. Esto no equivale a "
            "actividad legítima ni a compromiso: la cronología y la evidencia "
            "permanecen disponibles para revisión humana."
        )
        return
    for indice in range(len(caso.hallazgos)):
        _mostrar_hallazgo(servicio, caso, indice)
        st.divider()
