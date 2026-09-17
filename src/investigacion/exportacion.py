"""Exportación determinista de un caso validado."""

from __future__ import annotations

import html
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
    if formato is FormatoExportacion.HTML:
        return _a_html(caso, custodia)
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


def _a_html(caso: Caso, custodia: SelloCustodia | None) -> str:
    """Informe autocontenido en HTML: mismo contenido validado, sin scripts."""
    e = html.escape
    modalidad = (
        caso.modalidad_inferencia.value
        if caso.modalidad_inferencia
        else "no intentada"
    )
    partes: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="es"><head><meta charset="utf-8">',
        f"<title>Caso {e(caso.id)}</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;max-width:60em;margin:2em auto;",
        "padding:0 1em;color:#1a1a1a}",
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;",
        "padding:.3em .6em;text-align:left;font-size:.9em}",
        "code,tt{background:#f4f4f4;padding:.1em .3em}",
        ".sello{font-size:.85em;color:#555}",
        "</style></head><body>",
        f"<h1>Caso {e(caso.id)}</h1>",
        "<ul>",
        f"<li>Procedencia: {e(caso.origen.procedencia)}</li>",
        f"<li>SHA-256: <code>{e(caso.origen.sha256 or 'desconocido')}</code></li>",
        f"<li>Modalidad de inferencia: {e(modalidad)}</li>",
    ]
    if caso.origen.versiones:
        versiones = ", ".join(
            f"{e(clave)} {e(valor)}"
            for clave, valor in sorted(caso.origen.versiones.items())
        )
        partes.append(f"<li>Versiones: {versiones}</li>")
    if caso.contexto.strip():
        partes.append(f"<li>Contexto declarado: {e(caso.contexto)}</li>")
    partes.append("</ul>")
    partes.append(f"<h2>Cronología ({len(caso.eventos)} eventos)</h2><ul>")
    for evento in caso.eventos:
        partes.append(
            f"<li><code>{e(evento.uid)}</code> "
            f"{e(evento.timestamp_normalizado or 'sin timestamp')} — "
            f"{e(evento.tipo_evento or 'evento')} — "
            f"{e(evento.localizador_original)}</li>"
        )
    partes.append("</ul>")
    partes.append(f"<h2>Hallazgos ({len(caso.hallazgos)})</h2>")
    for hallazgo in caso.hallazgos:
        partes.append(f"<h3>{e(hallazgo.hipotesis)}</h3><ul>")
        partes.append(
            f"<li>Referencias: {e(', '.join(hallazgo.referencias_eventos) or 'ninguna')}</li>"
            f"<li>Razón del vínculo: {e(hallazgo.razon_vinculo or 'no declarada')}</li>"
            f"<li>Técnicas candidatas: "
            f"{e(', '.join(hallazgo.tecnicas_candidatas) or 'ninguna')}</li>"
            f"<li>Procedencia del mapeo: {e(hallazgo.procedencia_mapeo.value)}</li>"
            f"<li>Estado de revisión: {e(hallazgo.estado_revision.value)}</li>"
        )
        for etiqueta, valores in (
            ("Explicaciones alternativas", hallazgo.explicaciones_alternativas),
            ("Evidencia faltante", hallazgo.evidencia_faltante),
            ("Limitaciones", hallazgo.limitaciones),
        ):
            if valores:
                partes.append(f"<li>{etiqueta}: {e('; '.join(valores))}</li>")
        partes.append("</ul>")
    if caso.errores:
        partes.append("<h2>Advertencias</h2><ul>")
        partes.extend(f"<li>{e(error)}</li>" for error in caso.errores)
        partes.append("</ul>")
    if custodia is not None:
        partes.append(
            "<h2>Integridad</h2>"
            f"<p class='sello'>Sello del caso (SHA-256): <code>{e(custodia.sello)}</code>"
            f" — Escrituras encadenadas: {custodia.escrituras}</p>"
        )
    partes.append("</body></html>")
    return "\n".join(partes) + "\n"
