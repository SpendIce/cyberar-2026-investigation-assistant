"""Caso sembrado determinista para la demostración y la interfaz local.

El caso se construye con adaptadores controlados: no invoca Hayabusa ni un
modelo real. Es la evidencia de prueba que la interfaz abre sin servicios
externos y que las pruebas de humo recorren de extremo a extremo.
"""

from __future__ import annotations

from typing import Callable, Mapping

from investigacion.adaptadores.controlados import EvidenciaControlada, InferenciaControlada
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.modelos import Caso, Evento, Origen, PropuestaHallazgo
from investigacion.modulo import ModuloDeInvestigacion

RUTA_SEMBRADA = "fixtures/caso-sembrado.evtx"
PROCEDENCIA_SEMBRADA = "adaptadores controlados (sin Hayabusa ni modelo real)"
SHA_SEMBRADO = "sha256-sembrado-determinista"

VERSIONES_SEMBRADAS: Mapping[str, str] = {
    "hayabusa": "controlado",
    "catalogo_attack": "subconjunto-local-2026",
    "fixture": "sembrado-1",
}


def eventos_sembrados() -> tuple[Evento, ...]:
    """Eventos del caso de demostración: instalación de servicio y PowerShell."""
    return (
        Evento(
            uid="ev-1",
            caso_id="",
            origen_sha256="",
            localizador_original="Security/EventRecordID=4101",
            timestamp_original="2026-01-01T10:00:00",
            timestamp_normalizado="2026-01-01T10:00:00Z",
            host="WIN-CONTROL",
            usuario="admin",
            canal="Security",
            tipo_evento="ServiceInstalled",
            proceso="PSEXESVC.exe",
            proceso_padre="services.exe",
            contenido="Servicio PSEXESVC instalado",
            regla_hayabusa="hayabusa/psexec_service_install.yml",
            referencia_original="evidence/WIN-CONTROL/Security/4101",
        ),
        Evento(
            uid="ev-2",
            caso_id="",
            origen_sha256="",
            localizador_original="Security/EventRecordID=4102",
            timestamp_original="2026-01-01T10:00:05",
            timestamp_normalizado="2026-01-01T10:00:05Z",
            host="WIN-CONTROL",
            usuario="admin",
            canal="Security",
            tipo_evento="ProcessCreated",
            proceso="powershell.exe",
            proceso_padre="services.exe",
            contenido="powershell.exe -EncodedCommand <omitido>",
            regla_hayabusa=None,
            referencia_original="evidence/WIN-CONTROL/Security/4102",
        ),
        Evento(
            uid="ev-3",
            caso_id="",
            origen_sha256="",
            localizador_original="Security/EventRecordID=4103",
            timestamp_original="2026-01-01T10:00:07",
            timestamp_normalizado="2026-01-01T10:00:07Z",
            host="WIN-CONTROL",
            usuario="admin",
            canal="Security",
            tipo_evento="NetworkConnection",
            proceso="powershell.exe",
            proceso_padre="services.exe",
            contenido="Conexión SMB saliente hacia 10.20.30.40:445",
            regla_hayabusa="hayabusa/smb_outbound_connection.yml",
            referencia_original="evidence/WIN-CONTROL/Security/4103",
        ),
        Evento(
            uid="ev-4",
            caso_id="",
            origen_sha256="",
            localizador_original="Security/EventRecordID=4099",
            timestamp_original="2026-01-01T09:59:55",
            timestamp_normalizado="2026-01-01T09:59:55Z",
            host="WIN-CONTROL",
            usuario="admin",
            canal="Security",
            tipo_evento="ExplicitCredentialLogon",
            proceso="lsass.exe",
            proceso_padre=None,
            contenido="Inicio de sesión con credenciales explícitas",
            regla_hayabusa=None,
            referencia_original="evidence/WIN-CONTROL/Security/4099",
        ),
    )


def propuesta_sembrada() -> PropuestaHallazgo:
    """Hallazgo de demostración que cita eventos existentes del caso."""
    return PropuestaHallazgo(
        hipotesis="Ejecución remota compatible con administración remota de servicios",
        referencias_eventos=("ev-1", "ev-2", "ev-3"),
        tecnicas_candidatas=("T1021.002", "T1569.002"),
        campos_citados=("proceso", "proceso_padre", "canal", "tipo_evento"),
        razon_vinculo=(
            "Instalación de un servicio seguida de ejecución de PowerShell "
            "y de una conexión SMB saliente"
        ),
        explicaciones_alternativas=("Administración legítima con PsExec",),
        evidencia_faltante=("Firma del binario remoto", "Dirección de origen del operador"),
        limitaciones=("La dirección de origen no fue registrada en el fixture",),
    )


def construir_modulo_sembrado(
    *, generador_de_ids: Callable[[], str] | None = None
) -> ModuloDeInvestigacion:
    """Construye el módulo con adaptadores controlados y el caso sembrado."""
    return ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(
            eventos=eventos_sembrados(),
            sha256=SHA_SEMBRADO,
            nombre=RUTA_SEMBRADA,
            versiones=VERSIONES_SEMBRADAS,
        ),
        motor_inferencia=InferenciaControlada(propuestas=(propuesta_sembrada(),)),
        repositorio=RepositorioEnMemoria(),
        generador_de_ids=generador_de_ids,
    )


def abrir_caso_sembrado() -> tuple[ModuloDeInvestigacion, Caso]:
    """Crea e investiga el caso sembrado, sin servicios externos."""
    modulo = construir_modulo_sembrado()
    creado = modulo.crear_caso(
        Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA)
    )
    return modulo, modulo.investigar_caso(creado.id)
