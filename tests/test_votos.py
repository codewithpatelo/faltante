"""Etapa divergente: el guardrail de citas y el baseline de términos."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.votos import contraste_terminos, validar_hipotesis, vista  # noqa: E402

PUBS = [
    {"titulo": "Minipimer Atma 600w", "internacional": 0, "vendidos": 1000, "precio": 47000},
    {"titulo": "Licuadora De Inmersión Turelar 400w", "internacional": 1, "vendidos": 0, "precio": 90000},
    {"titulo": "Minipimer Oster 800w", "internacional": 0, "vendidos": 100, "precio": 111000},
    {"titulo": "Licuadora De Inmersión Turelar 1100w", "internacional": 1, "vendidos": 0, "precio": 200000},
]
FUENTE = {"mixer": PUBS}


def h(evidencia):
    return {"id": "H", "necesidad": "x", "tipo": "lenguaje", "oportunidad": "x", "rivales": ["precio"],
            "evidencia": evidencia}


def test_vista_separa_por_voto():
    v = vista(PUBS)
    assert [p["i"] for p in v["ganan"]] == [0, 2]
    assert [p["i"] for p in v["pierden"]] == [1, 3]


def test_baseline_encuentra_el_contraste():
    c = contraste_terminos(PUBS, k=1)
    assert c["ganan"][0][0] == "minipimer"
    assert c["pierden"][0][0] in {"turelar", "licuadora", "inmersion"}


def test_hipotesis_bien_citada_pasa():
    ok = h([{"busqueda": "mixer", "i": 0, "vota": "gana", "fragmento": "Minipimer"},
            {"busqueda": "mixer", "i": 1, "vota": "pierde", "fragmento": "Licuadora De Inmersión"}])
    assert validar_hipotesis(ok, FUENTE) == []


def test_fragmento_inventado_se_rechaza():
    mala = h([{"busqueda": "mixer", "i": 0, "vota": "gana", "fragmento": "220v 50Hz"},
              {"busqueda": "mixer", "i": 1, "vota": "pierde", "fragmento": "Turelar"}])
    assert any("no está en el título" in e for e in validar_hipotesis(mala, FUENTE))


def test_voto_mal_atribuido_se_rechaza():
    mala = h([{"busqueda": "mixer", "i": 1, "vota": "gana", "fragmento": "Turelar"},
              {"busqueda": "mixer", "i": 0, "vota": "pierde", "fragmento": "Atma"}])
    errores = validar_hipotesis(mala, FUENTE)
    assert any("no tiene ventas" in e for e in errores)
    assert any("tiene +1000 vendidos" in e for e in errores)


def test_sin_contraste_se_rechaza():
    mala = h([{"busqueda": "mixer", "i": 0, "vota": "gana", "fragmento": "Minipimer"}])
    assert any("al menos una publicación que gana y una que pierde" in e for e in validar_hipotesis(mala, FUENTE))


def test_cita_inexistente_se_rechaza():
    mala = h([{"busqueda": "mixer", "i": 9, "vota": "gana", "fragmento": "x"},
              {"busqueda": "otra", "i": 0, "vota": "pierde", "fragmento": "x"}])
    errores = validar_hipotesis(mala, FUENTE)
    assert any("no existe: 9" in e for e in errores) and any("búsqueda que no existe" in e for e in errores)
