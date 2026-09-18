"""Tema visual compartido de la interfaz: consola SOC densa y escaneable."""

from __future__ import annotations

import streamlit as st

# La tarjeta lleva dos marcas: <span class="card-open"> al inicio y
# <span class="card-del"> antes del botón de borrado. Con :has() ubicamos:
#   - la tarjeta: cualquier bloque que contiene .card-open
#   - el botón "Abrir caso": contenedor con botón y un hermano posterior .card-del
#   - el botón ✕: contenedor con botón sin hermano posterior .card-del
# Solo el wrapper externo lleva borde: las sombras y el hover van ahí para
# no duplicar el efecto en el bloque interno.
_MARCO = '[data-testid="stVerticalBlockBorderWrapper"]:has(.card-open)'
# Para posicionar los botones sirve cualquier ancestro marcado.
_CARD = (
    ':is([data-testid="stVerticalBlockBorderWrapper"],'
    '[data-testid="stVerticalBlock"]):has(.card-open)'
)
_ABIERTO = (
    '[data-testid="stElementContainer"]:has(button)'
    ':has(~ [data-testid="stElementContainer"] .card-del)'
)
_CERRAR = (
    '[data-testid="stElementContainer"]:has(button)'
    ':not(:has(~ [data-testid="stElementContainer"] .card-del))'
)

_CSS = f"""
<style>
{_MARCO} {{
    position: relative;
    cursor: pointer;
    transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
}}
{_MARCO}:hover {{
    border-color: rgba(120, 170, 255, .55);
    box-shadow: 0 6px 18px rgba(0, 0, 0, .28);
    transform: translateY(-1px);
}}
{_MARCO}:focus-within {{
    border-color: rgba(120, 170, 255, .8);
    box-shadow: 0 0 0 2px rgba(120, 170, 255, .35);
}}

/* Botón "Abrir caso": transparente, estirado a toda la tarjeta. */
{_CARD} {_ABIERTO} {{
    position: absolute;
    inset: 0;
    z-index: 3;
    margin: 0 !important;
}}
{_CARD} {_ABIERTO} button {{
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

/* Botón ✕: discreto, esquina superior derecha. */
{_CARD} {_CERRAR} {{
    position: absolute;
    top: .45rem;
    right: .45rem;
    z-index: 4;
    width: auto;
    margin: 0 !important;
}}
{_CARD} {_CERRAR} button {{
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
{_CARD} {_CERRAR} button:hover {{
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
