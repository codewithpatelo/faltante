"""Cada chequeo, probado contra un caso armado a mano donde la respuesta es obvia."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.diagnostico import Foto, Publicacion as P, diagnosticar  # noqa: E402


def sust(n, precio=10000, vendidos=100):
    return [P(f"sustituto {i}", False, vendidos, precio, False) for i in range(n)]


def test_sin_demanda():
    f = Foto("x", [P("prod", True, 0, 10000, True)] + [P("otro", False, 0, 9000, False)] * 5)
    assert diagnosticar(f)["conclusion"] == "sin_demanda"


def test_precio_explica():
    f = Foto("x", [P("prod", True, 0, 30000, True)] + sust(5, precio=10000))
    d = diagnosticar(f)
    assert d["chequeos"]["precio"]["resultado"] == "explica"
    assert d["conclusion"] == "no_compite_en_precio"


def test_espera_explica_con_mismo_producto_local_e_intl():
    f = Foto("x", [P("prod local", False, 100, 20000, True), P("prod intl", True, 0, 18000, True)] + sust(3))
    d = diagnosticar(f)
    assert d["chequeos"]["espera"]["resultado"] == "explica"
    assert d["conclusion"] == "ya_atendido"  # la espera explica el mecanismo, pero no es un hueco


def test_compran_aunque_esperen():
    f = Foto("x", [P("prod intl", True, 50, 15000, True)] + sust(3))
    assert diagnosticar(f)["conclusion"] == "oportunidad_compran_aunque_esperen"


def test_preferencia_local():
    f = Foto("x", [P("prod local", False, 0, 10000, True)] + sust(5, precio=10000))
    d = diagnosticar(f)
    assert d["chequeos"]["preferencia_local"]["resultado"] == "explica"
    assert d["conclusion"] == "prefieren_otras_opciones"


def test_solo_intl_a_precio_parecido_es_candidato_a_probar():
    f = Foto("x", [P("prod intl", True, 0, 10500, True)] + sust(5, precio=10000))
    assert diagnosticar(f)["conclusion"] == "candidato_a_probar"


def test_ya_atendido():
    f = Foto("x", [P("prod local", False, 500, 10000, True)] + sust(3))
    assert diagnosticar(f)["conclusion"] == "ya_atendido"
