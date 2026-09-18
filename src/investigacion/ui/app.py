"""Interfaz Streamlit: galería de casos y detalle navegable por pestañas.

Es un adaptador de presentación. No contiene reglas de investigación: crea y
consulta casos a través del módulo y dibuja lo que éste ya validó. Con la
variable `INVESTIGACION_DATOS` apuntando al directorio de datos de una
importación real, trabaja sobre los casos persistidos en `casos.sqlite` y
habilita el alta por arrastre de EVTX; sin ella expone el caso sembrado.
"""

from __future__ import annotations

import streamlit as st

from investigacion.ui import detalle, galeria
from investigacion.ui.estilos import inyectar_estilos
from investigacion.ui.servicio import obtener_servicio


def main() -> None:
    st.set_page_config(page_title="Investigación de eventos", layout="wide")
    inyectar_estilos()
    servicio = obtener_servicio()
    caso_abierto = st.session_state.get("caso_abierto")
    if caso_abierto:
        detalle.mostrar(servicio, caso_abierto)
    else:
        galeria.mostrar(servicio)


main()
