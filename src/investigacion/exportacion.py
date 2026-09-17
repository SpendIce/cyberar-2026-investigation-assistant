"""Exportación determinista de un caso validado."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from investigacion.custodia import SelloCustodia
from investigacion.modelos import Caso, FormatoExportacion


def exportar(
    caso: Caso,
    formato: FormatoExportacion,
    custodia: SelloCustodia | None = None,
) -> str:
    if formato is FormatoExportacion.JSON:
        return _a_json(caso, custodia)
    return _a_markdown(caso, custodia)


def _a_json(caso: Caso, custodia: SelloCustodia | None) -> str:
    datos: dict[str, Any] = asdict(caso)
    if custodia is not None:
        datos["custodia"] = {"sello": custodia.sello, "escrituras": custodia.escrituras}
    return json.dumps(datos, indent=2, ensure_ascii=False, sort_keys=True)


def _a_markdown(caso: Caso, custodia: SelloCustodia | None) -> str:
    lineas: list[str] = [
        f"# Caso {caso.id}",
        "",
        f"- Procedencia: {caso.origen.procedencia}",
        f"- SHA-256: {caso.origen.sha256 or 'desconocido'}",
        f"- Modalidad de inferencia: "
        f"{caso.modalidad_inferencia.value if caso.modalidad_inferencia else 'no intentada'}",
    ]
    if caso.origen.versiones:
        versiones = ", ".join(
            f"{clave} {valor}" for clave, valor in sorted(caso.origen.versiones.items())
        )
        lineas.append(f"- Versiones: {versiones}")
    lineas.extend(["", f"## Cronología ({len(caso.eventos)} eventos)", ""])
    for evento in caso.eventos:
        lineas.append(
            f"- `{evento.uid}` {evento.timestamp_normalizado or 'sin timestamp'}"
            f" — {evento.tipo_evento or 'evento'} — {evento.localizador_original}"
        )
    lineas.extend(["", f"## Hallazgos ({len(caso.hallazgos)})", ""])
    for hallazgo in caso.hallazgos:
        lineas.extend(
            [
                f"### {hallazgo.hipotesis}",
                "",
                f"- Referencias: {', '.join(hallazgo.referencias_eventos) or 'ninguna'}",
                f"- Razón del vínculo: {hallazgo.razon_vinculo or 'no declarada'}",
                f"- Técnicas candidatas: "
                f"{', '.join(hallazgo.tecnicas_candidatas) or 'ninguna'}",
                f"- Procedencia del mapeo: {hallazgo.procedencia_mapeo.value}",
                f"- Estado de revisión: {hallazgo.estado_revision.value}",
            ]
        )
        if hallazgo.explicaciones_alternativas:
            alternativas = "; ".join(hallazgo.explicaciones_alternativas)
            lineas.append(f"- Explicaciones alternativas: {alternativas}")
        if hallazgo.evidencia_faltante:
            faltante = "; ".join(hallazgo.evidencia_faltante)
            lineas.append(f"- Evidencia faltante: {faltante}")
        if hallazgo.limitaciones:
            limitaciones = "; ".join(hallazgo.limitaciones)
            lineas.append(f"- Limitaciones: {limitaciones}")
        lineas.append("")
    if caso.errores:
        lineas.extend(["## Advertencias", ""])
        lineas.extend(f"- {error}" for error in caso.errores)
    if custodia is not None:
        lineas.extend(
            [
                "",
                "## Integridad",
                "",
                f"- Sello del caso (SHA-256): `{custodia.sello}`",
                f"- Escrituras encadenadas: {custodia.escrituras}",
            ]
        )
    return "\n".join(lineas).rstrip() + "\n"
