"""Repositorio persistente del contrato de investigación; una conexión por operación."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
from typing import Any

from investigacion.modelos import (
    Caso, EstadoRevision, Evento, Hallazgo, ModalidadInferencia, Origen, ProcedenciaMapeo,
)


class RepositorioSQLite:
    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta.resolve()
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.ruta)) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS casos (
                    id TEXT PRIMARY KEY, datos TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS eventos (
                    caso_id TEXT NOT NULL REFERENCES casos(id),
                    uid TEXT NOT NULL, timestamp_normalizado TEXT, datos TEXT NOT NULL,
                    PRIMARY KEY (caso_id, uid)
                );
                CREATE INDEX IF NOT EXISTS eventos_cronologia
                    ON eventos(caso_id, timestamp_normalizado, uid);
            """)

    def guardar(self, caso: Caso) -> None:
        if any(e.caso_id != caso.id for e in caso.eventos):
            raise ValueError("un evento pertenece a otro caso")
        datos = asdict(caso)
        datos.pop("eventos")
        with closing(sqlite3.connect(self.ruta)) as db, db:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute(
                "INSERT INTO casos(id, datos) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET datos=excluded.datos",
                (caso.id, json.dumps(datos, ensure_ascii=False)),
            )
            db.execute("DELETE FROM eventos WHERE caso_id = ?", (caso.id,))
            db.executemany(
                "INSERT INTO eventos VALUES (?, ?, ?, ?)",
                [(caso.id, e.uid, e.timestamp_normalizado, json.dumps(asdict(e), ensure_ascii=False)) for e in caso.eventos],
            )

    def obtener(self, caso_id: str) -> Caso | None:
        with closing(sqlite3.connect(self.ruta)) as db, db:
            fila = db.execute("SELECT datos FROM casos WHERE id = ?", (caso_id,)).fetchone()
            if fila is None:
                return None
            datos = json.loads(fila[0])
            filas = db.execute(
                "SELECT datos FROM eventos WHERE caso_id = ? "
                "ORDER BY timestamp_normalizado IS NULL, timestamp_normalizado, uid",
                (caso_id,),
            ).fetchall()
        return Caso(
            id=datos["id"], origen=Origen(**datos["origen"]),
            eventos=tuple(Evento(**json.loads(f[0])) for f in filas),
            hallazgos=tuple(_hallazgo(h) for h in datos["hallazgos"]),
            errores=tuple(datos["errores"]),
            modalidad_inferencia=ModalidadInferencia(datos["modalidad_inferencia"]) if datos["modalidad_inferencia"] else None,
        )


def _hallazgo(datos: dict[str, Any]) -> Hallazgo:
    campos = dict(datos)
    for nombre in ("referencias_eventos", "campos_citados", "tecnicas_candidatas", "explicaciones_alternativas", "evidencia_faltante", "limitaciones"):
        campos[nombre] = tuple(campos[nombre])
    campos["procedencia_mapeo"] = ProcedenciaMapeo(campos["procedencia_mapeo"])
    campos["estado_revision"] = EstadoRevision(campos["estado_revision"])
    return Hallazgo(**campos)
