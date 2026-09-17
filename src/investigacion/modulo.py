"""Módulo de investigación: crear, investigar, consultar y exportar un caso."""

from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Callable

from investigacion.custodia import (
    SelloCustodia,
    VerificacionCustodia,
    verificar_cadena,
)
from investigacion.errores import CasoNoEncontrado, HallazgoInvalido, InferenciaNoDisponible
from investigacion.exportacion import exportar
from investigacion.modelos import (
    Caso,
    EstadoRevision,
    Evento,
    FormatoExportacion,
    Hallazgo,
    ModalidadInferencia,
    Origen,
    PropuestaHallazgo,
)
from investigacion.puertos import (
    MotorDeEvidencia,
    MotorDeInferencia,
    RepositorioDeCasos,
    ValidadorDeHallazgos,
)
from investigacion.validacion import ValidadorDeReferencias


class ModuloDeInvestigacion:
    def __init__(
        self,
        motor_evidencia: MotorDeEvidencia,
        motor_inferencia: MotorDeInferencia,
        repositorio: RepositorioDeCasos,
        validador: ValidadorDeHallazgos | None = None,
        generador_de_ids: Callable[[], str] | None = None,
    ) -> None:
        self._motor_evidencia = motor_evidencia
        self._motor_inferencia = motor_inferencia
        self._repositorio = repositorio
        self._validador = validador or ValidadorDeReferencias()
        self._generador_de_ids = generador_de_ids or (lambda: uuid.uuid4().hex)

    def crear_caso(self, origen: Origen, contexto: str = "") -> Caso:
        caso_id = self._generador_de_ids()
        resultado = self._motor_evidencia.analizar(caso_id, origen)
        caso = Caso(
            id=caso_id,
            origen=resultado.origen,
            eventos=resultado.eventos,
            contexto=contexto,
        )
        self._repositorio.guardar(caso)
        return caso

    def investigar_caso(self, caso_id: str) -> Caso:
        caso = self.consultar_caso(caso_id)
        try:
            propuestas = self._motor_inferencia.proponer(
                caso_id, caso.eventos, caso.contexto
            )
        except InferenciaNoDisponible as exc:
            return self._persistir(
                caso,
                hallazgos=caso.hallazgos,
                errores=(*caso.errores, str(exc)),
                modalidad=ModalidadInferencia.DEGRADADO,
            )
        hallazgos, rechazos = self._validar_propuestas(caso_id, propuestas, caso.eventos)
        return self._persistir(
            caso,
            hallazgos=hallazgos,
            errores=(*caso.errores, *self._motor_inferencia.advertencias, *rechazos),
            modalidad=self._motor_inferencia.modalidad,
        )

    def _validar_propuestas(
        self,
        caso_id: str,
        propuestas: tuple[PropuestaHallazgo, ...],
        eventos: tuple[Evento, ...],
    ) -> tuple[tuple[Hallazgo, ...], tuple[str, ...]]:
        aceptados: list[Hallazgo] = []
        rechazos: list[str] = []
        for propuesta in propuestas:
            try:
                aceptados.append(self._validador.validar(caso_id, propuesta, eventos))
            except HallazgoInvalido as exc:
                rechazos.append(str(exc))
        return tuple(aceptados), tuple(rechazos)

    def consultar_caso(self, caso_id: str) -> Caso:
        caso = self._repositorio.obtener(caso_id)
        if caso is None:
            raise CasoNoEncontrado(f"caso inexistente: {caso_id}")
        return caso

    def revisar_hallazgo(
        self, caso_id: str, indice: int, estado: EstadoRevision
    ) -> Caso:
        """Registra la revisión humana de un hallazgo (pendiente/aceptada/rechazada)."""
        caso = self.consultar_caso(caso_id)
        if not 0 <= indice < len(caso.hallazgos):
            raise ValueError(f"hallazgo fuera de rango: {indice}")
        hallazgos = list(caso.hallazgos)
        hallazgos[indice] = replace(hallazgos[indice], estado_revision=estado)
        actualizado = replace(caso, hallazgos=tuple(hallazgos))
        self._repositorio.guardar(actualizado)
        return actualizado

    def renombrar_caso(self, caso_id: str, nombre: str) -> Caso:
        caso = self.consultar_caso(caso_id)
        actualizado = replace(caso, origen=replace(caso.origen, nombre=nombre))
        self._repositorio.guardar(actualizado)
        return actualizado

    def actualizar_contexto(self, caso_id: str, contexto: str) -> Caso:
        """Persiste un nuevo contexto declarado; re-inferir es una llamada aparte."""
        caso = self.consultar_caso(caso_id)
        actualizado = replace(caso, contexto=contexto)
        self._repositorio.guardar(actualizado)
        return actualizado

    def eliminar_caso(self, caso_id: str) -> None:
        """Baja de un caso: borra estado y cadena de custodia persistidos.

        Los artefactos de evidencia en disco (EVTX original, cronología
        Hayabusa) no se destruyen: la baja retira el caso del repositorio,
        no la evidencia del origen.
        """
        self.consultar_caso(caso_id)
        self._repositorio.eliminar(caso_id)

    def exportar_caso(
        self, caso_id: str, formato: FormatoExportacion = FormatoExportacion.MARKDOWN
    ) -> str:
        caso = self.consultar_caso(caso_id)
        cadena = self._repositorio.cadena_custodia(caso_id)
        custodia = (
            SelloCustodia(sello=cadena[-1].sello, escrituras=len(cadena))
            if cadena
            else None
        )
        return exportar(caso, formato, custodia)

    def verificar_caso(
        self, caso_id: str, sello_publicado: str | None = None
    ) -> VerificacionCustodia:
        """Verifica la cadena de custodia persistida contra el estado del caso.

        Con `sello_publicado` (el sello que viajó en un informe exportado)
        también detecta una cadena reescrita o una reversión del registro.
        """
        caso = self.consultar_caso(caso_id)
        cadena = self._repositorio.cadena_custodia(caso_id)
        discrepancias = list(verificar_cadena(cadena, caso))
        sello = cadena[-1].sello if cadena else None
        if sello_publicado is not None and sello != sello_publicado:
            discrepancias.append(
                "la cadena persistida no coincide con el sello publicado"
            )
        return VerificacionCustodia(
            integro=not discrepancias,
            sello=sello,
            discrepancias=tuple(discrepancias),
        )

    def _persistir(
        self,
        caso: Caso,
        hallazgos: tuple[Hallazgo, ...],
        errores: tuple[str, ...],
        modalidad: ModalidadInferencia | None,
    ) -> Caso:
        actualizado = replace(
            caso,
            hallazgos=hallazgos,
            errores=errores,
            modalidad_inferencia=modalidad,
        )
        self._repositorio.guardar(actualizado)
        return actualizado
