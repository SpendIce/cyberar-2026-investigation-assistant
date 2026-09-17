"""Costura de la interfaz con el módulo de investigación.

Resuelve los adaptadores según el ambiente: con `INVESTIGACION_DATOS` trabaja
sobre el repositorio persistido y habilita el alta de casos (Hayabusa real +
inferencia según credenciales disponibles); sin esa variable expone el caso
sembrado con adaptadores controlados.
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
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.adaptadores.zen import InferenciaZen
from investigacion.adaptadores.respaldo import InferenciaConRespaldo
from investigacion.escenarios import (
    ARCHIVO_COMPARACION,
    EscenarioComparacion,
    cargar_comparacion,
)
from investigacion.modelos import Caso, Origen
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

_ENV_DATOS = "INVESTIGACION_DATOS"
_ENV_HAYABUSA = "HAYABUSA"
_HAYABUSA_DEFECTO = Path.home() / "tools" / "hayabusa-4.1.0" / "hayabusa-4.1.0-lin-x64-musl"


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


def _motor_inferencia() -> MotorDeInferencia:
    """El motor disponible según credenciales del ambiente, degradado al final."""
    motores: list[MotorDeInferencia] = []
    if os.environ.get("OPENCODE_API_KEY"):
        motores.append(InferenciaZen(permitir_externo=True))
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
        _motor_inferencia(),
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
