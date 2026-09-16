"""Interfaz Streamlit: abre un caso y navega hallazgo → evidencia.

Es un adaptador de presentación. No contiene reglas de investigación: crea y
consulta el caso a través del módulo y dibuja lo que éste ya validó. Con la
variable `INVESTIGACION_DATOS` apuntando al directorio de datos de una
importación real, abre los casos persistidos en `casos.sqlite` en lugar del
caso sembrado.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import streamlit as st

from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.exportacion import exportar
from investigacion.modelos import Caso, Evento, FormatoExportacion
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.sembrado import abrir_caso_sembrado
from investigacion.ui.presentacion import (
    cronologia,
    estado_caso,
    eventos_referenciados,
    procedencia_evento,
    referencias_no_resueltas,
)

_EXPORTACION: dict[str, tuple[FormatoExportacion, str, str, str]] = {
    "Markdown": (FormatoExportacion.MARKDOWN, "md", "text/markdown", "markdown"),
    "JSON": (FormatoExportacion.JSON, "json", "application/json", "json"),
}


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
        ("Contenido", evento.contenido or "sin contenido"),
    )


def _abrir_evento(uid: str) -> None:
    st.session_state["evento_abierto"] = uid


def _cerrar_evento() -> None:
    st.session_state["evento_abierto"] = None


def _caso_persistido(directorio_datos: str) -> Caso:
    repositorio = RepositorioSQLite(Path(directorio_datos) / "casos.sqlite")
    identificadores = repositorio.listar()
    if not identificadores:
        st.warning(
            f"Sin casos persistidos en {Path(directorio_datos) / 'casos.sqlite'}. "
            "Importar un EVTX con `python -m investigacion.importar` primero."
        )
        st.stop()
    caso_id = st.selectbox(
        "Caso persistido",
        options=identificadores,
        key="caso-persistido",
        on_change=_cerrar_evento,
    )
    caso = repositorio.obtener(caso_id)
    if caso is None:  # el caso desapareció entre listar() y obtener()
        st.error(f"El caso {caso_id} ya no existe en el repositorio.")
        st.stop()
    return caso


def _obtener_caso() -> Caso:
    directorio_datos = os.environ.get("INVESTIGACION_DATOS")
    if directorio_datos:
        return _caso_persistido(directorio_datos)
    if "modulo" not in st.session_state:
        modulo, caso = abrir_caso_sembrado()
        st.session_state["modulo"] = modulo
        st.session_state["caso_id"] = caso.id
    modulo = cast(ModuloDeInvestigacion, st.session_state["modulo"])
    caso_id = cast(str, st.session_state["caso_id"])
    return modulo.consultar_caso(caso_id)


def _mostrar_estado(caso: Caso) -> None:
    st.subheader("Estado del caso")
    estado = dict(estado_caso(caso))
    columnas = st.columns(4)
    columnas[0].metric("Identificador", estado["Identificador"])
    columnas[1].metric("Eventos", estado["Eventos"])
    columnas[2].metric("Hallazgos", estado["Hallazgos"])
    columnas[3].metric("Modalidad de inferencia", estado["Modalidad de inferencia"])
    st.caption(
        f"Fuente: {estado['Fuente']} · SHA-256: {estado['SHA-256']} · "
        f"Procedencia: {estado['Procedencia']}"
    )
    if caso.errores:
        st.warning(
            "Errores registrados:\n" + "\n".join(f"- {error}" for error in caso.errores)
        )


def _mostrar_detalle_evento(caso: Caso) -> None:
    uid = st.session_state.get("evento_abierto")
    if not uid:
        return
    evento = next((item for item in caso.eventos if item.uid == uid), None)
    if evento is None:
        return
    st.header(f"Evento {evento.uid}")
    st.button("Cerrar evento", key="cerrar-evento", on_click=_cerrar_evento)
    datos, procedencia = st.columns(2)
    with datos:
        st.markdown("**Datos normalizados**")
        for etiqueta, valor in _campos_evento(evento):
            st.markdown(f"- **{etiqueta}:** {valor}")
    with procedencia:
        st.markdown("**Procedencia**")
        for etiqueta, valor in procedencia_evento(caso, evento):
            st.markdown(f"- **{etiqueta}:** {valor}")


def _mostrar_cronologia(caso: Caso) -> None:
    st.subheader("Cronología")
    for evento in cronologia(caso):
        columnas = st.columns([1, 2, 2, 2, 3])
        columnas[0].markdown(f"`{evento.uid}`")
        columnas[1].markdown(evento.timestamp_normalizado or "sin timestamp")
        columnas[2].markdown(evento.tipo_evento or "evento")
        columnas[3].markdown(evento.proceso or "sin proceso")
        columnas[4].button(
            "Abrir evento",
            key=f"abrir-{evento.uid}",
            on_click=_abrir_evento,
            args=(evento.uid,),
        )


def _mostrar_hallazgos(caso: Caso) -> None:
    st.subheader(f"Hallazgos ({len(caso.hallazgos)})")
    if not caso.hallazgos:
        st.info(
            "Sin hallazgos validados. La cronología y la evidencia permanecen disponibles."
        )
        return
    for indice, hallazgo in enumerate(caso.hallazgos):
        st.markdown(f"### {hallazgo.hipotesis}")
        st.markdown(f"**Razón del vínculo:** {hallazgo.razon_vinculo}")
        st.markdown(
            "**Técnicas candidatas:** "
            + (", ".join(hallazgo.tecnicas_candidatas) or "ninguna")
        )
        st.markdown(f"**Procedencia del mapeo:** {hallazgo.procedencia_mapeo.value}")
        st.markdown(f"**Estado de revisión:** {hallazgo.estado_revision.value}")
        if hallazgo.explicaciones_alternativas:
            st.markdown(
                "**Explicaciones alternativas:** "
                + "; ".join(hallazgo.explicaciones_alternativas)
            )
        if hallazgo.evidencia_faltante:
            st.markdown(
                "**Evidencia faltante:** " + "; ".join(hallazgo.evidencia_faltante)
            )
        if hallazgo.limitaciones:
            st.markdown("**Limitaciones:** " + "; ".join(hallazgo.limitaciones))
        st.markdown("**Referencias de evidencia:**")
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


def _mostrar_exportacion(caso: Caso) -> None:
    st.subheader("Exportación")
    formato = st.radio(
        "Formato de exportación",
        options=tuple(_EXPORTACION),
        key="formato-exportacion",
        horizontal=True,
    )
    formato_exportacion, extension, mime, lenguaje = _EXPORTACION[formato]
    contenido = exportar(caso, formato_exportacion)
    st.download_button(
        f"Descargar {formato}",
        data=contenido,
        file_name=f"caso-{caso.id}.{extension}",
        mime=mime,
        key="descargar-exportacion",
    )
    st.code(contenido, language=lenguaje)


def main() -> None:
    st.set_page_config(page_title="Investigación de eventos", layout="wide")
    st.title("Asistente privado de investigación")
    if os.environ.get("INVESTIGACION_DATOS"):
        st.info(
            "Caso importado y persistido desde evidencia real: la interfaz "
            "sólo lo consulta, no repite la inferencia."
        )
    else:
        st.info(
            "Caso sembrado con adaptadores controlados: recorre la navegación sin "
            "invocar Hayabusa ni un modelo real."
        )
    caso = _obtener_caso()
    _mostrar_estado(caso)
    _mostrar_detalle_evento(caso)
    _mostrar_cronologia(caso)
    _mostrar_hallazgos(caso)
    _mostrar_exportacion(caso)


main()
