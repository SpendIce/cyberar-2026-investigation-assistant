"""Tipos del dominio de investigación."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class ModalidadInferencia(StrEnum):
    NODO_PRIVADO = "nodo_privado"
    MODELO_LOCAL = "modelo_local"
    MODELO_EXTERNO = "modelo_externo"
    DEGRADADO = "degradado"


class FormatoExportacion(StrEnum):
    MARKDOWN = "markdown"
    JSON = "json"


class ProcedenciaMapeo(StrEnum):
    HEREDADO_DE_REGLA = "heredado_de_regla"
    MODELO = "modelo"
    REVISION_HUMANA = "revision_humana"


class EstadoRevision(StrEnum):
    PENDIENTE = "pendiente"


@dataclass(frozen=True)
class Origen:
    ruta: str
    procedencia: str
    sha256: str | None = None
    nombre: str | None = None
    versiones: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Evento:
    uid: str
    caso_id: str
    origen_sha256: str
    localizador_original: str
    timestamp_original: str | None = None
    timestamp_normalizado: str | None = None
    host: str | None = None
    usuario: str | None = None
    canal: str | None = None
    tipo_evento: str | None = None
    proceso: str | None = None
    proceso_padre: str | None = None
    contenido: str | None = None
    regla_hayabusa: str | None = None
    referencia_original: str | None = None


@dataclass(frozen=True)
class ResultadoDeEvidencia:
    origen: Origen
    eventos: tuple[Evento, ...]


@dataclass(frozen=True)
class PropuestaHallazgo:
    hipotesis: str
    referencias_eventos: tuple[str, ...]
    tecnicas_candidatas: tuple[str, ...] = ()
    campos_citados: tuple[str, ...] = ()
    razon_vinculo: str = ""
    explicaciones_alternativas: tuple[str, ...] = ()
    evidencia_faltante: tuple[str, ...] = ()
    limitaciones: tuple[str, ...] = ()


@dataclass(frozen=True)
class Hallazgo:
    caso_id: str
    hipotesis: str
    referencias_eventos: tuple[str, ...]
    campos_citados: tuple[str, ...]
    tecnicas_candidatas: tuple[str, ...]
    razon_vinculo: str
    procedencia_mapeo: ProcedenciaMapeo
    explicaciones_alternativas: tuple[str, ...]
    evidencia_faltante: tuple[str, ...]
    limitaciones: tuple[str, ...]
    estado_revision: EstadoRevision


@dataclass(frozen=True)
class Caso:
    id: str
    origen: Origen
    eventos: tuple[Evento, ...]
    hallazgos: tuple[Hallazgo, ...] = ()
    errores: tuple[str, ...] = ()
    modalidad_inferencia: ModalidadInferencia | None = None
