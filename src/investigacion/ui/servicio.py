"""Costura de la interfaz con el módulo de investigación.

Resuelve los adaptadores según el ambiente: con `INVESTIGACION_DATOS` trabaja
sobre el repositorio persistido y habilita el alta de casos (Hayabusa real +
inferencia Ollama local/privada según `OLLAMA_*`); sin esa variable expone el
caso sembrado con adaptadores controlados. El endpoint externo Zen queda
reservado al pre-procesado offline de fixtures públicos y nunca se habilita
desde la interfaz.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from investigacion.adaptadores.controlados import (
    EvidenciaControlada,
    InferenciaControlada,
    InferenciaNoDisponibleControlada,
)
from investigacion.adaptadores.hayabusa import EvidenciaHayabusa
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.adaptadores.respaldo import InferenciaConRespaldo
from investigacion.escenarios import (
    ARCHIVO_COMPARACION,
    EscenarioComparacion,
    cargar_comparacion,
)
from investigacion.modelos import Caso, ModalidadInferencia, Origen
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.puertos import MotorDeInferencia, RepositorioDeCasos
from investigacion.sembrado import (
    PROCEDENCIA_SEMBRADA,
    RUTA_SEMBRADA,
    SHA_SEMBRADO,
    VERSIONES_SEMBRADAS,
    eventos_sembrados,
    propuesta_sembrada,
)
from investigacion.soberania import es_endpoint_local

_ENV_DATOS = "INVESTIGACION_DATOS"
_ENV_HAYABUSA = "HAYABUSA"
_ENV_OLLAMA_MODELO = "OLLAMA_MODELO"
_ENV_OLLAMA_BASE_URL = "OLLAMA_BASE_URL"
_ENV_OLLAMA_MODELO_NODO = "OLLAMA_MODELO_NODO"
_ENV_OLLAMA_BASE_URL_NODO = "OLLAMA_BASE_URL_NODO"
_ENV_HOST_CONTROLADO = "INVESTIGACION_HOST_CONTROLADO"
_HAYABUSA_DEFECTO = Path.home() / "tools" / "hayabusa-4.1.0" / "hayabusa-4.1.0-lin-x64-musl"
_OLLAMA_DEFECTO = "http://localhost:11434"
_MODELO_DEFECTO = "qwen2.5:7b-instruct"


@dataclass
class ServicioDeCasos:
    """El módulo, el repositorio y los metadatos de presentación del caso."""

    modulo: ModuloDeInvestigacion
    repositorio: RepositorioDeCasos
    escenarios: dict[str, EscenarioComparacion]
    directorio_datos: Path | None
    puede_importar: bool

    def casos(self) -> tuple[Caso, ...]:
        return tuple(
            caso
            for identificador in self.repositorio.listar()
            if (caso := self.repositorio.obtener(identificador)) is not None
        )

    def escenario_de(self, caso: Caso) -> EscenarioComparacion | None:
        return self.escenarios.get(caso.id)

    def titulo_de(self, caso: Caso) -> str:
        escenario = self.escenario_de(caso)
        if escenario is not None:
            return escenario.titulo
        return caso.origen.nombre or caso.origen.ruta

    def importar_upload(
        self, nombre: str, contenido: bytes, procedencia: str, contexto: str
    ) -> Caso:
        """Alta de un caso desde la interfaz: escribe el upload a disco y corre
        el pipeline completo (Hayabusa e inferencia declarada)."""
        if not self.puede_importar or self.directorio_datos is None:
            raise RuntimeError("la importación no está habilitada en esta sesión")
        uploads = self.directorio_datos / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        destino = Path(tempfile.mkdtemp(prefix="upload-", dir=uploads)) / nombre
        destino.write_bytes(contenido)
        caso = self.modulo.crear_caso(
            Origen(ruta=str(destino), procedencia=procedencia, nombre=nombre),
            contexto=contexto,
        )
        return self.modulo.investigar_caso(caso.id)


def _hosts_controlados() -> frozenset[str]:
    declarados = os.environ.get(_ENV_HOST_CONTROLADO, "")
    return frozenset(h.strip() for h in declarados.split(",") if h.strip())


def _ollama(
    modelo: str,
    url: str,
    modalidad: ModalidadInferencia,
    declarados: frozenset[str],
) -> InferenciaOllama:
    return InferenciaOllama(
        modelo,
        base_url=url,
        modalidad=modalidad,
        hosts_controlados=declarados,
    )


def motor_inferencia() -> MotorDeInferencia:
    """El motor interactivo de la interfaz (ADR-0011): nodo Ollama privado si
    se declara, modelo local a continuación y modo degradado al final.

    Zen queda reservado al pre-procesado offline de fixtures públicos
    (`scripts/preprocesar_zen.py`): la interfaz nunca envía evidencia a un
    endpoint externo aunque `OPENCODE_API_KEY` exista en el ambiente.
    `OLLAMA_MODELO=""` desactiva la inferencia explícitamente.
    """
    declarados = _hosts_controlados()
    motores: list[MotorDeInferencia] = []
    modelo_nodo = os.environ.get(_ENV_OLLAMA_MODELO_NODO, "").strip()
    url_nodo = os.environ.get(_ENV_OLLAMA_BASE_URL_NODO, "").strip()
    if modelo_nodo and url_nodo:
        motores.append(
            _ollama(modelo_nodo, url_nodo, ModalidadInferencia.NODO_PRIVADO, declarados)
        )
    modelo_local = os.environ.get(_ENV_OLLAMA_MODELO, _MODELO_DEFECTO).strip()
    if modelo_local:
        url_local = os.environ.get(_ENV_OLLAMA_BASE_URL, _OLLAMA_DEFECTO)
        modalidad = (
            ModalidadInferencia.MODELO_LOCAL
            if es_endpoint_local(url_local)
            else ModalidadInferencia.NODO_PRIVADO
        )
        motores.append(_ollama(modelo_local, url_local, modalidad, declarados))
    motores.append(InferenciaNoDisponibleControlada("sin motor configurado"))
    if len(motores) == 1:
        return motores[0]
    return InferenciaConRespaldo(*motores)


def servicio_persistido(directorio_datos: Path) -> ServicioDeCasos:
    repositorio = RepositorioSQLite(directorio_datos / "casos.sqlite")
    hayabusa = Path(os.environ.get(_ENV_HAYABUSA, str(_HAYABUSA_DEFECTO)))
    puede_importar = hayabusa.is_file()
    modulo = ModuloDeInvestigacion(
        EvidenciaHayabusa(hayabusa, directorio_datos / "evidencia"),
        motor_inferencia(),
        repositorio,
    )
    return ServicioDeCasos(
        modulo=modulo,
        repositorio=repositorio,
        escenarios=cargar_comparacion(directorio_datos / ARCHIVO_COMPARACION),
        directorio_datos=directorio_datos,
        puede_importar=puede_importar,
    )


def servicio_sembrado() -> ServicioDeCasos:
    """El caso sembrado en memoria, con el repositorio accesible a la interfaz."""
    repositorio = RepositorioEnMemoria()
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(
            eventos=eventos_sembrados(),
            sha256=SHA_SEMBRADO,
            nombre=RUTA_SEMBRADA,
            versiones=VERSIONES_SEMBRADAS,
        ),
        motor_inferencia=InferenciaControlada(propuestas=(propuesta_sembrada(),)),
        repositorio=repositorio,
    )
    creado = modulo.crear_caso(
        Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA)
    )
    modulo.investigar_caso(creado.id)
    return ServicioDeCasos(
        modulo=modulo,
        repositorio=repositorio,
        escenarios={},
        directorio_datos=None,
        puede_importar=False,
    )


_cache: dict[str, ServicioDeCasos] = {}


def obtener_servicio() -> ServicioDeCasos:
    """El servicio estable entre reruns: los ids de los casos sembrados son
    uuid por corrida y perderlos rompería la navegación."""
    directorio = os.environ.get(_ENV_DATOS)
    clave = directorio or "<sembrado>"
    if clave not in _cache:
        _cache[clave] = (
            servicio_persistido(Path(directorio))
            if directorio
            else servicio_sembrado()
        )
    return _cache[clave]
