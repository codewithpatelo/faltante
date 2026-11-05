"""El loop proponer → validar → reintentar, con un cliente falso (sin red ni API key)."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.divergente import costo, leer_busqueda  # noqa: E402

PUBS = [
    {"titulo": "Minipimer Atma 600w", "internacional": 0, "vendidos": 1000, "precio": 47000},
    {"titulo": "Licuadora De Inmersión Turelar 400w", "internacional": 1, "vendidos": 0, "precio": 90000},
]


def hip(fragmento):
    return {"id": "H1", "tipo": "marca", "necesidad": "x", "oportunidad": "x", "rivales": ["precio"],
            "evidencia": [{"busqueda": "mixer", "i": 0, "vota": "gana", "fragmento": fragmento},
                          {"busqueda": "mixer", "i": 1, "vota": "pierde", "fragmento": "Turelar"}]}


class Falso:
    """Devuelve las respuestas en orden y guarda lo que le mandaron."""
    def __init__(self, respuestas):
        self.respuestas, self.recibido = list(respuestas), []
        self.messages = self

    def create(self, **kw):
        self.recibido.append(kw["messages"])
        texto = json.dumps({"hipotesis": [self.respuestas.pop(0)]})
        return NS(content=[NS(text=texto)], usage=NS(input_tokens=1000, output_tokens=200))


def test_cita_inventada_se_corrige_en_el_reintento():
    cli = Falso([hip("220v 50Hz"), hip("Minipimer")])
    traza = []
    hs = leer_busqueda(cli, "mixer", PUBS, traza)
    assert len(hs) == 1 and hs[0]["evidencia"][0]["fragmento"] == "Minipimer"
    assert len(traza) == 2 and traza[0]["errores"] and not traza[1]["errores"]
    assert "El validador rechazó" in cli.recibido[1][-1]["content"]


def test_si_sigue_mal_se_descarta():
    traza = []
    hs = leer_busqueda(Falso([hip("inventado"), hip("inventado")]), "mixer", PUBS, traza)
    assert hs == [] and len(traza) == 2


def test_costo_por_tokens():
    c = costo([{"tokens": {"entrada": 1_000_000, "salida": 100_000}, "segundos": 1.0}])
    assert c["usd"] == 1.5


def test_juez_llm_devuelve_puntajes():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from juez_llm import juzgar

    class Cli:
        def __init__(self):
            self.messages = self

        def create(self, **kw):
            assert "Ítem a juzgar" in kw["messages"][0]["content"]
            return NS(content=[NS(text='{"sostenida_1a3": 3, "no_obvia_1a3": 2, "accionable_1a3": 1, "comentario": "ok"}')])

    cap = {"mixer": {"publicaciones": PUBS}}
    j = juzgar(Cli(), {"busqueda": "mixer", "texto": "algo"}, cap)
    assert (j["sostenida_1a3"], j["no_obvia_1a3"], j["accionable_1a3"]) == (3, 2, 1)
