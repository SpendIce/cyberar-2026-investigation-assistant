"""Activos reproducibles para comparar ambigüedad sin contaminar la inferencia.

Este módulo contiene solamente evidencia del control sintético y metadatos de
presentación. La verdad de referencia vive fuera de ``src`` y de SQLite, en
``docs/evaluacion/verdad-referencia-escenarios.json``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from investigacion.adaptadores.controlados import EvidenciaControlada
from investigacion.modelos import Evento, Origen

ESCENARIO_SOSPECHOSO = "actividad-psexec-publica"
ESCENARIO_LEGITIMO = "administracion-autorizada-sintetica"
ARCHIVO_COMPARACION = "escenarios-comparacion.json"


@dataclass(frozen=True)
class EscenarioComparacion:
    escenario_id: str
    caso_id: str
    titulo: str
    descripcion: str
    tipo_evidencia: str


def eventos_control_legitimo() -> tuple[Evento, ...]:
    """Telemetría sintética comparable con el caso sospechoso.

    Los campos describen sólo lo observable: la autorización de la operación
    se documenta en la verdad de referencia, no dentro de la evidencia que
    recibe el modelo (ADR-0004).
    """
    return (
        Evento(
            uid="ctl-1", caso_id="", origen_sha256="",
            localizador_original="Application/EventRecordID=9001",
            timestamp_normalizado="2026-02-01T09:00:00Z", host="WIN-ADMIN01",
            usuario="svc-patching", canal="Application",
            tipo_evento="ChangeTicketReferenced",
            contenido="Referencia a ticket CHG-4821 para actualización de agente en WIN-ADMIN01",
            referencia_original="evidence/WIN-ADMIN01/Application/9001",
        ),
        Evento(
            uid="ctl-2", caso_id="", origen_sha256="",
            localizador_original="Security/EventRecordID=9002",
            timestamp_normalizado="2026-02-01T09:00:10Z", host="WIN-ADMIN01",
            usuario="svc-patching", canal="Security", tipo_evento="ServiceInstalled",
            proceso="PSEXESVC.exe", proceso_padre="services.exe",
            contenido="Servicio PSEXESVC instalado por svc-patching",
            referencia_original="evidence/WIN-ADMIN01/Security/9002",
        ),
        Evento(
            uid="ctl-3", caso_id="", origen_sha256="",
            localizador_original="Security/EventRecordID=9003",
            timestamp_normalizado="2026-02-01T09:00:15Z", host="WIN-ADMIN01",
            usuario="svc-patching", canal="Security", tipo_evento="ProcessCreated",
            proceso="powershell.exe", proceso_padre="services.exe",
            contenido=r"powershell.exe -File \\fileserver-interno\parches\aplicar-chg-4821.ps1",
            referencia_original="evidence/WIN-ADMIN01/Security/9003",
        ),
        Evento(
            uid="ctl-4", caso_id="", origen_sha256="",
            localizador_original="Security/EventRecordID=9004",
            timestamp_normalizado="2026-02-01T09:00:20Z", host="WIN-ADMIN01",
            usuario="svc-patching", canal="Security", tipo_evento="NetworkConnection",
            proceso="powershell.exe", proceso_padre="services.exe",
            contenido="Conexión SMB saliente hacia fileserver-interno.corp.local:445",
            referencia_original="evidence/WIN-ADMIN01/Security/9004",
        ),
    )


def origen_control_legitimo() -> Origen:
    """Origen del control sintético, identificado sin simular captura real.

    El sha256 se calcula sobre la serialización canónica de la fixture, así
    que se re-verifica contra ``eventos_control_legitimo()`` y no contra los
    eventos persistidos (a los que el módulo asigna ``caso_id`` y
    ``origen_sha256`` al importarlos).
    """
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


def evidencia_control_legitimo() -> EvidenciaControlada:
    """El control legítimo ya montado como fuente de evidencia del módulo."""
    origen = origen_control_legitimo()
    return EvidenciaControlada(
        eventos_control_legitimo(),
        sha256=origen.sha256 or "",
        nombre=origen.nombre or "control-legitimo-sintetico",
        versiones=origen.versiones,
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
    escenarios = datos.get("escenarios") if isinstance(datos, dict) else None
    if not isinstance(escenarios, list):
        raise ValueError(f"{ruta} no contiene una lista 'escenarios' válida")
    resultado: dict[str, EscenarioComparacion] = {}
    for item in escenarios:
        escenario = EscenarioComparacion(**item)
        resultado[escenario.caso_id] = escenario
    return resultado
