"""Aplicación mínima: recorre crear → investigar → consultar → exportar."""

from __future__ import annotations

from investigacion.modelos import FormatoExportacion, Origen
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.sembrado import (
    PROCEDENCIA_SEMBRADA,
    RUTA_SEMBRADA,
    construir_modulo_sembrado,
)


def main() -> int:
    modulo: ModuloDeInvestigacion = construir_modulo_sembrado(
        generador_de_ids=lambda: "caso-demo"
    )

    caso = modulo.crear_caso(
        Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA)
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
