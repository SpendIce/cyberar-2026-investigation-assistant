"""Prueba opt-in con Hayabusa y un lector EVTX independiente; ver docs/evidencia.md."""

import hashlib
import json
import os
from pathlib import Path
from xml.etree import ElementTree

import pytest

from investigacion.adaptadores.controlados import InferenciaNoDisponibleControlada
from investigacion.adaptadores.hayabusa import EvidenciaHayabusa
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.modelos import Origen
from investigacion.modulo import ModuloDeInvestigacion


@pytest.mark.skipif(not os.environ.get("HAYABUSA_BIN"), reason="requiere HAYABUSA_BIN y fixture público")
def test_evtx_publico_hayabusa_sqlite_y_registro_original(tmp_path):
    from Evtx.Evtx import Evtx

    carpeta = Path(__file__).parent / "fixtures" / "publico"
    manifiesto = json.loads((carpeta / "manifest.json").read_text())
    entrada = carpeta / manifiesto["archivo"]
    assert entrada.is_file(), "Ejecutar uv run python scripts/descargar_fixture.py"
    motor = EvidenciaHayabusa(Path(os.environ["HAYABUSA_BIN"]), tmp_path / "evidencia")
    m = ModuloDeInvestigacion(motor, InferenciaNoDisponibleControlada(), RepositorioSQLite(tmp_path / "casos.sqlite"))
    caso = m.crear_caso(Origen(str(entrada), manifiesto["url"], sha256=manifiesto["sha256"]))
    reabierto = RepositorioSQLite(tmp_path / "casos.sqlite").obtener(caso.id)
    assert reabierto == caso
    assert hashlib.sha256(Path(caso.origen.ruta).read_bytes()).hexdigest() == manifiesto["sha256"]
    # Referencia independiente: XML extraído del EVTX conservado, no de Hayabusa.
    ns = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
    registros = {}
    with Evtx(caso.origen.ruta) as log:
        for registro in log.records():
            raiz = ElementTree.fromstring(registro.xml())
            sistema = raiz.find("e:System", ns)
            record = sistema.findtext("e:EventRecordID", namespaces=ns)
            registros[record] = sistema
    assert len(caso.eventos) == 3
    assert {e.localizador_original for e in caso.eventos} == {
        "Channel=System;EventRecordID=8423", "Channel=System;EventRecordID=8424",
        "Channel=System;EventRecordID=8426",
    }
    for evento in caso.eventos:
        record = evento.localizador_original.rsplit("=", 1)[1]
        original = registros[record]
        assert evento.tipo_evento == original.findtext("e:EventID", namespaces=ns)
        assert evento.canal == original.findtext("e:Channel", namespaces=ns)
        assert evento.host == original.findtext("e:Computer", namespaces=ns)
    segundo = m.crear_caso(Origen(str(entrada), manifiesto["url"]))
    assert [e.uid for e in segundo.eventos] == [e.uid for e in caso.eventos]
