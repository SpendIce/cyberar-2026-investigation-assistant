"""Vista de presentación: transforma el estado del caso en datos para la interfaz.

No contiene reglas de investigación: sólo ordena y etiqueta lo que el módulo de
investigación ya validó, para que el adaptador Streamlit se limite a dibujar.
"""

from __future__ import annotations

from investigacion.modelos import Caso, Evento, Hallazgo


def cronologia(caso: Caso) -> tuple[Evento, ...]:
    """Eventos ordenados por timestamp normalizado; los ausentes van al final."""
    return tuple(
        sorted(
            caso.eventos,
            key=lambda evento: (
                evento.timestamp_normalizado is None,
                evento.timestamp_normalizado or "",
            ),
        )
    )


def eventos_referenciados(caso: Caso, hallazgo: Hallazgo) -> tuple[Evento, ...]:
    """Resuelve las referencias del hallazgo contra los eventos del caso."""
    por_uid = {evento.uid: evento for evento in caso.eventos}
    return tuple(
        por_uid[referencia]
        for referencia in hallazgo.referencias_eventos
        if referencia in por_uid
    )


def referencias_no_resueltas(caso: Caso, hallazgo: Hallazgo) -> tuple[str, ...]:
    """Referencias del hallazgo que no apuntan a ningún evento del caso.

    La interfaz las muestra como error en lugar de ocultarlas: una referencia
    rota no debe degradarse silenciosamente en evidencia ausente.
    """
    existentes = {evento.uid for evento in caso.eventos}
    return tuple(
        referencia
        for referencia in hallazgo.referencias_eventos
        if referencia not in existentes
    )


def procedencia_evento(caso: Caso, evento: Evento) -> tuple[tuple[str, str], ...]:
    """Etiquetas de procedencia para abrir un evento sin abandonar el caso."""
    versiones = (
        ", ".join(f"{clave} {valor}" for clave, valor in sorted(caso.origen.versiones.items()))
        or "no declaradas"
    )
    return (
        ("Fuente", caso.origen.nombre or caso.origen.ruta),
        ("Ruta", caso.origen.ruta),
        ("SHA-256", caso.origen.sha256 or "desconocido"),
        ("Procedencia", caso.origen.procedencia),
        ("Localizador original", evento.localizador_original),
        ("Referencia original", evento.referencia_original or "no declarada"),
        ("Regla Hayabusa", evento.regla_hayabusa or "sin regla"),
        ("Versiones", versiones),
    )


def estado_caso(caso: Caso) -> tuple[tuple[str, str], ...]:
    """Resumen del estado del caso para el encabezado de la interfaz."""
    modalidad = (
        caso.modalidad_inferencia.value if caso.modalidad_inferencia else "no intentada"
    )
    return (
        ("Identificador", caso.id),
        ("Procedencia", caso.origen.procedencia),
        ("Fuente", caso.origen.nombre or caso.origen.ruta),
        ("SHA-256", caso.origen.sha256 or "desconocido"),
        ("Eventos", str(len(caso.eventos))),
        ("Hallazgos", str(len(caso.hallazgos))),
        ("Modalidad de inferencia", modalidad),
    )
