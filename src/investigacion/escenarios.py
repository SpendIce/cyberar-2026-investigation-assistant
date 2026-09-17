"""Activos reproducibles para comparar ambigüedad sin contaminar la inferencia.

Este módulo contiene solamente evidencia del control sintético y metadatos de
presentación. La verdad de referencia vive fuera de ``src`` y de SQLite, en
``docs/evaluacion/ground-truth-escenarios.json``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from investigacion.modelos import Evento, Origen

ESCENARIO_SOSPECHOSO = "actividad-psexec-publica"
ESCENARIO_LEGITIMO = "administracion-autorizada-sintetica"
ARCHIVO_COMPARACION = "escenarios-comparacion.json"


@dataclass(frozen=True)
class EscenarioComparacion:
    scenario_id: str
    caso_id: str
    titulo: str
    descripcion: str
    tipo_evidencia: str


def eventos_control_legitimo() -> tuple[Evento, ...]:
    """Operación administrativa documentada; evidencia sintética, no un EVTX real."""
    return (
        Evento(
            uid="ctl-1", caso_id="", origen_sha256="",
            localizador_original="Application/EventRecordID=9001",
            timestamp_normalizado="2026-02-01T09:00:00Z", host="WIN-ADMIN01",
            usuario="svc-patching", canal="Application",
            tipo_evento="ChangeTicketApproved",
            contenido="Ticket CHG-4821 aprobado: actualizar agente de parcheo en WIN-ADMIN01",
            referencia_original="evidence/WIN-ADMIN01/Application/9001",
        ),
        Evento(
            uid="ctl-2", caso_id="", origen_sha256="",
            localizador_original="Security/EventRecordID=9002",
            timestamp_normalizado="2026-02-01T09:00:10Z", host="WIN-ADMIN01",
            usuario="svc-patching", canal="Security", tipo_evento="ServiceInstalled",
            proceso="PSEXESVC.exe", proceso_padre="services.exe",
            contenido="Servicio PSEXESVC instalado por svc-patching para CHG-4821",
            referencia_original="evidence/WIN-ADMIN01/Security/9002",
        ),
        Evento(
            uid="ctl-3", caso_id="", origen_sha256="",
            localizador_original="Security/EventRecordID=9003",
            timestamp_normalizado="2026-02-01T09:00:15Z", host="WIN-ADMIN01",
            usuario="svc-patching", canal="Security", tipo_evento="ProcessCreated",
            proceso="powershell.exe", proceso_padre="services.exe",
            contenido=(
                r"powershell.exe -File \\fileserver-interno\parches\aplicar-chg-4821.ps1 "
                "(script firmado, catalogado en CMDB)"
            ),
            referencia_original="evidence/WIN-ADMIN01/Security/9003",
        ),
        Evento(
            uid="ctl-4", caso_id="", origen_sha256="",
            localizador_original="Security/EventRecordID=9004",
            timestamp_normalizado="2026-02-01T09:00:20Z", host="WIN-ADMIN01",
            usuario="svc-patching", canal="Security", tipo_evento="NetworkConnection",
            proceso="powershell.exe", proceso_padre="services.exe",
            contenido=(
                "Conexión SMB saliente hacia fileserver-interno.corp.local:445 "
                "(recurso de parches conocido en CMDB)"
            ),
            referencia_original="evidence/WIN-ADMIN01/Security/9004",
        ),
    )


def origen_control_legitimo() -> Origen:
    """Origen verificable del control sintético, identificado sin simular captura real."""
    serializado = json.dumps(
        [asdict(evento) for evento in eventos_control_legitimo()],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return Origen(
        ruta="control-sintetico/documentado-chg-4821.json",
        procedencia=(
            "control sintético/documentado del equipo; operación administrativa "
            "autorizada CHG-4821; captura EVTX real pendiente"
        ),
        sha256=hashlib.sha256(serializado).hexdigest(),
        nombre="control-legitimo-sintetico-chg-4821",
        versiones={"fixture": "control-legitimo-1", "captura": "sintetica"},
    )


def guardar_comparacion(ruta: Path, escenarios: tuple[EscenarioComparacion, ...]) -> None:
    ruta.write_text(
        json.dumps(
            {"version": 1, "escenarios": [asdict(escenario) for escenario in escenarios]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def cargar_comparacion(ruta: Path) -> dict[str, EscenarioComparacion]:
    if not ruta.is_file():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    escenarios = datos.get("escenarios", []) if isinstance(datos, dict) else []
    if not isinstance(escenarios, list):
        return {}
    resultado: dict[str, EscenarioComparacion] = {}
    for item in escenarios:
        if not isinstance(item, dict):
            continue
        try:
            escenario = EscenarioComparacion(**item)
        except TypeError:
            continue
        resultado[escenario.caso_id] = escenario
    return resultado
