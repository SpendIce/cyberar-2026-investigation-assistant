"""Métricas del caso para la interfaz: números Sigma y técnicas con procedencia.

Todo se calcula por código desde el estado persistido del caso: las filas de
detección Hayabusa preservadas en cada evento y los hallazgos validados. La
interfaz no inventa cobertura ni atribuye mapeos al modelo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

from investigacion.adaptadores.hayabusa import detecciones_de
from investigacion.modelos import Caso

_ID_TECNICA = re.compile(r"T\d{4}(?:\.\d{3})?")


def detecciones(caso: Caso) -> tuple[dict[str, Any], ...]:
    """Todas las filas de detección Hayabusa preservadas en los eventos."""
    filas: list[dict[str, Any]] = []
    for evento in caso.eventos:
        filas.extend(detecciones_de(evento))
    return tuple(filas)


def numeros_sigma(caso: Caso) -> dict[str, int]:
    """Conteos del motor defensivo sobre este caso."""
    filas = detecciones(caso)
    reglas = {
        str(fila.get("RuleID") or fila.get("RuleFile") or fila.get("RuleTitle"))
        for fila in filas
        if fila.get("RuleID") or fila.get("RuleFile") or fila.get("RuleTitle")
    }
    eventos_con_deteccion = sum(1 for e in caso.eventos if detecciones_de(e))
    return {
        "eventos_con_deteccion": eventos_con_deteccion,
        "eventos_total": len(caso.eventos),
        "detecciones": len(filas),
        "reglas_distintas": len(reglas),
        "tecnicas_heredadas": len(tecnicas_heredadas(caso)),
    }


def _tags_mitre(fila: dict[str, Any]) -> tuple[str, ...]:
    """Identificadores ATT&CK de una fila de detección (MitreTags)."""
    crudo = fila.get("MitreTags") or fila.get("MitreTactics") or ()
    if isinstance(crudo, str):
        crudo = (crudo,)
    if not isinstance(crudo, (list, tuple)):
        return ()
    tags = set()
    for item in crudo:
        for encontrado in _ID_TECNICA.findall(str(item)):
            tags.add(encontrado)
    return tuple(sorted(tags))


def tecnicas_heredadas(caso: Caso) -> dict[str, str]:
    """Técnica -> título de regla que la produjo (procedencia heredada)."""
    resultado: dict[str, str] = {}
    for fila in detecciones(caso):
        titulo = str(fila.get("RuleTitle") or fila.get("RuleFile") or "regla")
        for tag in _tags_mitre(fila):
            resultado.setdefault(tag, titulo)
    return resultado


def tecnicas_del_modelo(caso: Caso) -> dict[str, str]:
    """Técnica -> etiqueta de procedencia modelo. La prosa del hallazgo no se
    copia acá: el texto concluyente legado no debe filtrarse por los tooltips."""
    resultado: dict[str, str] = {}
    for hallazgo in caso.hallazgos:
        for tecnica in hallazgo.tecnicas_candidatas:
            resultado.setdefault(tecnica, "hipótesis del modelo")
    return resultado


def hosts_del_caso(caso: Caso) -> tuple[str, ...]:
    return tuple(sorted({e.host for e in caso.eventos if e.host}))


_SEVERIDADES = ("critical", "high", "medium", "low", "informational")


def severidad_evento(evento: Any) -> str:
    """La severidad más alta entre las detecciones del evento."""
    niveles = {str(fila.get("Level") or "").strip() for fila in detecciones_de(evento)}
    for severidad in _SEVERIDADES:
        if severidad in niveles:
            return severidad
    return "sin detección"


def detecciones_evento(evento: Any) -> int:
    return len(detecciones_de(evento))


def severidad_caso(caso: Caso) -> str:
    """La severidad más alta marcada por las reglas en todo el caso."""
    niveles = {severidad_evento(evento) for evento in caso.eventos}
    for severidad in _SEVERIDADES:
        if severidad in niveles:
            return severidad
    return "sin detección"


_CAMPOS_REMOTOS = (
    "IpAddress",
    "SourceIp",
    "DestinationIp",
    "DestinationHostname",
    "WorkstationName",
    "SourceHostname",
    "TargetServerName",
    "ComputerName",
)

_VALORES_NO_REMOTOS = {"-", "127.0.0.1", "::1", "localhost", "0.0.0.0", "::"}


def campos_de(evento: Any) -> dict[str, Any]:
    """`AllFieldInfo` preservado dentro del `contenido` del evento."""
    try:
        contenido = json.loads(evento.contenido or "")
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(contenido, dict):
        return {}
    campos = contenido.get("campos")
    return campos if isinstance(campos, dict) else {}


def topologia_hosts(caso: Caso) -> dict[str, set[str]]:
    """Host observado -> endpoints remotos referenciados por sus eventos.

    Las aristas son referencias observadas en campos de la evidencia, no
    dirección de ataque: un `IpAddress` en un logon type 3 es el origen
    remoto, un `DestinationHostname` es un destino. Se dibujan sin flecha.
    """
    topologia: dict[str, set[str]] = {}
    for evento in caso.eventos:
        host = evento.host or "host desconocido"
        campos = campos_de(evento)
        for clave in _CAMPOS_REMOTOS:
            valor = campos.get(clave)
            if isinstance(valor, (list, tuple)):
                valores = tuple(str(item) for item in valor)
            elif isinstance(valor, str):
                valores = tuple(valor.split(","))
            else:
                continue
            for remoto in valores:
                remoto = remoto.strip()
                if (
                    remoto
                    and remoto.casefold() not in _VALORES_NO_REMOTOS
                    and remoto.casefold() != host.casefold()
                ):
                    topologia.setdefault(host, set()).add(remoto)
    return topologia


def mapa_attack() -> dict[str, Any]:
    """El asset de display táctica→técnica generado desde las reglas fijadas."""
    ruta = Path(__file__).resolve().parent.parent / "datos" / "mapa_attack.json"
    return cast(dict[str, Any], json.loads(ruta.read_text(encoding="utf-8")))


_TACTICAS_ORDEN = (
    "reconnaissance",
    "resource_development",
    "initial_access",
    "execution",
    "persistence",
    "privilege_escalation",
    "defense_evasion",
    "credential_access",
    "discovery",
    "lateral_movement",
    "collection",
    "command_and_control",
    "exfiltration",
    "impact",
)


def tacticas_orden() -> tuple[str, ...]:
    return _TACTICAS_ORDEN


def artefactos_del_caso(caso: Caso, directorio_datos: Path | None = None) -> dict[str, Path]:
    """Artefactos conservados en disco junto al EVTX original, si existen.

    `origen.ruta` es absoluta en la máquina que importó; cuando el repositorio
    viaja (clone de un compañero), se re-resuelve bajo `directorio_datos` por
    el nombre de la carpeta de importación."""
    origen = Path(caso.origen.ruta)
    carpeta = origen.parent
    if not origen.is_file() and directorio_datos is not None:
        candidata = directorio_datos / "evidencia" / carpeta.name
        if (candidata / origen.name).is_file():
            origen = candidata / origen.name
            carpeta = origen.parent
    artefactos: dict[str, Path] = {}
    if origen.is_file():
        artefactos["EVTX original"] = origen
    for nombre, etiqueta in (
        ("hayabusa.jsonl", "Salida Hayabusa (JSONL)"),
        ("manifest.json", "Manifiesto de importación"),
    ):
        candidato = carpeta / nombre
        if candidato.is_file():
            artefactos[etiqueta] = candidato
    return artefactos
