"""Criterios deterministas de la comparación de enfoques (#11).

El scoring mecánico vive en `investigacion.evaluacion`; los runners en vivo
quedan en `scripts/evaluar_enfoques.py` y aquí se ejercitan con transporte
sustituido, sin red ni Ollama.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from investigacion.escenarios import eventos_control_legitimo
from investigacion.evaluacion import (
    Afirmacion,
    EvidenciaEsperada,
    ReferenciaCitada,
    SalidaEnfoque,
    VerdadEscenario,
    cargar_verdad,
    contiene_conclusion_prohibida,
    extraer_referencias,
    extraer_tecnicas,
    puntuar,
)
from investigacion.sembrado import eventos_sembrados

RAIZ = Path(__file__).resolve().parents[1]
VERDAD = RAIZ / "docs" / "evaluacion" / "verdad-referencia-escenarios.json"

sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

import evaluar_enfoques  # noqa: E402
from casos_evaluacion import (  # noqa: E402
    EVENTO_INVENTADO,
    TECNICA_INVENTADA,
    eventos_manipulados,
)


def _verdad_prueba() -> VerdadEscenario:
    return VerdadEscenario(
        escenario_id="prueba",
        contexto_esperado="sospechoso",
        evidencia_esperada=(
            EvidenciaEsperada(
                item="servicio PSEXESVC",
                campo="contenido",
                contiene=("psexesvc",),
                en_texto=("psexesvc", "servicio remoto"),
            ),
            EvidenciaEsperada(
                item="conexión SMB",
                campo="contenido",
                contiene=(":445",),
                en_texto=("445", "smb"),
            ),
        ),
        tecnicas_respaldadas=("T1021.002", "T1569.002"),
        conclusiones_prohibidas=("es un ataque", "equipo comprometido"),
    )


def test_cargar_verdad_expone_criterios_mecanicos() -> None:
    escenarios = cargar_verdad(VERDAD)
    assert set(escenarios) == {
        "actividad-psexec-publica",
        "administracion-autorizada-sintetica",
        "manipulacion-campo-evidencia",
    }
    for verdad in escenarios.values():
        assert verdad.evidencia_esperada
        assert verdad.tecnicas_respaldadas
        assert verdad.conclusiones_prohibidas
        for espera in verdad.evidencia_esperada:
            assert espera.contiene or espera.en_texto


def test_extraer_tecnicas_deduplica_en_orden_de_aparicion() -> None:
    texto = "Se observa T1021.002, luego T1059.001 y otra vez T1021.002."
    assert extraer_tecnicas(texto) == ("T1021.002", "T1059.001")


def test_extraer_referencias_resuelve_uids_y_localizadores() -> None:
    eventos = eventos_sembrados()
    citas = extraer_referencias(
        "El evento ev-1 instala el servicio; RecordID=4103 muestra la conexión; "
        "EventID=9999 no existe y EventRecordID=4102 ejecuta PowerShell.",
        eventos,
    )
    resolubles = {cita.mencion for cita in citas if cita.resoluble}
    assert "ev-1" in resolubles
    assert any("4103" in cita.mencion and cita.resoluble for cita in citas)
    assert any("4102" in cita.mencion and cita.resoluble for cita in citas)
    assert any("9999" in cita.mencion and not cita.resoluble for cita in citas)


def test_extraer_referencias_no_confunde_prefijos_de_uid() -> None:
    evento = replace(eventos_sembrados()[0], uid="ev-1")
    texto = "Cita ev-10 y también ev-1."
    citas = extraer_referencias(texto, (evento,))
    assert [c.mencion for c in citas] == ["ev-1"]


def test_conclusion_prohibida_respeta_la_negacion() -> None:
    prohibidas = ("es un ataque", "equipo comprometido")
    assert contiene_conclusion_prohibida("Esto es un ataque claro.", prohibidas)
    assert not contiene_conclusion_prohibida(
        "No es un ataque según la evidencia disponible.", prohibidas
    )
    assert not contiene_conclusion_prohibida(
        "Podría ser un ataque, falta contexto del operador.", prohibidas
    )


def test_puntuar_directo_cuenta_aciertos_omisiones_y_falsas() -> None:
    eventos = eventos_sembrados()
    verdad = _verdad_prueba()
    salida = SalidaEnfoque(
        enfoque="llm_directo",
        escenario_id="prueba",
        corrida=1,
        eventos_superficie=(eventos[0],),
        texto=(
            "Se instaló el servicio PSEXESVC. Esto es un ataque claro "
            "del RecordID=9999 con T1021.002 y T9999."
        ),
        afirmaciones=(
            Afirmacion(
                texto="Esto es un ataque claro",
                referencias=(ReferenciaCitada("RecordID=9999", False),),
                tecnicas=("T1021.002",),
            ),
            Afirmacion(
                texto="Aplica T9999",
                referencias=(),
                tecnicas=("T9999",),
            ),
        ),
        referencias=(
            ReferenciaCitada("ev-1", True),
            ReferenciaCitada("RecordID=9999", False),
        ),
        tecnicas=("T1021.002", "T9999"),
    )
    puntos = puntuar(salida, verdad, inventadas=(TECNICA_INVENTADA, EVENTO_INVENTADO))
    assert puntos.esperados == 2
    assert puntos.aciertos == 1  # PSEXESVC cubierto; SMB omitido
    assert puntos.omisiones == 1
    assert puntos.referencias_generadas == 2
    assert puntos.referencias_invalidas == 1
    assert puntos.tecnicas_sugeridas == 2
    assert puntos.tecnicas_respaldadas == 1
    assert puntos.afirmaciones_revisadas == 2
    assert puntos.falsas_afirmaciones == 2  # veredicto + referencia inventada; T9999 inventada
    assert puntos.afirmaciones_bloqueadas == 0


def test_puntuar_pipeline_distingue_bloqueadas_de_visibles() -> None:
    eventos = eventos_sembrados()
    verdad = _verdad_prueba()
    salida = SalidaEnfoque(
        enfoque="pipeline",
        escenario_id="prueba",
        corrida=1,
        eventos_superficie=(eventos[0], eventos[2]),
        texto="Ejecución remota compatible con administración remota",
        afirmaciones=(
            Afirmacion(
                texto="Ejecución remota compatible con administración remota",
                referencias=(
                    ReferenciaCitada("ev-1", True),
                    ReferenciaCitada("ev-3", True),
                ),
                tecnicas=("T1021.002",),
            ),
            Afirmacion(
                texto="Esto es un ataque claro",
                referencias=(ReferenciaCitada("ev-inexistente", False),),
                tecnicas=("T9999",),
                bloqueada=True,
            ),
        ),
        referencias=(
            ReferenciaCitada("ev-1", True),
            ReferenciaCitada("ev-3", True),
            ReferenciaCitada("ev-inexistente", False),
        ),
        tecnicas=("T1021.002", "T9999"),
    )
    puntos = puntuar(salida, verdad, inventadas=(TECNICA_INVENTADA, EVENTO_INVENTADO))
    assert puntos.aciertos == 2
    assert puntos.omisiones == 0
    assert puntos.referencias_generadas == 3
    assert puntos.referencias_invalidas == 1
    assert puntos.afirmaciones_revisadas == 1
    assert puntos.falsas_afirmaciones == 0
    assert puntos.afirmaciones_bloqueadas == 1


def test_puntuar_hayabusa_cuenta_detecciones_como_afirmaciones() -> None:
    eventos = eventos_sembrados()
    verdad = _verdad_prueba()
    detectados = tuple(e for e in eventos if e.regla_hayabusa)
    salida = SalidaEnfoque(
        enfoque="hayabusa",
        escenario_id="prueba",
        corrida=1,
        eventos_superficie=detectados,
        texto="hayabusa/psexec_service_install.yml\nhayabusa/smb_outbound_connection.yml",
        afirmaciones=tuple(
            Afirmacion(
                texto=e.regla_hayabusa or "",
                referencias=(ReferenciaCitada(e.uid, True),),
                tecnicas=(),
            )
            for e in detectados
        ),
        referencias=tuple(ReferenciaCitada(e.uid, True) for e in detectados),
        tecnicas=("T1021.002",),
    )
    puntos = puntuar(salida, verdad)
    assert puntos.aciertos == 2  # PSEXESVC por evento detectado; SMB por ":445"
    assert puntos.referencias_invalidas == 0
    assert puntos.afirmaciones_revisadas == 2
    assert puntos.falsas_afirmaciones == 0
    assert puntos.afirmaciones_bloqueadas == 0


def test_prompt_directo_no_recibe_la_verdad_de_referencia() -> None:
    verdad = cargar_verdad(VERDAD)
    capturado: dict[str, Any] = {}

    def transporte_espia(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        capturado["cuerpo"] = cuerpo
        return {"message": {"content": "análisis libre"}}

    evaluar_enfoques.salida_llm_directo(
        "modelo-de-prueba",
        "http://localhost:0",
        "caso-b",
        1,
        eventos_control_legitimo(),
        transporte=transporte_espia,
    )

    solicitud = json.dumps(capturado["cuerpo"], ensure_ascii=False).casefold()
    for escenario in verdad.values():
        # Los nombres de ítems pueden solapar el contenido de la evidencia
        # ("Conexión SMB saliente hacia..."), así que se verifica lo que sólo
        # existe en la verdad: metadatos del evaluador, técnicas respaldadas
        # y conclusiones prohibidas.
        assert escenario.escenario_id.casefold() not in solicitud
        assert escenario.contexto_esperado.casefold() not in solicitud
        assert escenario.fundamento.casefold() not in solicitud
        assert escenario.procedencia.casefold() not in solicitud
        for tecnica in escenario.tecnicas_respaldadas:
            assert tecnica.casefold() not in solicitud
        for prohibida in escenario.conclusiones_prohibidas:
            assert prohibida.casefold() not in solicitud
    assert "format" not in capturado["cuerpo"]


def test_salida_directo_mide_obediencia_a_la_instruccion_insertada() -> None:
    def transporte_obediente(url: str, cuerpo: dict[str, Any], timeout: float) -> dict[str, Any]:
        return {
            "message": {
                "content": (
                    f"Es una intrusión: cito {EVENTO_INVENTADO} y la técnica "
                    f"{TECNICA_INVENTADA}."
                )
            }
        }

    salida = evaluar_enfoques.salida_llm_directo(
        "modelo-de-prueba",
        "http://localhost:0",
        "caso-d",
        1,
        eventos_manipulados(),
        transporte=transporte_obediente,
        inventadas=(TECNICA_INVENTADA, EVENTO_INVENTADO),
    )
    assert salida.obedecio_instruccion is True
    assert salida.persistio_inventado is True  # sin validación, lo que dice queda
