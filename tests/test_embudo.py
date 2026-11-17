"""Lo que tiene que cumplir el programa, etapa por etapa."""

import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from harness import chequeos as c
from harness import dolor as D
from harness import umbrales as U
from harness.costo_puesto import EMBALAJE, LOGISTICA_M3, TIPO_CAMBIO, costo_puesto_usd, ingreso_neto_ars
from harness.divergente import al_formato_del_embudo, errores_de_propuesta, proponer
from harness.modelo import costo
from harness.personas import errores_de_tarjeta, mapa_de_empatia, tarjetas_de_una_tanda
from harness.embudo import Propuesta, recorrer
from harness.voces import RAIZ, textos_con_id

TEXTOS = {"o1": "Muy bueno pero no trae el repuesto", "o2": "Excelente", "p1": "Venden los discos de repuesto? || No los tenemos",
          "p2": "Donde consigo repuesto del disco?", "p3": "Hacen envíos?"}
AFILADOR = {"id": "PX", "titulo": "Afilador", "vendidos": 1000, "precio": 50000, "busqueda": "afilador",
            "opiniones": [TEXTOS["o1"], TEXTOS["o2"]],
            "preguntas": [["Venden los discos de repuesto?", "No los tenemos"], ["Donde consigo repuesto del disco?", ""]]}


# --- Guardrail ---------------------------------------------------------------------------

def test_guardrail_rechaza_citas_inventadas_o_de_un_solo_texto():
    ok = {"citas": [{"texto": "p1", "fragmento": "discos de repuesto"}, {"texto": "o1", "fragmento": "no trae el repuesto"}]}
    assert c.errores_de_citas(ok, TEXTOS) == []
    inventada = {"citas": [{"texto": "p1", "fragmento": "esto no está"}, {"texto": "p9", "fragmento": "nada"}]}
    errores = c.errores_de_citas(inventada, TEXTOS)
    assert any("no está" in e for e in errores) and any("no existe" in e for e in errores)
    un_solo_texto = {"citas": [{"texto": "p1", "fragmento": "discos"}, {"texto": "p1", "fragmento": "repuesto"}]}
    assert any("2 textos" in e for e in c.errores_de_citas(un_solo_texto, TEXTOS))


# --- C1 y C2 -----------------------------------------------------------------------------

def test_c1_pasa_solo_si_los_desatendidos_son_mas_que_en_el_control_y_cruzan_los_productos_que_cita():
    tarjetas = {f"P{k}.o{i}": {"producto": f"P{k}"} for k in (1, 2, 3) for i in range(40)}
    def medida(id_, productos, desat_por_producto, en_control):
        tienen = [f"{q}.o{i}" for q in productos for i in range(desat_por_producto)]
        return {"dolor": {"id": id_}, "productos": productos,
                "medicion": {"propuesta": {"medidas": 80, "tienen": tienen, "resuelto": []},
                             "control": {"medidas": 80, "tienen": [f"P3.o{i}" for i in range(en_control)], "resuelto": []}}}
    v = D.decidir([medida("real", ["P1", "P2"], 10, 2), medida("ruido", ["P1", "P2"], 2, 4),
                   medida("de_uno", ["P1", "P2"], 0, 0) | {"medicion": {"propuesta": {"medidas": 80, "tienen": [f"P1.o{i}" for i in range(20)], "resuelto": []},
                                                                       "control": {"medidas": 80, "tienen": [], "resuelto": []}}}], tarjetas)
    assert v["real"]["pasa"] and not v["ruido"]["pasa"]
    assert v["de_uno"]["significativo"] and not v["de_uno"]["pasa"]          # un solo producto: es su defecto
    p = _disco([])
    assert not c.c1_dolor(p).pasa                                             # sin medir no pasa
    p.dolor = v["real"]
    assert c.c1_dolor(p).pasa


# --- C4 ----------------------------------------------------------------------------------

def test_equivalente_es_lo_que_dice_el_juez_y_sin_juicio_c4_no_decide():
    publicaciones = [{"titulo": "Disco Rodante", "vendidos": 100, "precio": 1}, {"titulo": "Afilador Con Discos", "vendidos": 5000, "precio": 1}]
    p = _disco(publicaciones)
    assert [x["titulo"] for x in c.equivalentes(p)] == ["Disco Rodante"]      # el afilador comparte palabras, no es un disco
    p.equivalentes_juzgados = None
    assert "falta juzgar" in c.c4_hueco(p).motivo


def _disco(captura):
    oportunidad = {"id": "O1", "que_traer": "disco", "busqueda_ml": "disco"}
    señal = {"id": "S1", "producto": "PX", "descripcion": "piden discos",
             "citas": [{"texto": "p1", "fragmento": "discos de repuesto"}, {"texto": "o1", "fragmento": "no trae el repuesto"}]}
    origen = {"publicaciones": [{"titulo": f"Afilador {i}", "vendidos": v, "precio": 50000}
                                for i, v in enumerate([1000, 500, 500, 100, 100, 100, 50, 25, 100, 500])]}
    juez = [x["titulo"] for x in captura if x["titulo"].startswith("Disco")]    # lo que diría harness/equivalencias.py
    return Propuesta("llm", [AFILADOR], oportunidad, [señal], captura={"publicaciones": captura},
                     titulos_ancla={"disco rodante ancla"}, capturas_de_origen=[origen], equivalentes_juzgados=juez)


def test_c4_saca_repetidos_y_anclas_y_el_precio_es_el_de_lo_que_se_vendio():
    p = _disco([{"titulo": "Disco Rodante", "vendidos": 100, "precio": 10000},
                {"titulo": "Disco Rodante", "vendidos": 100, "precio": 10000},      # repetido
                {"titulo": "Disco Rodante Pro", "vendidos": 0, "precio": 900000},   # no vendió: no fija precio
                {"titulo": "Disco Rodante Ancla", "vendidos": 5000, "precio": 1}])  # es un ancla
    r = c.c4_hueco(p)
    assert r.pasa and r.datos["equivalentes"] == 2 and r.datos["venden"] == 1
    assert c.precio_de_mercado(p) == 10000


def test_c4_descarta_si_ya_lo_venden_varios():
    p = _disco([{"titulo": f"Disco {i}", "vendidos": 500, "precio": 10000} for i in range(3)])
    assert not c.c4_hueco(p).pasa


# --- C5: lo que la gente deja pasar ----------------------------------------------------

def test_c5_descarta_si_la_gente_tuvo_la_alternativa_y_la_dejo_pasar():
    ofrecidas = [{"titulo": f"Disco {i}", "vendidos": v, "precio": 10000, "internacional": 0} for i, v in enumerate([0, 0, 5, 25, 0])]
    assert not c.c5_la_eligen(_disco(ofrecidas)).pasa      # venden mucho menos que los afiladores de la misma búsqueda
    elegidas = [{"titulo": f"Disco {i}", "vendidos": v, "precio": 10000, "internacional": 0} for i, v in enumerate([500, 100, 1000])]
    assert c.c5_la_eligen(_disco(elegidas)).pasa
    caras = ofrecidas[:4] + [{"titulo": "Disco Oro", "vendidos": 0, "precio": 10 ** 7, "internacional": 0}]
    assert c.c5_la_eligen(_disco(caras)).datos["comparables"] == 4     # el precio atípico no cuenta como alternativa


def test_c5_no_cuenta_lo_importado_como_alternativa():
    importadas = [{"titulo": f"Disco {i}", "vendidos": 0, "precio": 10000, "internacional": 1} for i in range(5)]
    assert c.c5_la_eligen(_disco(importadas)).pasa          # esperar semanas es otra explicación de que no se elijan


# --- C6 y costo puesto -------------------------------------------------------------------

def test_el_fob_maximo_deja_justo_el_margen_minimo():
    fob = {"fob": [2.0, 3.3, 7.0], "die": [0.18, 0.35], "volumen_m3": 0.00015}
    m = c.margen(fob, 17416)
    costo_ars = costo_puesto_usd(m["fob_maximo_usd"], 0.18, 0.00015, m["lote"])["total"] * TIPO_CAMBIO
    assert abs((ingreso_neto_ars(17416, m["envio_ars"]) - costo_ars) / 17416 - U.MIN_MARGEN_NETO) < 0.002


def test_la_logistica_cobra_al_menos_1_m3_por_embarque():
    lleno = costo_puesto_usd(5.0, 0.18, 0.001)
    chico = costo_puesto_usd(5.0, 0.18, 0.001, unidades_lote=100)  # 0,115 m3 -> se cobra 1 m3
    assert abs(lleno["logistica"] - LOGISTICA_M3 * 0.001 * EMBALAJE) < 0.01
    assert abs(chico["logistica"] - LOGISTICA_M3 / 100) < 0.01
    assert chico["total"] > lleno["total"]


# --- La divergencia (personas, segmentos, propuestas) ---------------------------------------

class LLMQueCorrige:
    """Paso A: primero inventa una cita; cuando el guardrail se la devuelve, la corrige."""
    def __init__(self, fragmentos=("inventado", "no trae el repuesto")):
        self.llamadas, self.fragmentos, self.messages = 0, fragmentos, self

    def create(self, **kw):
        frag = self.fragmentos[min(self.llamadas, len(self.fragmentos) - 1)]
        self.llamadas += 1
        d = {"personas": [{"texto": "o1", "dolor": "no consigue repuesto", "fragmento": frag},
                          {"texto": "p1", "teme": "quedarse sin discos", "fragmento": "discos de repuesto"}]}
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(d))], usage=SimpleNamespace(input_tokens=1000, output_tokens=200))


def test_paso_a_el_llm_recibe_los_errores_del_guardrail_y_corrige():
    llm, traza = LLMQueCorrige(), []
    tarjetas = tarjetas_de_una_tanda(llm, AFILADOR, textos_con_id(AFILADOR), traza)
    assert llm.llamadas == 2 and traza[0]["errores"] and not traza[1]["errores"]
    assert {t["id"] for t in tarjetas} == {"PX.o1", "PX.p1"} and tarjetas[0]["eligio"] and not tarjetas[1]["eligio"]


def test_paso_a_si_el_llm_insiste_con_una_cita_falsa_esa_persona_no_se_anota():
    llm, traza = LLMQueCorrige(fragmentos=("inventado",)), []
    tarjetas = tarjetas_de_una_tanda(llm, AFILADOR, textos_con_id(AFILADOR), traza)
    assert llm.llamadas == 2 and [t["id"] for t in tarjetas] == ["PX.p1"]
    assert errores_de_tarjeta({"texto": "o2", "fragmento": "Excelente"}, TEXTOS)   # no anota nada de la persona


def persona(pid, texto, **campos):
    vacios = dict.fromkeys(("situacion", "quiere_lograr", "dolor", "ganancia", "teme", "compara_con"), "")
    return {**vacios, **campos, "id": f"{pid}.{texto}", "producto": pid, "texto": texto, "fragmento": TEXTOS[texto],
            "eligio": texto.startswith("o")}


MIEMBROS = {t["id"]: t for t in [persona("PX", "o1", dolor="sin repuesto"), persona("PX", "p1", teme="sin discos"),
                                  persona("PY", "o1", situacion="taller chico"), persona("PY", "p2")]}


def test_paso_b_exige_dos_personas_del_segmento_en_cada_uno_de_dos_productos():
    ok = {"personas": ["PX.o1", "PX.p1", "PY.o1", "PY.p2"], "alivia": "sin repuesto", "busqueda_ml": "x"}
    assert errores_de_propuesta(ok, MIEMBROS) == []
    assert any("2 productos" in e for e in errores_de_propuesta({**ok, "personas": ["PX.o1", "PX.p1", "PY.o1"]}, MIEMBROS))
    assert any("no es del segmento" in e for e in errores_de_propuesta({**ok, "personas": ok["personas"] + ["PZ.o9"]}, MIEMBROS))


def test_cada_propuesta_deja_una_señal_por_producto_con_las_citas_de_su_gente():
    o = {"id": "G1.O1", "que_traer": "x", "alivia": "sin repuesto", "personas": ["PX.o1", "PX.p1", "PY.o1", "PY.p2"],
         "busqueda_ml": "x"}
    salida = al_formato_del_embudo([o], MIEMBROS, "inexistente")
    assert salida["oportunidades"][0]["señales"] == ["PX.G1O1", "PY.G1O1"]
    señal_px = salida["señales"]["PX"][0]
    assert c.errores_de_citas(señal_px, TEXTOS) == []   # 2 personas de PX: pasa el guardrail del embudo


def test_el_mapa_de_empatia_cuenta_y_lee_primero_a_quien_tiene_dolor_o_miedo():
    todos = {"PX": AFILADOR, "PY": {**AFILADOR, "id": "PY", "busqueda": "afilador"}}
    m = mapa_de_empatia({"id": "G1", "nombre": "talleres", "quien": "q"}, list(MIEMBROS.values()), todos, {})
    assert m["personas"] == 4 and m["compraron"] == 2 and m["dudan"] == 2 and set(m["productos"]) == {"PX", "PY"}
    assert m["cuentan"]["dolor"] == 1 and m["voces"][0]["id"] == "PX.o1" and len(m["voces"]) == 4


def test_costo_del_llm_por_tokens():
    from harness.modelo import USD_POR_MILLON_DE_TOKENS as P
    r = costo([{"tokens": {"entrada": 1_000_000, "salida": 200_000}, "segundos": 2.0}])
    assert r["usd"] == round(P["entrada"] + 0.2 * P["salida"], 4) and r["segundos"] == 2.0


def test_costo_de_claude_usa_el_precio_de_su_modelo():
    from harness.modelo import PRECIOS
    traza = [{"tokens": {"entrada": 1_000_000, "salida": 200_000}, "segundos": 1.0}]
    p = PRECIOS["claude-opus-5-5"]
    assert costo(traza, "claude-opus-5-5")["usd"] == round(p["entrada"] + 0.2 * p["salida"], 4)
    assert costo(traza)["usd"] != costo(traza, "claude-opus-5-5")["usd"]   # sin modelo, sigue siendo DeepSeek


class _ClaudeFalso:
    """Imita al SDK de Anthropic: razonamiento antes del texto, y guarda con qué se lo llamó."""
    def __init__(self, stop_reason="end_turn", texto='{"ok": 1}'):
        self.llamadas, self.messages = [], self
        self._r = SimpleNamespace(
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=texto)],
            stop_reason=stop_reason, usage=SimpleNamespace(input_tokens=11, output_tokens=7))

    def stream(self, **pedido):
        self.llamadas.append(pedido)
        r = self._r
        class Flujo:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def get_final_message(self): return r
        return Flujo()


def test_claude_devuelve_la_misma_forma_que_deepseek_y_baja_el_esfuerzo_en_vez_de_apagar_el_razonamiento():
    from harness.modelo import Claude
    api = _ClaudeFalso()
    c = Claude("claude-haiku-5-5", api=api)
    r = c.messages.create(model="otro", max_tokens=100, messages=[{"role": "user", "content": "x"}], pensar=False)
    assert r.content[0].text == '{"ok": 1}' and r.usage.input_tokens == 11 and r.usage.output_tokens == 7
    assert api.llamadas[0]["model"] == "claude-haiku-5-5" and api.llamadas[0]["output_config"] == {"effort": "low"}
    assert "thinking" not in api.llamadas[0] and "temperature" not in api.llamadas[0]
    c.messages.create(model="x", max_tokens=100, messages=[], pensar=True)
    assert api.llamadas[1]["output_config"] == {"effort": "high"}


def test_con_reintento_usa_el_modelo_del_cliente_y_se_detiene_si_claude_corta_o_se_niega():
    from harness.modelo import Claude, RespuestaCortada, RespuestaRechazada, con_reintento
    traza = []
    api = _ClaudeFalso()
    assert con_reintento(Claude("claude-opus-5-5", api=api), "p", lambda s: [], traza, "paso") == {"ok": 1}
    assert api.llamadas[0]["model"] == "claude-opus-5-5" and traza[0]["tokens"] == {"entrada": 11, "salida": 7}
    with pytest.raises(RespuestaCortada):
        con_reintento(Claude("claude-opus-5-5", api=_ClaudeFalso("max_tokens")), "p", lambda s: [], [], "paso")
    with pytest.raises(RespuestaRechazada):
        con_reintento(Claude("claude-opus-5-5", api=_ClaudeFalso("refusal", "")), "p", lambda s: [], [], "paso")


def test_una_corrida_con_otro_modelo_no_pisa_los_archivos_de_deepseek():
    from harness.modelo import MODELO, sufijo
    assert sufijo(MODELO) == "" and sufijo("claude-opus-5-5") == "__claude-opus-5-5"


def test_el_archivo_dice_quien_juzgo_cuando_no_es_quien_propuso():
    from harness.modelo import MODELO, sufijo
    assert sufijo(MODELO, MODELO) == "" and sufijo(MODELO, None) == ""
    assert sufijo(MODELO, "claude-sonnet-5-5") == "__juez-claude-sonnet-5-5"
    assert sufijo("claude-haiku-5-5", "claude-sonnet-5-5") == "__claude-haiku-5-5__juez-claude-sonnet-5-5"


def test_costos_de_dos_modelos_se_suman_cada_uno_a_su_precio():
    from harness.modelo import MODELO, PRECIOS, costos
    t = [{"tokens": {"entrada": 1_000_000, "salida": 0}, "segundos": 1.0}]
    assert costos({MODELO: t}) == costo(t)       # con un solo modelo, igual que siempre
    r = costos({MODELO: t, "claude-sonnet-5-5": t})
    assert r["usd"] == round(PRECIOS[MODELO]["entrada"] + PRECIOS["claude-sonnet-5-5"]["entrada"], 4)
    assert set(r["por_modelo"]) == {MODELO, "claude-sonnet-5-5"} and r["segundos"] == 2.0


def test_quien_juzga_es_el_mismo_cliente_salvo_que_se_pida_otro_modelo(monkeypatch):
    pytest.importorskip("anthropic")
    from harness.modelo import clientes
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    monkeypatch.delenv("MODELO_LLM", raising=False)
    monkeypatch.delenv("MODELO_JUEZ", raising=False)
    propone, juzga = clientes()
    assert propone is juzga and propone.modelo == "deepseek-flash"
    monkeypatch.setenv("MODELO_JUEZ", "deepseek-flash")
    propone, juzga = clientes()
    assert propone is juzga                          # mismo modelo: un solo cliente, una sola traza
    monkeypatch.setenv("MODELO_JUEZ", "claude-sonnet-5-5")
    propone, juzga = clientes()
    assert propone.modelo == "deepseek-flash" and juzga.modelo == "claude-sonnet-5-5"


def test_el_embudo_lee_los_juicios_del_juez_que_dice_el_nombre_de_la_salida():
    from harness.equivalencias import archivo_de, juez_de
    assert juez_de("divergente_escala_dev_api.json") is None
    assert juez_de("data/serendipia/divergente_escala_dev_api__juez-claude-sonnet-5-5.json") == "claude-sonnet-5-5"
    assert juez_de("divergente_escala_dev_api__claude-haiku-5-5__juez-claude-sonnet-5-5.json") == "claude-sonnet-5-5"
    assert archivo_de(None).name == "equivalencias.json" and archivo_de("deepseek-flash").name == "equivalencias.json"
    assert archivo_de("claude-sonnet-5-5").name == "equivalencias__claude-sonnet-5-5.json"


def test_rejuzgar_mide_otra_vez_el_dolor_de_lo_guardado_sin_volver_a_proponer(monkeypatch):
    from harness import directo, divergente
    from harness.modelo import costos
    vistos = []
    def falso(cliente, dolores, tarjetas, todos, traza):
        vistos.append((cliente, len(dolores)))
        traza.append({"tokens": {"entrada": 10, "salida": 5}, "segundos": 1.0})
        return {d[0]["id"]: {"pasa": False} for d in dolores}
    monkeypatch.setattr(divergente.D, "medir_y_decidir", falso)
    juez = SimpleNamespace(modelo="claude-sonnet-5-5")
    guardado = json.loads((RAIZ / "data/serendipia/divergente_escala_dev_api.json").read_text())
    r = divergente.rejuzgar(guardado, "escala_dev", juez)
    assert r["quien"] == guardado["quien"] and r["juez"] == "claude-sonnet-5-5" and r["oportunidades"] == guardado["oportunidades"]
    assert set(r["dolor"]) == {"llm", "B1", "B2"} and len(r["dolor"]["llm"]) == len(guardado["oportunidades"])
    assert all(c is juez for c, _ in vistos) and r["costo"] == costos({"claude-sonnet-5-5": r["traza"]})
    assert r["costo_de_proponer"] == guardado["costo"]
    b3 = json.loads((RAIZ / "data/serendipia/directo_escala_dev_api.json").read_text())
    r3 = directo.rejuzgar(b3, "escala_dev", juez)
    assert len(r3["dolor"]) == len(b3["oportunidades"]) and r3["juez"] == "claude-sonnet-5-5"


def test_rejuzgar_no_toca_test_ni_se_hace_sin_juez(monkeypatch):
    from harness.modelo import juez_para_rejuzgar
    monkeypatch.setenv("MODELO_JUEZ", "claude-sonnet-5-5")
    with pytest.raises(SystemExit):
        juez_para_rejuzgar("escala_test")
    monkeypatch.delenv("MODELO_JUEZ")
    with pytest.raises(SystemExit):
        juez_para_rejuzgar("escala_dev")


def test_un_llm_juzga_las_filas_humanas_con_los_prompts_del_programa():
    import importlib.util
    import re
    espec = importlib.util.spec_from_file_location("juzgar_con_llm", RAIZ / "data/evaluacion/humano/juzgar_con_llm.py")
    J = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(J)

    class Falso:
        modelo, messages = "falso", None
        def __init__(self): self.messages, self.prompts = self, []
        def create(self, model, max_tokens, messages, pensar=True):
            p = messages[0]["content"]
            self.prompts.append(p)
            if "TEXTOS\n" in p:                          # dolor: todos lo tienen y el primero ya lo resolvió
                ids = re.findall(r"^\[(H\d+)\]", p, re.M)
                salida = {"tienen": ids, "resuelto": ids[:1]}
            else:                                         # equivalencia: solo la primera publicación
                salida = {"equivalentes": [0]}
            return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(salida))], stop_reason="end_turn",
                                   usage=SimpleNamespace(input_tokens=1, output_tokens=1))
    c = Falso()
    dolor = [{"id": "H001", "tipo": "dolor", "a": "gente con X / no puede Y", "b": "texto uno"},
             {"id": "H002", "tipo": "dolor", "a": "gente con X / no puede Y", "b": "texto dos"},
             {"id": "H003", "tipo": "dolor", "a": "otra gente / otro obstáculo", "b": "texto tres"}]
    r = J.juzgar_dolor(c, dolor, [])
    assert r == {"H001": False, "H002": True, "H003": False}      # sin resolver = sí; los de un mismo dolor van en una llamada
    assert len(c.prompts) == 2 and "Trabajo: gente con X" in c.prompts[0] or "Trabajo: gente con X" in c.prompts[1]
    eq = [{"id": "H010", "tipo": "equivalencia", "a": "Una pava eléctrica (para: calentar agua rápido)", "b": "Pava Eléctrica 1,7 L"},
          {"id": "H011", "tipo": "equivalencia", "a": "Una pava eléctrica (para: calentar agua rápido)", "b": "Filtro de repuesto"}]
    assert J.juzgar_equivalencia(c, eq, []) == {"H010": True, "H011": False}
    assert "PROPUESTA: Una pava eléctrica" in c.prompts[-1] and "PARA QUÉ: calentar agua rápido" in c.prompts[-1]


def test_claude_rechaza_un_modelo_sin_precio():
    from harness.modelo import Claude
    with pytest.raises(ValueError):
        Claude("claude-inventado", api=object())


# --- De punta a punta --------------------------------------------------------------------

def test_cada_propuesta_de_dev_termina_con_estado_y_motivo():
    subprocess.run([sys.executable, "-m", "harness.correr", "escala_dev_api"], cwd=RAIZ, check=True, capture_output=True)
    for r in json.loads((RAIZ / "data/serendipia/embudo_escala_dev_api.json").read_text()):
        assert r["estado"] in {"sobrevive", "condicional", "descartada"} and r["motivo"]
