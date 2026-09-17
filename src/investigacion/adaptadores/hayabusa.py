"""Importación de un EVTX mediante la distribución local Hayabusa 4.1.0.

La cronología contiene registros detectados por reglas, no todos los registros
del EVTX. El original y la salida derivada se conservan por separado.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from investigacion.errores import ErrorDeImportacion
from investigacion.modelos import Evento, Origen, ResultadoDeEvidencia


def _sha256(ruta: Path) -> str:
    with ruta.open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest()


def _huella_directorio(ruta: Path) -> str:
    huella = hashlib.sha256()
    archivos = sorted(p for p in ruta.rglob("*") if p.is_file() and ".git" not in p.parts)
    if not archivos:
        raise ErrorDeImportacion(f"distribución incompleta: {ruta}")
    for archivo in archivos:
        huella.update(archivo.relative_to(ruta).as_posix().encode() + b"\x00")
        huella.update(_sha256(archivo).encode() + b"\n")
    return huella.hexdigest()


def detecciones_de(evento: Evento) -> tuple[dict[str, Any], ...]:
    """Las detecciones Hayabusa preservadas dentro de `contenido`, si existen.

    El adaptador guarda en `contenido` un objeto con `campos`,
    `detecciones_hayabusa` y `procedencia_mapeo`; eventos de otra procedencia
    no tienen esa estructura y devuelven vacío.
    """
    try:
        contenido = json.loads(evento.contenido or "")
    except (json.JSONDecodeError, TypeError):
        return ()
    detecciones = contenido.get("detecciones_hayabusa")
    if not isinstance(detecciones, list):
        return ()
    return tuple(d for d in detecciones if isinstance(d, dict))


def contenido_observable(evento: Evento) -> str | None:
    """`contenido` sin la salida de reglas: sólo la evidencia observable.

    Quita `detecciones_hayabusa` y `procedencia_mapeo` del objeto persistido;
    un `contenido` que no es JSON, o que no lleva detecciones, se devuelve
    tal cual.
    """
    try:
        contenido = json.loads(evento.contenido or "")
    except (json.JSONDecodeError, TypeError):
        return evento.contenido
    if not isinstance(contenido, dict) or "detecciones_hayabusa" not in contenido:
        return evento.contenido
    observable = {
        clave: valor
        for clave, valor in contenido.items()
        if clave not in ("detecciones_hayabusa", "procedencia_mapeo")
    }
    return json.dumps(observable, ensure_ascii=False, sort_keys=True)


class EvidenciaHayabusa:
    """Implementa MotorDeEvidencia sin red ni ejecución del contenido de logs."""

    def __init__(
        self, ejecutable: Path, almacen: Path, *, timeout: float = 120,
        max_bytes: int = 100 * 1024 * 1024,
    ) -> None:
        self.ejecutable = ejecutable.resolve()
        self.almacen = almacen.resolve()
        self.timeout = timeout
        self.max_bytes = max_bytes

    def analizar(self, caso_id: str, origen: Origen) -> ResultadoDeEvidencia:
        carpeta: Path | None = None
        try:
            entrada = Path(origen.ruta).resolve(strict=True)
            if not entrada.is_file() or entrada.stat().st_size > self.max_bytes:
                raise ErrorDeImportacion("se requiere un archivo dentro del límite de tamaño")
            with entrada.open("rb") as archivo:
                if archivo.read(8) != b"ElfFile\x00" or entrada.stat().st_size < 4096:
                    raise ErrorDeImportacion("fuente incompatible: encabezado EVTX inválido")
            if not origen.procedencia.strip():
                raise ErrorDeImportacion("la procedencia es obligatoria")
            versiones = self._versiones()
            self.almacen.mkdir(parents=True, exist_ok=True)
            carpeta = Path(tempfile.mkdtemp(prefix="importacion-", dir=self.almacen))
            original = carpeta / "original.evtx"
            shutil.copyfile(entrada, original)
            sha = _sha256(original)
            if sha != _sha256(entrada):
                raise ErrorDeImportacion("la fuente cambió durante la copia")
            if origen.sha256 is not None and sha != origen.sha256:
                raise ErrorDeImportacion("el SHA-256 no coincide con el esperado")
            salida = carpeta / "hayabusa.jsonl"
            argumentos = [
                str(self.ejecutable), "dfir-timeline", "-f", str(original),
                "-o", str(salida), "-t", "jsonl", "-p", "all-field-info-verbose",
                "-w", "-O", "-b", "-F", "-q", "-K", "-N", "--threads", "2",
                "-r", str(self.ejecutable.parent / "rules"),
                "-c", str(self.ejecutable.parent / "rules" / "config"),
            ]
            self._ejecutar(argumentos)
            if not salida.is_file() or salida.stat().st_size > 64 * 1024 * 1024:
                raise ErrorDeImportacion("salida Hayabusa ausente o mayor a 64 MiB")
            if _sha256(original) != sha:
                raise ErrorDeImportacion("el original se modificó durante el procesamiento")
            versiones["salida_sha256"] = _sha256(salida)
            guardado = replace(
                origen, ruta=str(original), sha256=sha,
                nombre=origen.nombre or entrada.name, versiones=versiones,
            )
            eventos = _normalizar(salida, caso_id, guardado)
            manifiesto = {
                "caso_id": caso_id, "sha256": sha, "procedencia": origen.procedencia,
                "ruta_importada": str(entrada), "archivo_original": "original.evtx",
                "salida": "hayabusa.jsonl", "versiones": versiones,
                "comando": argumentos, "eventos_normalizados": len(eventos),
                "importado_utc": datetime.now(timezone.utc).isoformat(),
                "alcance": "Registros detectados por Hayabusa; no es todo el EVTX.",
            }
            (carpeta / "manifest.json").write_text(
                json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return ResultadoDeEvidencia(guardado, eventos)
        except (OSError, ValueError, subprocess.SubprocessError, ErrorDeImportacion) as exc:
            if carpeta is not None:
                shutil.rmtree(carpeta, ignore_errors=True)
            if isinstance(exc, ErrorDeImportacion):
                raise
            raise ErrorDeImportacion(f"no se pudo importar el EVTX: {exc}") from exc

    def _ejecutar(self, argumentos: list[str]) -> str:
        resultado = subprocess.run(
            argumentos, cwd=self.ejecutable.parent, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=self.timeout, check=False,
        )
        if resultado.returncode:
            raise ErrorDeImportacion(
                f"Hayabusa terminó con código {resultado.returncode}: "
                f"{resultado.stderr[-1000:]}"
            )
        return resultado.stdout

    def _versiones(self) -> dict[str, str]:
        texto = self._ejecutar([str(self.ejecutable), "help"])
        encontrado = re.search(r"Hayabusa v(\d+\.\d+\.\d+)", texto)
        if encontrado is None or encontrado[1] != "4.1.0":
            raise ErrorDeImportacion("se requiere la distribución Hayabusa 4.1.0")
        return {
            "hayabusa": encontrado[1], "normalizador": "1",
            "perfil": "all-field-info-verbose", "formato": "jsonl",
            "binario_sha256": _sha256(self.ejecutable),
            "reglas_sha256": _huella_directorio(self.ejecutable.parent / "rules"),
            "config_sha256": _huella_directorio(self.ejecutable.parent / "config"),
        }


def _texto(valor: Any) -> str | None:
    if valor is None or valor == "" or valor == "-":
        return None
    if isinstance(valor, bool) or not isinstance(valor, (str, int)):
        raise ErrorDeImportacion("campo escalar inválido en la salida Hayabusa")
    return str(valor)


def _campo_disponible(campos: dict[str, Any], *nombres: str) -> str | None:
    for nombre in nombres:
        valor = _texto(campos.get(nombre))
        if valor is not None:
            return valor
    return None


def _timestamp(valor: str | None) -> str | None:
    if valor is None:
        return None
    formato = re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,7}))?(Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)",
        valor,
    )
    if formato is None:
        raise ErrorDeImportacion("timestamp inválido o sin zona horaria")
    fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    fraccion = (formato[1] or "").ljust(7, "0")
    # datetime conserva sólo microsegundos; retenemos los 100 ns de Windows.
    try:
        segundos = fecha.astimezone(timezone.utc).isoformat(timespec="seconds")[:19]
    except OverflowError as exc:
        raise ErrorDeImportacion("timestamp fuera del rango UTC admitido") from exc
    return f"{segundos}.{fraccion}Z"


def _normalizar(salida: Path, caso_id: str, origen: Origen) -> tuple[Evento, ...]:
    grupos: dict[tuple[str, str], list[dict[str, Any]]] = {}
    with salida.open(encoding="utf-8-sig") as archivo:
        for numero, linea in enumerate(archivo, 1):
            if not linea.strip():
                continue
            fila = json.loads(linea)
            if not isinstance(fila, dict):
                raise ErrorDeImportacion(f"fila {numero}: se esperaba un objeto JSON")
            record = _texto(fila.get("RecordID"))
            canal = _texto(fila.get("Channel"))
            fuente = _texto(fila.get("EvtxFile"))
            if not record or not record.isdecimal() or not canal:
                raise ErrorDeImportacion(f"fila {numero}: falta RecordID/canal verificable")
            if fuente is None or Path(fuente).resolve() != Path(origen.ruta):
                raise ErrorDeImportacion(f"fila {numero}: referencia a otra fuente")
            grupos.setdefault((canal, str(int(record))), []).append(fila)

    eventos = []
    for (canal, record), filas in grupos.items():
        fila = filas[0]
        for otra in filas[1:]:
            if any(otra.get(k) != fila.get(k) for k in ("Timestamp", "Computer", "EventID", "AllFieldInfo")):
                raise ErrorDeImportacion(f"datos contradictorios para RecordID={record}")
        localizador = f"Channel={canal};EventRecordID={record}"
        uid = "ev-" + hashlib.sha256(
            json.dumps([origen.sha256, canal, record], ensure_ascii=False).encode()
        ).hexdigest()
        campos = fila.get("AllFieldInfo", {})
        if not isinstance(campos, dict):
            raise ErrorDeImportacion("AllFieldInfo debe ser un objeto")
        detecciones = sorted(
            {json.dumps(f, sort_keys=True, ensure_ascii=False) for f in filas}
        )
        contenido = json.dumps({
            "campos": campos,
            "detecciones_hayabusa": [json.loads(f) for f in detecciones],
            "procedencia_mapeo": "heredado_de_regla",
        }, ensure_ascii=False, sort_keys=True)
        reglas = sorted({regla for f in filas if (regla := _texto(f.get("RuleID"))) is not None})
        timestamp = _texto(fila.get("Timestamp"))
        eventos.append(Evento(
            uid=uid, caso_id=caso_id, origen_sha256=origen.sha256 or "",
            localizador_original=localizador, timestamp_original=timestamp,
            timestamp_normalizado=_timestamp(timestamp), host=_texto(fila.get("Computer")),
            usuario=_campo_disponible(campos, "User", "AccountName", "SubjectUserName"),
            canal=canal, tipo_evento=_texto(fila.get("EventID")),
            proceso=_campo_disponible(campos, "Image", "NewProcessName"),
            proceso_padre=_campo_disponible(campos, "ParentImage", "ParentProcessName"),
            contenido=contenido, regla_hayabusa=";".join(reglas) or None,
            referencia_original=Path(origen.ruta).as_uri() + "#" + urlencode({"Channel": canal, "EventRecordID": record}),
        ))
    return tuple(sorted(eventos, key=lambda e: (e.timestamp_normalizado is None, e.timestamp_normalizado or "", e.uid)))
