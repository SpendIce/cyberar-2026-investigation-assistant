from pathlib import Path

import pytest

from investigacion.catalogo_attack import cargar_catalogo


def test_el_catalogo_por_defecto_carga_version_fecha_y_tecnicas_conocidas() -> None:
    catalogo = cargar_catalogo()

    assert catalogo.version
    assert catalogo.fecha
    assert catalogo.procedencia
    assert catalogo.contiene("T1021.002")
    assert catalogo.contiene("T1569.002")
    assert not catalogo.contiene("T9999")


def test_un_catalogo_puede_cargarse_desde_una_ruta_explicita(tmp_path: Path) -> None:
    ruta = tmp_path / "catalogo.json"
    ruta.write_text(
        '{"version": "v1", "fecha": "2026-01-01", "procedencia": "prueba", '
        '"tecnicas": [{"id": "T1000", "nombre": "Técnica de prueba"}]}',
        encoding="utf-8",
    )

    catalogo = cargar_catalogo(ruta)

    assert catalogo.version == "v1"
    assert catalogo.contiene("T1000")
    assert catalogo.tecnicas["T1000"].nombre == "Técnica de prueba"


def test_cargar_un_catalogo_inexistente_falla_explicitamente(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        cargar_catalogo(tmp_path / "no-existe.json")
