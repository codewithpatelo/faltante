"""El emparejamiento por reglas: qué cuenta como "es el producto"."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from emparejar import emparejar  # noqa: E402

STANLEY = [["stanley"], ["quencher"]]
TURELAR = [["turelar"]]


def test_producto_con_todas_las_palabras():
    assert emparejar("Vaso Térmico Stanley Quencher H2.0 1.18 L", STANLEY) == (True, False)


def test_acentos_y_mayusculas_no_importan():
    assert emparejar("MIXER DE INMERSIÓN TURELAR 1100W", TURELAR) == (True, False)


def test_falta_una_palabra_es_sustituto():
    assert emparejar("Termo Stanley Classic 1.4 L", STANLEY) == (False, False)


def test_accesorio_no_es_el_producto():
    assert emparejar("Funda De Silicona Para Stanley Quencher 40 Oz", STANLEY) == (False, True)
    assert emparejar("Tapa Repuesto Stanley Quencher", STANLEY) == (False, True)


def test_compatible_es_accesorio():
    assert emparejar("Pajitas Compatibles Stanley Quencher x6", STANLEY) == (False, True)
