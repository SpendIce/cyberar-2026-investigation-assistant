"""Adaptador MCP del módulo de investigación (ADR-0013, superficie P1).

Expone las operaciones del módulo como herramientas MCP sobre JSON-RPC 2.0
por stdio (NDJSON): un mensaje por línea, una respuesta por línea. La
superficie es deliberadamente acotada: no se expone `crear_caso`, que exigiría
aceptar una ruta de archivo arbitraria, ni shell, SQL ni acceso al EVTX —
un host externo no debe convertirse en destinatario de evidencia sensible.

Las pruebas conducen `manejar` como función pura; `servir` es el loop de
entrada/salida y `main` el cableado con los adaptadores reales.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, TextIO

from investigacion.adaptadores.controlados import EvidenciaControlada
from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.adaptadores.respaldo import InferenciaConRespaldo
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.errores import CasoNoEncontrado
from investigacion.modelos import FormatoExportacion, ModalidadInferencia
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.puertos import MotorDeInferencia, RepositorioDeCasos

PROTOCOLO = "2024-11-05"

_CASO_ID = {"type": "object", "properties": {"caso_id": {"type": "string"}}, "required": ["caso_id"]}

_HERRAMIENTAS: tuple[dict[str, Any], ...] = (
    {
        "name": "listar_casos",
        "description": "Lista los identificadores de los casos persistidos.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "consultar_caso",
        "description": "Devuelve el estado validado de un caso: cronología, "
        "hallazgos, advertencias, modalidad e integridad, en JSON.",
        "inputSchema": _CASO_ID,
    },
    {
        "name": "investigar_caso",
        "description": "Ejecuta la inferencia validada sobre un caso existente "
        "y devuelve su estado actualizado. Sin inferencia disponible el caso "
        "queda en modo degradado, sin fingir conclusiones.",
        "inputSchema": _CASO_ID,
    },
    {
        "name": "exportar_caso",
        "description": "Exporta el informe reproducible del caso en markdown o json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "caso_id": {"type": "string"},
                "formato": {"type": "string", "enum": ["markdown", "json"]},
            },
            "required": ["caso_id"],
        },
    },
    {
        "name": "verificar_caso",
        "description": "Verifica la cadena de custodia del caso contra su "
        "estado persistido y, si se indica, contra el sello publicado.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "caso_id": {"type": "string"},
                "sello_publicado": {"type": "string"},
            },
            "required": ["caso_id"],
        },
    },
)


def _resultado(identificador: Any, carga: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": identificador, "result": carga}


def _error(identificador: Any, codigo: int, mensaje: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": identificador,
        "error": {"code": codigo, "message": mensaje},
    }


def _contenido(texto: str, *, error: bool = False) -> dict[str, Any]:
    carga: dict[str, Any] = {"content": [{"type": "text", "text": texto}]}
    if error:
        carga["isError"] = True
    return carga


class ServidorMCP:
    """Despacha mensajes JSON-RPC hacia el módulo y el repositorio."""

    def __init__(
        self, modulo: ModuloDeInvestigacion, repositorio: RepositorioDeCasos
    ) -> None:
        self.modulo = modulo
        self._repositorio = repositorio

    def manejar(self, mensaje: dict[str, Any]) -> dict[str, Any] | None:
        metodo = mensaje.get("method")
        identificador = mensaje.get("id")
        if metodo == "initialize":
            version = (
                mensaje.get("params", {}).get("protocolVersion") or PROTOCOLO
            )
            return _resultado(
                identificador,
                {
                    "protocolVersion": version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "investigacion-eventos", "version": "0.1.0"},
                },
            )
        if metodo == "ping":
            return _resultado(identificador, {})
        if metodo == "tools/list":
            return _resultado(identificador, {"tools": list(_HERRAMIENTAS)})
        if metodo == "tools/call":
            return self._tools_call(identificador, mensaje.get("params") or {})
        if identificador is None:
            return None
        return _error(identificador, -32601, f"método desconocido: {metodo}")

    def _tools_call(self, identificador: Any, params: dict[str, Any]) -> dict[str, Any]:
        nombre = params.get("name")
        argumentos = params.get("arguments") or {}
        if not isinstance(argumentos, dict):
            argumentos = {}
        try:
            texto = self._ejecutar(nombre, argumentos)
        except (CasoNoEncontrado, ValueError, TypeError) as exc:
            return _resultado(identificador, _contenido(str(exc), error=True))
        return _resultado(identificador, _contenido(texto))

    def _ejecutar(self, nombre: Any, argumentos: dict[str, Any]) -> str:
        if nombre == "listar_casos":
            return json.dumps(list(self._repositorio.listar()), ensure_ascii=False)
        caso_id = argumentos.get("caso_id")
        if not isinstance(caso_id, str) or not caso_id:
            raise ValueError("caso_id es obligatorio")
        if nombre == "consultar_caso":
            return self.modulo.exportar_caso(caso_id, FormatoExportacion.JSON)
        if nombre == "investigar_caso":
            caso = self.modulo.investigar_caso(caso_id)
            return self.modulo.exportar_caso(caso.id, FormatoExportacion.JSON)
        if nombre == "exportar_caso":
            formato = FormatoExportacion(argumentos.get("formato", "markdown"))
            return self.modulo.exportar_caso(caso_id, formato)
        if nombre == "verificar_caso":
            verificacion = self.modulo.verificar_caso(
                caso_id, sello_publicado=argumentos.get("sello_publicado")
            )
            return json.dumps(asdict(verificacion), ensure_ascii=False)
        raise ValueError(f"herramienta desconocida: {nombre}")


def servir(servidor: ServidorMCP, entrada: TextIO, salida: TextIO) -> None:
    """Loop stdio: un JSON-RPC por línea; las notificaciones no responden."""
    for linea in entrada:
        linea = linea.strip()
        if not linea:
            continue
        try:
            mensaje = json.loads(linea)
        except json.JSONDecodeError:
            salida.write(
                json.dumps(_error(None, -32700, "JSON inválido")) + "\n"
            )
            salida.flush()
            continue
        respuesta = servidor.manejar(mensaje)
        if respuesta is not None:
            salida.write(json.dumps(respuesta, ensure_ascii=False) + "\n")
            salida.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument("--modelo", help="Modelo Ollama para investigar casos")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument(
        "--modalidad",
        choices=[ModalidadInferencia.MODELO_LOCAL, ModalidadInferencia.NODO_PRIVADO],
        type=ModalidadInferencia,
        default=ModalidadInferencia.MODELO_LOCAL,
    )
    parser.add_argument("--modelo-respaldo")
    parser.add_argument("--ollama-url-respaldo", default="http://localhost:11434")
    parser.add_argument(
        "--permitir-externo",
        action="store_true",
        help="Permitir endpoints fuera de la infraestructura controlada",
    )
    parser.add_argument(
        "--host-controlado",
        action="append",
        default=[],
        metavar="HOST",
        help="Host adicional administrado por el equipo; repetible",
    )
    args = parser.parse_args()

    motor: MotorDeInferencia = InferenciaOllama(
        args.modelo or "sin-modelo",
        base_url=args.ollama_url,
        modalidad=args.modalidad,
        permitir_externo=args.permitir_externo,
        hosts_controlados=frozenset(args.host_controlado),
    )
    if args.modelo_respaldo:
        motor = InferenciaConRespaldo(
            motor,
            InferenciaOllama(
                args.modelo_respaldo,
                base_url=args.ollama_url_respaldo,
                modalidad=ModalidadInferencia.MODELO_LOCAL,
                permitir_externo=args.permitir_externo,
                hosts_controlados=frozenset(args.host_controlado),
            ),
        )
    repositorio = RepositorioSQLite(args.datos / "casos.sqlite")
    modulo = ModuloDeInvestigacion(
        # MCP no puede crear casos (no acepta rutas arbitrarias): el motor de
        # evidencia queda como marcador, igual que en el CLI de informe.
        EvidenciaControlada(),
        motor,
        repositorio,
    )
    servir(ServidorMCP(modulo, repositorio), sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
