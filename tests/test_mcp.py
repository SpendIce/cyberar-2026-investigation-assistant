"""Adaptador MCP (ADR-0013): JSON-RPC por stdio sobre las operaciones del módulo.

El servidor se prueba como función pura `manejar(mensaje) -> respuesta`; el
loop de stdio es la única pieza que queda fuera de las pruebas unitarias.
`crear_caso` no se expone: exigiría aceptar una ruta de archivo arbitraria.
"""

from __future__ import annotations

import io
import json
from typing import Any

from investigacion.adaptadores.controlados import (
    EvidenciaControlada,
    InferenciaControlada,
)
from investigacion.adaptadores.mcp import ServidorMCP, servir
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.modelos import Origen
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.sembrado import (
    PROCEDENCIA_SEMBRADA,
    RUTA_SEMBRADA,
    SHA_SEMBRADO,
    VERSIONES_SEMBRADAS,
    eventos_sembrados,
    propuesta_sembrada,
)

CASO = "caso-mcp"


def _servidor(tmp_path: Any) -> ServidorMCP:
    repositorio = RepositorioSQLite(tmp_path / "casos.sqlite")
    modulo = ModuloDeInvestigacion(
        motor_evidencia=EvidenciaControlada(
            eventos=eventos_sembrados(),
            sha256=SHA_SEMBRADO,
            nombre=RUTA_SEMBRADA,
            versiones=VERSIONES_SEMBRADAS,
        ),
        motor_inferencia=InferenciaControlada(propuestas=(propuesta_sembrada(),)),
        repositorio=repositorio,
        generador_de_ids=lambda: CASO,
    )
    return ServidorMCP(modulo, repositorio)


def _crear(servidor: ServidorMCP) -> str:
    # MCP no expone crear_caso: el caso se siembra por la vía del módulo.
    caso = servidor.modulo.crear_caso(
        Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA)
    )
    return caso.id


def _llamar(servidor: ServidorMCP, metodo: str, params: dict | None = None) -> dict:
    mensaje: dict[str, Any] = {"jsonrpc": "2.0", "id": 1, "method": metodo}
    if params is not None:
        mensaje["params"] = params
    respuesta = servidor.manejar(mensaje)
    assert respuesta is not None
    return respuesta


def test_initialize_declara_capacidades_de_herramientas(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)

    respuesta = _llamar(
        servidor, "initialize", {"protocolVersion": "2024-11-05", "clientInfo": {}}
    )

    resultado = respuesta["result"]
    assert resultado["protocolVersion"] == "2024-11-05"
    assert "tools" in resultado["capabilities"]
    assert resultado["serverInfo"]["name"] == "investigacion-eventos"


def test_las_notificaciones_no_producen_respuesta(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)

    assert servidor.manejar({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_tools_list_expone_las_operaciones_sin_crear(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)

    herramientas = _llamar(servidor, "tools/list")["result"]["tools"]
    nombres = {h["name"] for h in herramientas}

    assert nombres == {
        "listar_casos",
        "consultar_caso",
        "investigar_caso",
        "exportar_caso",
        "verificar_caso",
    }
    for herramienta in herramientas:
        assert "inputSchema" in herramienta


def test_consultar_y_exportar_devuelven_el_estado_del_caso(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)
    caso_id = _crear(servidor)

    listado = _llamar(servidor, "tools/call", {"name": "listar_casos"})
    assert caso_id in listado["result"]["content"][0]["text"]

    consulta = _llamar(
        servidor, "tools/call", {"name": "consultar_caso", "arguments": {"caso_id": caso_id}}
    )
    caso = json.loads(consulta["result"]["content"][0]["text"])
    assert caso["id"] == caso_id
    assert len(caso["eventos"]) == 4

    exportacion = _llamar(
        servidor,
        "tools/call",
        {"name": "exportar_caso", "arguments": {"caso_id": caso_id, "formato": "markdown"}},
    )
    assert f"# Caso {caso_id}" in exportacion["result"]["content"][0]["text"]


def test_investigar_caso_devuelve_los_hallazgos_validados(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)
    caso_id = _crear(servidor)

    respuesta = _llamar(
        servidor,
        "tools/call",
        {"name": "investigar_caso", "arguments": {"caso_id": caso_id}},
    )

    caso = json.loads(respuesta["result"]["content"][0]["text"])
    assert len(caso["hallazgos"]) == 1
    assert caso["modalidad_inferencia"] == "modelo_local"


def test_verificar_caso_informa_la_integridad(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)
    caso_id = _crear(servidor)
    servidor.modulo.investigar_caso(caso_id)

    respuesta = _llamar(
        servidor, "tools/call", {"name": "verificar_caso", "arguments": {"caso_id": caso_id}}
    )

    verificacion = json.loads(respuesta["result"]["content"][0]["text"])
    assert verificacion["integro"] is True
    assert verificacion["sello"]


def test_un_caso_inexistente_es_un_error_de_herramienta(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)

    respuesta = _llamar(
        servidor,
        "tools/call",
        {"name": "consultar_caso", "arguments": {"caso_id": "no-existe"}},
    )

    assert respuesta["result"]["isError"] is True
    assert "no-existe" in respuesta["result"]["content"][0]["text"]


def test_un_metodo_desconocido_es_error_jsonrpc(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)

    respuesta = _llamar(servidor, "resources/list")

    assert respuesta["error"]["code"] == -32601


def test_una_herramienta_desconocida_es_error_de_herramienta(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)

    respuesta = _llamar(servidor, "tools/call", {"name": "borrar_todo"})

    assert respuesta["result"]["isError"] is True


def test_argumentos_invalidos_son_error_de_herramienta(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)

    respuesta = _llamar(
        servidor, "tools/call", {"name": "consultar_caso", "arguments": {}}
    )

    assert respuesta["result"]["isError"] is True


def test_servir_recorre_stdio_linea_a_linea(tmp_path: Any) -> None:
    servidor = _servidor(tmp_path)
    caso_id = _crear(servidor)
    entrada = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                    "params": {"name": "consultar_caso", "arguments": {"caso_id": caso_id}}})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        + "\n"
    )
    salida = io.StringIO()

    servir(servidor, entrada, salida)

    lineas = salida.getvalue().strip().splitlines()
    assert len(lineas) == 1
    respuesta = json.loads(lineas[0])
    assert respuesta["id"] == 7
    assert caso_id in respuesta["result"]["content"][0]["text"]
