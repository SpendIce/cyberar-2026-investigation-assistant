"""Aplicación mínima: recorre crear → investigar → consultar → exportar."""

from __future__ import annotations

from investigacion.adaptadores.controlados import EvidenciaControlada, InferenciaControlada
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.modelos import (
    Evento,
    FormatoExportacion,
    Origen,
    PropuestaHallazgo,
)
from investigacion.modulo import ModuloDeInvestigacion


def _eventos_de_demostracion() -> tuple[Evento, ...]:
    return (
        Evento(
            uid="ev-1",
            caso_id="",
            origen_sha256="",
            localizador_original="Security/RecordID=4101",
            timestamp_original="2026-01-01T10:00:00",
            timestamp_normalizado="2026-01-01T10:00:00Z",
            host="WIN-CONTROL",
            usuario="admin",
            canal="Security",
            tipo_evento="ServiceInstalled",
            proceso="PSEXESVC.exe",
            contenido="Servicio PSEXESVC instalado",
        ),
        Evento(
            uid="ev-2",
            caso_id="",
            origen_sha256="",
            localizador_original="Security/RecordID=4102",
            timestamp_original="2026-01-01T10:00:05",
            timestamp_normalizado="2026-01-01T10:00:05Z",
            host="WIN-CONTROL",
            usuario="admin",
            canal="Security",
            tipo_evento="ProcessCreated",
            proceso="powershell.exe",
            proceso_padre="services.exe",
            contenido="powershell.exe -EncodedCommand ...",
        ),
    )


def _propuesta_de_demostracion() -> PropuestaHallazgo:
    return PropuestaHallazgo(
        hipotesis="Ejecución remota compatible con administración remota de servicios",
        referencias_eventos=("ev-1", "ev-2"),
        tecnicas_candidatas=("T1021.002", "T1569.002"),
        campos_citados=("proceso", "proceso_padre"),
        razon_vinculo="Instalación de servicio seguida de ejecución de PowerShell",
        explicaciones_alternativas=("Administración legítima con PsExec",),
        evidencia_faltante=("Firma del binario remoto", "IP de origen"),
        limitaciones=("El fixture no incluye eventos de red",),
    )


def main() -> int:
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(eventos=_eventos_de_demostracion()),
        motor_inferencia=InferenciaControlada(propuestas=(_propuesta_de_demostracion(),)),
        repositorio=RepositorioEnMemoria(),
        generador_de_ids=lambda: "caso-demo",
    )

    caso = modulo.crear_caso(
        Origen(ruta="fixtures/demostracion.evtx", procedencia="adaptadores controlados")
    )
    investigado = modulo.investigar_caso(caso.id)
    consultado = modulo.consultar_caso(caso.id)

    print(f"Caso {consultado.id}: {len(consultado.eventos)} eventos")
    modalidad = (
        consultado.modalidad_inferencia.value
        if consultado.modalidad_inferencia
        else "no intentada"
    )
    print(f"Modalidad de inferencia: {modalidad}")
    print(f"Hallazgos: {len(consultado.hallazgos)}")
    print()
    print(modulo.exportar_caso(consultado.id, FormatoExportacion.MARKDOWN))
    print("Exportación JSON disponible con exportar_caso(caso_id, FormatoExportacion.JSON).")
    print(f"Caso investigado: {investigado.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
