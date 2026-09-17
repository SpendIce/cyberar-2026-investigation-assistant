"""Clasificación de endpoints de inferencia según la soberanía de la evidencia.

La herramienta es local-first: por defecto la evidencia seleccionada sólo
puede viajar hacia endpoints que el equipo administra —loopback, redes
privadas, link-local y overlays tipo Tailscale (CGNAT 100.64.0.0/10)— más
los hosts que el equipo declare explícitamente como propios. La decisión de
usar un endpoint externo existe, pero es opt-in y deja una advertencia
persistida en el caso (ver `adaptadores/ollama.py`).
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

# Nombres que resuelven a la propia máquina en los despliegues habituales.
_HOSTS_LOCALES = frozenset({"localhost", "host.docker.internal"})

# Overlay CGNAT usado por Tailscale/Headscale: no es RFC1918, pero el nodo
# sigue siendo administrado por el equipo.
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def es_endpoint_controlado(
    url: str, hosts_declarados: frozenset[str] = frozenset()
) -> bool:
    """Indica si el endpoint pertenece a infraestructura administrada por el equipo."""
    host = urlparse(url).hostname
    if host is None:
        return False
    normalizado = host.rstrip(".").lower()
    if normalizado in hosts_declarados or normalizado in _HOSTS_LOCALES:
        return True
    if normalizado.endswith(".localhost"):
        return True
    try:
        direccion = ipaddress.ip_address(normalizado)
    except ValueError:
        return False
    return direccion.is_private or direccion in _CGNAT
