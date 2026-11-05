import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from harness.costo_puesto import TIPO_CAMBIO, costo_puesto_usd, ingreso_neto_ars
from harness.serendipia import (es_equivalente, hueco_local, leer_voces_llm, margen, medir_señal, textos_numerados,
                                validar_señal)

RAIZ = Path(__file__).resolve().parent.parent
TEXTOS = {"o1": "Muy bueno pero no trae el repuesto", "o2": "Excelente", "p1": "Venden los discos de repuesto? || No los tenemos",
          "p2": "Donde consigo repuesto del disco?", "p3": "Hacen envíos?"}


def test_guardrail_rechaza_citas_inventadas_o_de_un_solo_texto():
    ok = {"palabras_clave": ["repuesto"], "citas": [{"texto": "p1", "fragmento": "discos de repuesto"}, {"texto": "o1", "fragmento": "no trae el repuesto"}]}
    assert validar_señal(ok, TEXTOS) == []
    inventada = {"palabras_clave": ["x"], "citas": [{"texto": "p1", "fragmento": "esto no está"}, {"texto": "p9", "fragmento": "nada"}]}
    errores = validar_señal(inventada, TEXTOS)
    assert any("no está" in e for e in errores) and any("no existe" in e for e in errores)
    uno = {"palabras_clave": ["x"], "citas": [{"texto": "p1", "fragmento": "discos"}, {"texto": "p1", "fragmento": "repuesto"}]}
    assert any("2 textos" in e for e in validar_señal(uno, TEXTOS))


def test_medir_cuenta_en_todos_los_textos_y_marca_insatisfaccion():
    m = medir_señal({"palabras_clave": ["repuesto"]}, TEXTOS)
    assert m["menciones"] == 3 and m["insatisfechas"] == 3 and m["C1_verificada"] and m["C2_subatendida"]
    assert not medir_señal({"palabras_clave": ["excelente"]}, TEXTOS)["C1_verificada"]


def test_equivalencia_mira_el_comienzo_del_titulo():
    crit = {"empieza_con": ["disco"], "todos": [["rodante"]], "excluir": ["motosierra"]}
    assert es_equivalente("Disco Diamante Afilador Rodante", crit)
    assert not es_equivalente("Afilador Rodante Con Discos", crit)          # es el afilador, no el disco
    assert not es_equivalente("Disco Afilador Rodante Motosierra", crit)
    assert not es_equivalente("Estante Adhesivo Repuesto", {"no_empieza_con": ["estante"], "todos": [["adhesivo"]]})


def test_hueco_local_usa_precio_de_lo_que_vende_y_saca_duplicados_y_anclas():
    pubs = [{"titulo": "Disco Rodante", "vendidos": 100, "precio": 10000},
            {"titulo": "Disco Rodante", "vendidos": 100, "precio": 10000},      # duplicado
            {"titulo": "Disco Rodante Pro", "vendidos": 0, "precio": 900000},   # no vendió: no fija precio
            {"titulo": "Disco Rodante Ancla", "vendidos": 5000, "precio": 1}]
    h = hueco_local(pubs, {"empieza_con": ["disco"]}, {"disco rodante ancla"})
    assert h["equivalentes"] == 2 and h["venden"] == 1 and h["C4_hueco"]
    assert h["precio_mediano_equivalentes_que_vendieron"] == 10000


def test_fob_maximo_deja_el_margen_minimo():
    fob = {"fob": [2.0, 3.3, 7.0], "die": [0.18, 0.35], "volumen_m3": 0.00015}
    r = margen(fob, 17416)
    from harness.serendipia import LOTE_MAX
    costo = costo_puesto_usd(r["fob_maximo_usd"], 0.18, 0.00015, min(LOTE_MAX, r["lote"]))["total"] * TIPO_CAMBIO
    assert abs(ingreso_neto_ars(17416, r["envio_ars"]) / costo - 1.30) < 0.01
    assert r["C5_condicional"] == (not r["C5_margen"] and r["escenarios"]["optimista"]["margen_pct"] >= 30)


class ClienteFalso:
    """Primero inventa una cita; cuando el validador se la devuelve, la corrige."""
    def __init__(self):
        self.llamadas = 0

    def _r(self, d):
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(d))], usage=SimpleNamespace(input_tokens=1000, output_tokens=200))

    @property
    def messages(self):
        return self

    def create(self, **kw):
        self.llamadas += 1
        frag = "inventado" if self.llamadas == 1 else "no trae el repuesto"
        return self._r({"señales": [{"id": "S1", "palabras_clave": ["repuesto"],
                                     "citas": [{"texto": "p1", "fragmento": "discos de repuesto"}, {"texto": "o1", "fragmento": frag}]}],
                        "oportunidades": []})


def test_paso_divergente_api_reintenta_con_los_errores_del_validador():
    prod = {"id": "PX", "titulo": "Afilador", "vendidos": 1000, "precio": 50000, "busqueda": "afilador",
            "opiniones": [TEXTOS["o1"], TEXTOS["o2"]], "preguntas": [["Venden los discos de repuesto?", "No los tenemos"]]}
    cliente, traza = ClienteFalso(), []
    salida = leer_voces_llm(cliente, prod, traza)
    assert cliente.llamadas == 2 and traza[0]["errores"] and not traza[1]["errores"]
    assert validar_señal(salida["señales"][0], textos_numerados(prod)) == []


def test_embudo_dev_corre_y_cada_oportunidad_tiene_destino():
    subprocess.run([sys.executable, "scripts/serendipia_run.py", "dev"], cwd=RAIZ, check=True, capture_output=True)
    res = json.loads((RAIZ / "data/serendipia/embudo_dev.json").read_text())
    for lista in res.values():
        for r in lista:
            assert r.get("sobrevive") or r.get("condicional") or r["muere_en"] in {"guardrail", "C1", "C2", "C3", "C4", "C5"}
