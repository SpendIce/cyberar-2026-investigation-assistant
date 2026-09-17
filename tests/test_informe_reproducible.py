"""Prueba de aceptación del informe reproducible (issue #10)."""

import json
import re
import subprocess
import sys
from pathlib import Path

from investigacion.adaptadores.controlados import (
    EvidenciaControlada,
    InferenciaControlada,
)
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.modelos import (
    Evento,
    FormatoExportacion,
    ModalidadInferencia,
    Origen,
    PropuestaHallazgo,
)
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.puertos import MotorDeInferencia
from investigacion.sembrado import (
    PROCEDENCIA_SEMBRADA,
    RUTA_SEMBRADA,
    SHA_SEMBRADO,
    VERSIONES_SEMBRADAS,
    eventos_sembrados,
    propuesta_sembrada,
)


class _InferenciaEspia:
    """Envuelve un motor de inferencia contando cuántas veces se lo invoca."""

    def __init__(self, motor: MotorDeInferencia) -> None:
        self._motor = motor
        self.invocaciones = 0

    @property
    def modalidad(self) -> ModalidadInferencia:
        return self._motor.modalidad

    def proponer(
        self, caso_id: str, evidencia: tuple[Evento, ...]
    ) -> tuple[PropuestaHallazgo, ...]:
        self.invocaciones += 1
        return self._motor.proponer(caso_id, evidencia)


def _caso_investigado(tmp_path: Path) -> tuple[ModuloDeInvestigacion, _InferenciaEspia, str]:
    propuestas = (
        propuesta_sembrada(),
        PropuestaHallazgo(
            hipotesis="Propuesta con referencia inventada",
            referencias_eventos=("ev-inexistente",),
        ),
    )
    espia = _InferenciaEspia(InferenciaControlada(propuestas=propuestas))
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(
            eventos=eventos_sembrados(),
            sha256=SHA_SEMBRADO,
            nombre=RUTA_SEMBRADA,
            versiones=VERSIONES_SEMBRADAS,
        ),
        motor_inferencia=espia,
        repositorio=RepositorioSQLite(tmp_path / "casos.sqlite"),
        generador_de_ids=lambda: "caso-informe",
    )
    caso = modulo.crear_caso(Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA))
    modulo.investigar_caso(caso.id)
    return modulo, espia, caso.id


def test_los_formatos_representan_el_mismo_estado_validado(tmp_path: Path) -> None:
    modulo, espia, caso_id = _caso_investigado(tmp_path)
    caso = modulo.consultar_caso(caso_id)
    invocaciones_tras_investigar = espia.invocaciones

    contenido_json = modulo.exportar_caso(caso_id, FormatoExportacion.JSON)
    contenido_markdown = modulo.exportar_caso(caso_id, FormatoExportacion.MARKDOWN)

    assert modulo.exportar_caso(caso_id, FormatoExportacion.JSON) == contenido_json
    assert modulo.exportar_caso(caso_id, FormatoExportacion.MARKDOWN) == contenido_markdown
    assert espia.invocaciones == invocaciones_tras_investigar

    datos = json.loads(contenido_json)
    assert datos["id"] == caso_id
    assert datos["errores"]
    assert datos["origen"]["sha256"] == SHA_SEMBRADO
    assert datos["origen"]["procedencia"] == PROCEDENCIA_SEMBRADA
    assert datos["origen"]["versiones"] == dict(VERSIONES_SEMBRADAS)
    assert datos["modalidad_inferencia"] == "modelo_local"

    hallazgos_json = datos["hallazgos"]
    assert [h["hipotesis"] for h in hallazgos_json] == [
        h.hipotesis for h in caso.hallazgos
    ]
    assert set(datos["errores"]) == set(caso.errores)
    assert hallazgos_json[0]["referencias_eventos"] == list(
        caso.hallazgos[0].referencias_eventos
    )
    assert hallazgos_json[0]["estado_revision"] == "pendiente"
    uids = {evento["uid"] for evento in datos["eventos"]}
    assert set(hallazgos_json[0]["referencias_eventos"]) <= uids

    assert f"# Caso {caso_id}" in contenido_markdown
    assert SHA_SEMBRADO in contenido_markdown
    assert PROCEDENCIA_SEMBRADA in contenido_markdown
    assert "catalogo_attack subconjunto-local-2026" in contenido_markdown
    assert "modelo_local" in contenido_markdown
    for hallazgo in caso.hallazgos:
        assert hallazgo.hipotesis in contenido_markdown
        assert hallazgo.razon_vinculo in contenido_markdown
        for limitacion in hallazgo.limitaciones:
            assert limitacion in contenido_markdown
        for referencia in hallazgo.referencias_eventos:
            assert re.search(rf"`{referencia}`", contenido_markdown)
    assert "## Advertencias" in contenido_markdown
    for error in caso.errores:
        assert error in contenido_markdown


def test_el_cli_exporta_el_informe_persistido_sin_inferencia(tmp_path: Path) -> None:
    _, espia, caso_id = _caso_investigado(tmp_path)
    salida_md = tmp_path / "informe.md"
    salida_json = tmp_path / "informe.json"

    for formato, salida in (("markdown", salida_md), ("json", salida_json)):
        resultado = subprocess.run(
            [
                sys.executable,
                "-m",
                "investigacion.informe",
                "--datos",
                str(tmp_path),
                "--caso",
                caso_id,
                "--formato",
                formato,
                "--salida",
                str(salida),
            ],
            capture_output=True,
            text=True,
        )
        assert resultado.returncode == 0, resultado.stderr

    datos = json.loads(salida_json.read_text(encoding="utf-8"))
    assert datos["id"] == caso_id
    assert datos["origen"]["sha256"] == SHA_SEMBRADO
    assert len(datos["hallazgos"]) == 1
    markdown = salida_md.read_text(encoding="utf-8")
    assert datos["hallazgos"][0]["hipotesis"] in markdown
    assert datos["errores"]
    assert "## Advertencias" in markdown
    assert espia.invocaciones == 1
