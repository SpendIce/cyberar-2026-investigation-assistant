"""Tema visual compartido de la interfaz: consola SOC densa y escaneable.

Las tarjetas de la galería son un componente CCv2 con su propio CSS en
shadow DOM (ver `galeria.py`); acá queda sólo lo que aplica a elementos
nativos de Streamlit.
"""

from __future__ import annotations

import streamlit as st

_CSS = """
<style>
[data-testid="stMetric"] {
    background: var(--secondary-background-color);
    border: 1px solid rgba(140, 140, 150, .22);
    border-radius: 10px;
    padding: .65rem .9rem;
}

[data-testid="stAppViewContainer"] .block-container {
    /* El header fijo de Streamlit (toolbar con Deploy) tapa el contenido
       si el padding superior es menor a su altura (~3.5rem). */
    padding-top: 4.5rem;
    padding-bottom: 3rem;
    max-width: 1320px;
}
[data-testid="stExpander"] {
    border-radius: 10px;
}
</style>
"""


def inyectar_estilos() -> None:
    """Aplica el tema compartido de la interfaz."""
    st.markdown(_CSS, unsafe_allow_html=True)
