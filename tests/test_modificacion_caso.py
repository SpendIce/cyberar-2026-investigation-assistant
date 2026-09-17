"""Operaciones de modificación del caso: revisión humana, renombrar, contexto y baja (#24).

Cada operación pasa por `guardar`, así que la cadena de custodia registra la
escritura. La baja retira el caso y su cadena del repositorio.
"""

from __future__ import annotations

import pytest

from investigacion.adaptadores.controlados import EvidenciaControlada, InferenciaControlada
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.errores import CasoNoEncontrado
from investigacion.modelos import EstadoRevision, Origen, PropuestaHallazgo
from investigacion.modulo import ModuloDeInvestigacion


def _modulo(
    propuestas: tuple[PropuestaHallazgo, ...] = (),
) -> tuple[ModuloDeInvestigacion, RepositorioEnMemoria]:
    repositorio = RepositorioEnMemoria()
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(),
        motor_inferencia=InferenciaControlada(propuestas=propuestas),
        repositorio=repositorio,
        generador_de_ids=lambda: "caso-abm",
    )
    return modulo, repositorio


def _caso_investigado() -> tuple[ModuloDeInvestigacion, RepositorioEnMemoria, str]:
    propuesta = PropuestaHallazgo(
        hipotesis="Actividad de ejemplo",
        referencias_eventos=(),
        razon_vinculo="vínculo de ejemplo",
    )
    modulo, repositorio = _modulo(propuestas=(propuesta,))
    caso = modulo.crear_caso(Origen(ruta="origen.evtx", procedencia="prueba"))
    return modulo, repositorio, modulo.investigar_caso(caso.id).id


def test_revisar_hallazgo_registra_estado_y_custodia() -> None:
    modulo, repositorio, caso_id = _caso_investigado()
    antes = len(repositorio.cadena_custodia(caso_id))

    caso = modulo.revisar_hallazgo(caso_id, 0, EstadoRevision.ACEPTADA)

    assert caso.hallazgos[0].estado_revision is EstadoRevision.ACEPTADA
    assert len(repositorio.cadena_custodia(caso_id)) == antes + 1
    assert modulo.consultar_caso(caso_id).hallazgos[0].estado_revision is EstadoRevision.ACEPTADA


def test_revisar_hallazgo_fuera_de_rango_falla() -> None:
    modulo, _, caso_id = _caso_investigado()

    with pytest.raises(ValueError, match="fuera de rango"):
        modulo.revisar_hallazgo(caso_id, 5, EstadoRevision.RECHAZADA)


def test_renombrar_caso_actualiza_el_nombre_del_origen() -> None:
    modulo, _, caso_id = _caso_investigado()

    caso = modulo.renombrar_caso(caso_id, "intrusion-fileserver")

    assert caso.origen.nombre == "intrusion-fileserver"
    assert modulo.consultar_caso(caso_id).origen.nombre == "intrusion-fileserver"


def test_actualizar_contexto_persiste_y_alimenta_la_reinferencia() -> None:
    capturado: list[str] = []

    class InferenciaEspia:
        @property
        def modalidad(self):
            from investigacion.modelos import ModalidadInferencia
            return ModalidadInferencia.MODELO_LOCAL

        @property
        def advertencias(self) -> tuple[str, ...]:
            return ()

        def proponer(self, caso_id, evidencia, contexto=""):
            capturado.append(contexto)
            return ()

    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(),
        motor_inferencia=InferenciaEspia(),
        repositorio=RepositorioEnMemoria(),
        generador_de_ids=lambda: "caso-abm",
    )
    caso = modulo.crear_caso(Origen(ruta="origen.evtx", procedencia="prueba"))

    modulo.actualizar_contexto(caso.id, "host de administración autorizado")
    modulo.investigar_caso(caso.id)

    assert modulo.consultar_caso(caso.id).contexto == "host de administración autorizado"
    assert capturado == ["host de administración autorizado"]


def test_eliminar_caso_retira_estado_y_custodia() -> None:
    modulo, repositorio, caso_id = _caso_investigado()

    modulo.eliminar_caso(caso_id)

    assert caso_id not in repositorio.listar()
    assert repositorio.obtener(caso_id) is None
    assert repositorio.cadena_custodia(caso_id) == ()
    with pytest.raises(CasoNoEncontrado):
        modulo.consultar_caso(caso_id)


def test_eliminar_caso_inexistente_falla() -> None:
    modulo, _, _ = _caso_investigado()

    with pytest.raises(CasoNoEncontrado):
        modulo.eliminar_caso("no-existe")
