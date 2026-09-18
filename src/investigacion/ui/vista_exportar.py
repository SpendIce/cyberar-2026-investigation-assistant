"""Pestaña Exportar: modal para elegir artefactos y formato del informe."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import streamlit as st

from investigacion.modelos import Caso, FormatoExportacion
from investigacion.ui.metricas import artefactos_del_caso
from investigacion.ui.servicio import ServicioDeCasos

_FORMATOS = {
    "Markdown": (FormatoExportacion.MARKDOWN, "md", "text/markdown"),
    "HTML": (FormatoExportacion.HTML, "html", "text/html"),
    "JSON": (FormatoExportacion.JSON, "json", "application/json"),
}


@st.dialog("Exportar caso", width="large")
def _dialogo_exportar(servicio: ServicioDeCasos, caso: Caso) -> None:
    st.caption(
        "Elegí qué artefactos descargar. El informe sale del estado validado "
        "del caso; los archivos raw son los conservados por la importación, "
        "byte a byte."
    )
    st.markdown("**Informe del caso**")
    formato = st.radio(
        "Formato del informe",
        options=tuple(_FORMATOS),
        horizontal=True,
        key="formato-informe",
    )
    formato_exportacion, extension, mime = _FORMATOS[formato]
    contenido = servicio.modulo.exportar_caso(caso.id, formato_exportacion)
    st.download_button(
        f"Descargar informe .{extension}",
        data=contenido,
        file_name=f"caso-{caso.id}.{extension}",
        mime=mime,
        key="descargar-informe",
    )

    st.markdown("**Eventos normalizados (JSON)**")
    eventos_json = json.dumps(
        [asdict(evento) for evento in caso.eventos],
        ensure_ascii=False,
        indent=2,
    )
    st.download_button(
        "Descargar eventos.json",
        data=eventos_json,
        file_name=f"caso-{caso.id}-eventos.json",
        mime="application/json",
        key="descargar-eventos",
    )

    st.markdown("**Artefactos conservados de la importación**")
    artefactos = artefactos_del_caso(caso, servicio.directorio_datos)
    if not artefactos:
        st.caption(
            "Este caso no tiene artefactos en disco (evidencia controlada o "
            "importación anterior al almacén)."
        )
    for etiqueta, ruta in artefactos.items():
        contenido_raw = Path(ruta).read_bytes()
        st.download_button(
            f"{etiqueta} ({Path(ruta).name})",
            data=contenido_raw,
            file_name=Path(ruta).name,
            key=f"artefacto-{etiqueta}",
        )


def mostrar(servicio: ServicioDeCasos, caso: Caso) -> None:
    st.subheader("Exportación")
    st.caption(
        "El informe incluye el sello de la cadena de custodia: verificable con "
        "`python -m investigacion.informe --verificar <archivo>`."
    )
    if st.button("Exportar…", type="primary", key="abrir-exportar"):
        _dialogo_exportar(servicio, caso)
