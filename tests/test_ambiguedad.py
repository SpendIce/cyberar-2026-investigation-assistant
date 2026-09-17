"""Criterios deterministas de la demostración de ambigüedad (#8)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from streamlit.testing.v1 import AppTest

from investigacion.adaptadores.controlados import EvidenciaControlada, InferenciaControlada
from investigacion.adaptadores.ollama import construir_prompt
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.catalogo_attack import CatalogoAttack, Tecnica
from investigacion.escenarios import (
    ARCHIVO_COMPARACION,
    ESCENARIO_LEGITIMO,
    ESCENARIO_SOSPECHOSO,
    EscenarioComparacion,
    eventos_control_legitimo,
    guardar_comparacion,
    origen_control_legitimo,
)
from investigacion.modelos import (
    Caso,
    EstadoRevision,
    Hallazgo,
    ModalidadInferencia,
    Origen,
    ProcedenciaMapeo,
    PropuestaHallazgo,
)
from investigacion.modulo import ModuloDeInvestigacion

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "src" / "investigacion" / "ui" / "app.py"
GROUND_TRUTH = RAIZ / "docs" / "evaluacion" / "ground-truth-escenarios.json"


def _catalogo() -> CatalogoAttack:
    return CatalogoAttack(
        version="prueba", fecha="2026-01-01", procedencia="prueba",
        tecnicas={"T1021.002": Tecnica("T1021.002", "SMB/Windows Admin Shares")},
    )


def _hallazgo(caso_id: str, hipotesis: str = "Actividad de doble uso a revisar") -> Hallazgo:
    return Hallazgo(
        caso_id=caso_id,
        hipotesis=hipotesis,
        referencias_eventos=("ctl-2", "ctl-3"),
        campos_citados=("proceso",),
        tecnicas_candidatas=("T1021.002",),
        razon_vinculo="PSEXESVC seguido de PowerShell",
        procedencia_mapeo=ProcedenciaMapeo.MODELO,
        explicaciones_alternativas=(),
        evidencia_faltante=(),
        limitaciones=(),
        estado_revision=EstadoRevision.PENDIENTE,
    )


def _caso(caso_id: str, *, hallazgo: Hallazgo | None = None) -> Caso:
    origen = origen_control_legitimo()
    eventos = tuple(
        replace(evento, caso_id=caso_id, origen_sha256=origen.sha256 or "")
        for evento in eventos_control_legitimo()
    )
    return Caso(
        id=caso_id,
        origen=origen,
        eventos=eventos,
        hallazgos=(hallazgo or _hallazgo(caso_id),),
        modalidad_inferencia=ModalidadInferencia.MODELO_LOCAL,
    )


def _textos(at: AppTest) -> str:
    colecciones = (at.title, at.header, at.subheader, at.markdown, at.caption, at.info,
                   at.warning, at.error)
    return "\n".join(str(elemento.value) for grupo in colecciones for elemento in grupo)


def test_ground_truth_permanece_fuera_del_payload_del_modelo() -> None:
    verdad = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
    prompt = construir_prompt(eventos_control_legitimo(), _catalogo())
    payload = json.loads(prompt)

    assert set(payload) == {"eventos", "uids_citables", "tecnicas_permitidas"}
    assert "expected_context" not in prompt
    assert "known_operator_context" not in prompt
    for escenario in verdad["escenarios"]:
        assert escenario["scenario_id"] not in prompt
        assert escenario["expected_context"] not in prompt


def test_control_legitimo_conserva_ground_truth_separado() -> None:
    caso = _caso("caso-b")
    serializado = json.dumps(
        {"origen": caso.origen.__dict__, "eventos": [e.__dict__ for e in caso.eventos]},
        default=dict,
    )

    assert caso.origen.versiones["captura"] == "sintetica"
    assert "expected_context" not in serializado
    assert "legitimate" not in serializado
    assert ESCENARIO_LEGITIMO in GROUND_TRUTH.read_text(encoding="utf-8")


def test_dos_escenarios_persistidos_se_comparan_desde_la_misma_interfaz(
    tmp_path: Path, monkeypatch,
) -> None:
    repositorio = RepositorioSQLite(tmp_path / "casos.sqlite")
    repositorio.guardar(_caso("caso-a"))
    repositorio.guardar(_caso("caso-b"))
    guardar_comparacion(
        tmp_path / ARCHIVO_COMPARACION,
        (
            EscenarioComparacion(
                ESCENARIO_SOSPECHOSO, "caso-a", "Escenario A — evidencia pública",
                "Actividad a investigar", "EVTX público real",
            ),
            EscenarioComparacion(
                ESCENARIO_LEGITIMO, "caso-b", "Escenario B — control documentado",
                "Operación administrativa", "control sintético/documentado",
            ),
        ),
    )
    monkeypatch.setenv("INVESTIGACION_DATOS", str(tmp_path))

    at = AppTest.from_file(str(APP)).run()
    assert not at.exception
    assert "Escenario A — evidencia pública" in _textos(at)
    assert "Evidencia observada" in _textos(at)
    at.selectbox(key="caso-persistido").set_value("caso-b").run()

    textos = _textos(at)
    assert not at.exception
    assert "Escenario B — control documentado" in textos
    assert "Explicaciones alternativas:** No declarada por el modelo" in textos
    assert "Evidencia faltante / incertidumbre:** No especificada" in textos
    assert "Limitaciones:** No especificada" in textos
    assert "Pendiente de revisión humana" in textos
    for caso_id in ("caso-a", "caso-b"):
        caso = repositorio.obtener(caso_id)
        assert caso is not None
        existentes = {evento.uid for evento in caso.eventos}
        assert all(
            set(hallazgo.referencias_eventos) <= existentes
            for hallazgo in caso.hallazgos
        )


def test_lenguaje_de_veredicto_no_se_persiste_ni_se_muestra(
    tmp_path: Path, monkeypatch,
) -> None:
    propuesta = PropuestaHallazgo(
        hipotesis="Ataque confirmado por PowerShell",
        referencias_eventos=("ctl-2",),
        razon_vinculo="PSEXESVC presente",
    )
    origen = origen_control_legitimo()
    repositorio = RepositorioSQLite(tmp_path / "casos.sqlite")
    modulo = ModuloDeInvestigacion(
        EvidenciaControlada(
            eventos_control_legitimo(), sha256=origen.sha256 or "",
            nombre=origen.nombre or "control", versiones=origen.versiones,
        ),
        InferenciaControlada((propuesta,)),
        repositorio,
        generador_de_ids=lambda: "caso-rechazado",
    )
    caso = modulo.investigar_caso(modulo.crear_caso(origen).id)
    assert caso.hallazgos == ()
    assert any("lenguaje de veredicto" in error for error in caso.errores)

    legado = _caso(
        "caso-legado",
        hallazgo=_hallazgo("caso-legado", "Equipo comprometido por PsExec"),
    )
    repositorio.guardar(legado)
    monkeypatch.setenv("INVESTIGACION_DATOS", str(tmp_path))
    at = AppTest.from_file(str(APP)).run()
    at.selectbox(key="caso-persistido").set_value("caso-legado").run()
    textos = _textos(at)
    assert "Equipo comprometido por PsExec" not in textos
    assert "Formulación no mostrada" in textos


def test_abstencion_no_se_transforma_en_ataque(tmp_path: Path) -> None:
    origen = origen_control_legitimo()
    repositorio = RepositorioSQLite(tmp_path / "casos.sqlite")
    modulo = ModuloDeInvestigacion(
        EvidenciaControlada(
            eventos_control_legitimo(), sha256=origen.sha256 or "",
            nombre=origen.nombre or "control", versiones=origen.versiones,
        ),
        InferenciaControlada(()),
        repositorio,
        generador_de_ids=lambda: "caso-sin-hallazgos",
    )

    caso = modulo.investigar_caso(modulo.crear_caso(origen).id)

    assert caso.hallazgos == ()
    assert caso.modalidad_inferencia is ModalidadInferencia.MODELO_LOCAL
