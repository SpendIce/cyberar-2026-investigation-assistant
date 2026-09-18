"""Tema visual compartido de la interfaz: consola SOC densa y escaneable."""

from __future__ import annotations

import streamlit as st

# La tarjeta lleva dos marcas ocultas justo antes de cada botón:
# <span class="card-open"> antes de "Abrir caso" y <span class="card-del">
# antes del ✕. El contenedor del botón es el hermano adyacente del
# contenedor de la marca. En Streamlit 1.64 el container(border=True) se
# envuelve en stLayoutWrapper; el :not(:has(stLayoutWrapper .card-open))
# deja sólo el wrapper más interno por si un bloque ancestro también
# resultara envuelto.
_CARD = (
    '[data-testid="stLayoutWrapper"]:has(.card-open)'
    ':not(:has([data-testid="stLayoutWrapper"] .card-open))'
)
_OPEN = (
    '[data-testid="stElementContainer"]:has(.card-open)'
    ' + [data-testid="stElementContainer"]'
)
_DEL = (
    '[data-testid="stElementContainer"]:has(.card-del)'
    ' + [data-testid="stElementContainer"]'
)

_CSS = f"""
<style>
{_CARD} {{
    position: relative;
    cursor: pointer;
    transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
}}
{_CARD}:hover {{
    border-color: rgba(120, 170, 255, .55);
    box-shadow: 0 6px 18px rgba(0, 0, 0, .28);
    transform: translateY(-1px);
}}
{_CARD}:focus-within {{
    border-color: rgba(120, 170, 255, .8);
    box-shadow: 0 0 0 2px rgba(120, 170, 255, .35);
}}

/* "Abrir caso" transparente estirado a toda la tarjeta. */
{_CARD} {_OPEN} {{
    position: absolute;
    inset: 0;
    z-index: 3;
    margin: 0 !important;
}}
{_CARD} {_OPEN} button {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    min-height: 0;
    padding: 0;
    border: none;
    background: transparent;
    color: transparent;
    font-size: 0;
}}

/* ✕ discreto en la esquina superior derecha. */
{_CARD} {_DEL} {{
    position: absolute;
    top: .45rem;
    right: .45rem;
    z-index: 4;
    width: auto;
    margin: 0 !important;
}}
{_CARD} {_DEL} button {{
    width: 1.7rem;
    height: 1.7rem;
    min-height: 0;
    padding: 0;
    border-radius: 50%;
    font-size: .95rem;
    line-height: 1;
    background: var(--secondary-background-color);
    border: 1px solid rgba(140, 140, 150, .35);
    color: rgba(165, 165, 175, .9);
    transition: color .15s ease, border-color .15s ease;
}}
{_CARD} {_DEL} button:hover {{
    border-color: #ff4d4f;
    color: #ff4d4f;
}}

/* Las marcas no ocupan espacio visible. */
{_CARD} [data-testid="stElementContainer"]:has(.card-open),
{_CARD} [data-testid="stElementContainer"]:has(.card-del) {{
    display: none;
}}

.abrir-hint {{
    margin-top: .35rem;
    font-size: .8rem;
    letter-spacing: .04em;
    color: rgba(120, 170, 255, .9);
}}

[data-testid="stMetric"] {{
    background: var(--secondary-background-color);
    border: 1px solid rgba(140, 140, 150, .22);
    border-radius: 10px;
    padding: .65rem .9rem;
}}

[data-testid="stAppViewContainer"] .block-container {{
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1320px;
}}
[data-testid="stExpander"] {{
    border-radius: 10px;
}}
</style>
"""


def inyectar_estilos() -> None:
    """Aplica el tema compartido de la interfaz."""
    st.markdown(_CSS, unsafe_allow_html=True)
