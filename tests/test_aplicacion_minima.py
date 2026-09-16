import pytest

from investigacion.__main__ import main


def test_la_aplicacion_minima_recorre_el_contrato_y_exporta(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = main()

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "Caso caso-demo: 2 eventos" in salida
    assert "Modalidad de inferencia: modelo_local" in salida
    assert "T1021.002" in salida
