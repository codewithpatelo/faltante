"""Tests del harness. No usan red ni API key: el LLM se reemplaza por un guion."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pytest  # noqa: E402

from adapters import AdaptadorFixtures, AdaptadorMercadoLibre  # noqa: E402
from harness.agente import PoliticaReAct  # noqa: E402
from harness.motor import Motor, Rechazo  # noqa: E402
from harness.politicas import PoliticaFija, PoliticaHeuristica  # noqa: E402

PISTAS = json.loads((RAIZ / "data/pistas_sintetico.json").read_text(encoding="utf-8"))["pistas"]


def motor(adaptador=None, pistas=PISTAS):
    return Motor(adaptador=adaptador or AdaptadorFixtures(RAIZ / "data/fixtures_sintetico.json"), pistas=pistas)


def test_guardrail_confirmar_sin_evidencia_es_rechazado():
    m = motor()
    hid = m.proponer_hipotesis("P2", "kit cepillos laterales robot X200", "complemento", "test")
    with pytest.raises(Rechazo):
        m.dar_veredicto(hid, "confirmar", [], "sin probar nada")
    assert hid not in m.veredictos


def test_guardrail_no_acepta_evidencia_de_otra_hipotesis():
    m = motor()
    h1 = m.proponer_hipotesis("P2", "kit cepillos laterales robot X200", "complemento", "a")
    h2 = m.proponer_hipotesis("P3", "termo acero 1L premium", "precio", "b")
    ev = m.verificar("contar_oferta", h1)
    with pytest.raises(Rechazo):
        m.dar_veredicto(h2, "confirmar", [ev["id"]], "evidencia prestada")


def test_guardrail_no_acepta_evidencia_fallida():
    m = motor(adaptador=AdaptadorMercadoLibre(token=None))
    hid = m.proponer_hipotesis("P2", "algo", "ausencia", "x")
    ev = m.verificar("contar_oferta", hid)
    assert not ev["ok"] and ev["error"] == "sin_credenciales"
    with pytest.raises(Rechazo):
        m.dar_veredicto(hid, "confirmar", [ev["id"]], "con evidencia fallida")
    m.dar_veredicto(hid, "insuficiente", [ev["id"]], "no se pudo verificar")  # esto sí se acepta


def test_cache_evita_segunda_llamada_a_la_fuente():
    m = motor()
    h1 = m.proponer_hipotesis("P2", "kit cepillos laterales robot X200", "complemento", "a")
    h2 = m.proponer_hipotesis("P2", "kit cepillos laterales robot X200", "ausencia", "b")
    m.verificar("contar_oferta", h1)
    ev = m.verificar("contar_oferta", h2)
    assert ev["cache"] and m.llamadas_fuente == 1


def test_heuristica_usa_menos_skills_que_fija_con_igual_accuracy():
    mf, mh = motor(), motor()
    PoliticaFija().correr(mf)
    PoliticaHeuristica().correr(mh)
    df, dh = mf.decision_por_pista(), mh.decision_por_pista()
    assert {k: v["decision"] for k, v in df.items()} == {k: v["decision"] for k, v in dh.items()}
    assert mh.llamadas_fuente < mf.llamadas_fuente


# ---------- loop ReAct con un LLM de guion ----------

def _uso():
    return NS(input_tokens=100, output_tokens=20, cache_read_input_tokens=0, cache_creation_input_tokens=0)


def _tool(i, nombre, args):
    return NS(type="tool_use", id=f"t{i}", name=nombre, input=args)


class ClienteGuion:
    """Devuelve una respuesta prearmada por turno y guarda lo que recibió."""

    def __init__(self, turnos):
        self.turnos = list(turnos)
        self.recibido = []
        self.messages = self

    def create(self, **kw):
        self.recibido.append(kw["messages"][-1])
        return NS(content=self.turnos.pop(0), usage=_uso())


def test_react_rechaza_veredicto_sin_evidencia_y_se_recupera():
    pistas = [p for p in PISTAS if p["id"] == "P2"]
    m = motor(pistas=pistas)
    guion = [
        [_tool(1, "proponer_hipotesis", {"pista_id": "P2", "producto": "cepillos laterales robot X200",
                                         "tipo": "complemento", "razonamiento": "usado a precio de nuevo"})],
        [_tool(2, "dar_veredicto", {"hipotesis_id": "H1", "decision": "confirmar", "evidencias": [],
                                "justificacion": "obvio"})],                       # debe rebotar
        [_tool(3, "terminar", {})],                                                 # debe rebotar
        [_tool(4, "verificar", {"skill": "contar_oferta", "hipotesis_id": "H1"})],
        [_tool(5, "dar_veredicto", {"hipotesis_id": "H1", "decision": "confirmar", "evidencias": ["E1"],
                                "justificacion": "2 vendedores"})],
        [_tool(6, "terminar", {})],
    ]
    cli = ClienteGuion(guion)
    PoliticaReAct(cliente=cli).correr(m)

    errores = [r["content"][0]["is_error"] for r in cli.recibido[1:]]
    assert errores == [False, True, True, False, False]
    assert m.veredictos["H1"]["decision"] == "confirmar"
    assert m.decision_por_pista()["P2"]["decision"] == "confirmar"
    assert any(t["evento"] == "rechazo" for t in m.traza)
