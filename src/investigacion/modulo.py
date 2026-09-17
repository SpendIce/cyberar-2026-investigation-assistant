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

    def crear_caso(self, origen: Origen) -> Caso:
        caso_id = self._generador_de_ids()
        resultado = self._motor_evidencia.analizar(caso_id, origen)
        caso = Caso(id=caso_id, origen=resultado.origen, eventos=resultado.eventos)
        self._repositorio.guardar(caso)
        return caso

    def investigar_caso(self, caso_id: str) -> Caso:
        caso = self.consultar_caso(caso_id)
        try:
            propuestas = self._motor_inferencia.proponer(caso_id, caso.eventos)
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
