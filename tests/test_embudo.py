"""Lo que tiene que cumplir el programa, etapa por etapa."""

import json
import subprocess
import sys
from types import SimpleNamespace

from harness import chequeos as c
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
    ok = {"palabras_clave": ["repuesto"], "citas": [{"texto": "p1", "fragmento": "discos de repuesto"}, {"texto": "o1", "fragmento": "no trae el repuesto"}]}
    assert c.errores_de_citas(ok, TEXTOS) == []
    inventada = {"palabras_clave": ["x"], "citas": [{"texto": "p1", "fragmento": "esto no está"}, {"texto": "p9", "fragmento": "nada"}]}
    errores = c.errores_de_citas(inventada, TEXTOS)
    assert any("no está" in e for e in errores) and any("no existe" in e for e in errores)
    un_solo_texto = {"palabras_clave": ["x"], "citas": [{"texto": "p1", "fragmento": "discos"}, {"texto": "p1", "fragmento": "repuesto"}]}
    assert any("2 textos" in e for e in c.errores_de_citas(un_solo_texto, TEXTOS))


# --- C1 y C2 -----------------------------------------------------------------------------

def test_la_señal_se_cuenta_en_todos_los_textos_y_se_marca_la_insatisfaccion():
    m = c.medir({"palabras_clave": ["repuesto"]}, TEXTOS)
    assert m["menciones"] == 3 and m["insatisfechas"] == 3 and c.es_verificada(m) and c.es_subatendida(m)
    assert not c.es_verificada(c.medir({"palabras_clave": ["excelente"]}, TEXTOS))


# --- C4 ----------------------------------------------------------------------------------

def test_equivalente_es_lo_que_el_titulo_dice_que_se_vende():
    criterio = {"empieza_con": ["disco"], "todos": [["rodante"]], "excluir": ["motosierra"]}
    assert c.es_equivalente("Disco Diamante Afilador Rodante", criterio)
    assert not c.es_equivalente("Afilador Rodante Con Discos", criterio)          # es el afilador, no el disco
    assert not c.es_equivalente("Disco Afilador Rodante Motosierra", criterio)
    assert not c.es_equivalente("Estante Adhesivo Repuesto", {"no_empieza_con": ["estante"], "todos": [["adhesivo"]]})


def _disco(captura):
    oportunidad = {"id": "O1", "que_traer": "disco", "busqueda_ml": "disco", "criterio_equivalencia": {"empieza_con": ["disco"]}}
    señal = {"id": "S1", "producto": "PX", "descripcion": "piden discos", "palabras_clave": ["repuesto"],
             "citas": [{"texto": "p1", "fragmento": "discos de repuesto"}, {"texto": "o1", "fragmento": "no trae el repuesto"}]}
    return Propuesta("llm", [AFILADOR], oportunidad, [señal], captura={"publicaciones": captura},
                     titulos_ancla={"disco rodante ancla"})


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
    ofrecidas = [{"titulo": f"Disco {i}", "vendidos": 25, "precio": 10000, "internacional": 0} for i in range(3)]
    assert not c.c5_la_eligen(_disco(ofrecidas)).pasa                        # 75 ventas contra +1000 del afilador


def test_c5_no_cuenta_lo_importado_como_alternativa():
    importadas = [{"titulo": f"Disco {i}", "vendidos": 0, "precio": 10000, "internacional": 1} for i in range(5)]
    assert c.c5_la_eligen(_disco(importadas)).pasa          # esperar semanas es otra explicación de que no se elijan


# --- C6 y costo puesto -------------------------------------------------------------------

def test_el_fob_maximo_deja_justo_el_margen_minimo():
    fob = {"fob": [2.0, 3.3, 7.0], "die": [0.18, 0.35], "volumen_m3": 0.00015}
    m = c.margen(fob, 17416)
    costo_ars = costo_puesto_usd(m["fob_maximo_usd"], 0.18, 0.00015, m["lote"])["total"] * TIPO_CAMBIO
    assert abs(ingreso_neto_ars(17416, m["envio_ars"]) / costo_ars - (1 + U.MIN_MARGEN_SOBRE_COSTO)) < 0.01


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


VIVOS = {"G1.D1": {"medicion": {"segmento": {"tienen": ["PX.o1", "PX.p1", "PY.o1", "PY.p2", "PY.o9"], "resuelto": ["PY.o9"]}}}}


def test_paso_b_resuelve_un_dolor_verificado_y_cita_a_quienes_lo_tienen_en_dos_productos():
    ok = {"dolor": "G1.D1", "personas": ["PX.o1", "PX.p1", "PY.o1", "PY.p2"], "palabras_clave": ["repuesto"], "busqueda_ml": "x"}
    assert errores_de_propuesta(ok, MIEMBROS, VIVOS) == []
    assert any("dolores verificados" in e for e in errores_de_propuesta({**ok, "dolor": "G1.D9"}, MIEMBROS, VIVOS))
    assert any("2 productos" in e for e in errores_de_propuesta({**ok, "personas": ["PX.o1", "PX.p1", "PY.o1"]}, MIEMBROS, VIVOS))
    assert any("sin resolver" in e for e in errores_de_propuesta({**ok, "personas": ok["personas"] + ["PY.o9"]}, MIEMBROS, VIVOS))


def test_paso_b_sin_dolores_verificados_no_propone_nada():
    class NoDeberiaLlamarse:
        messages = None
    assert proponer(NoDeberiaLlamarse(), {"segmento": "G1"}, MIEMBROS, {}, []) == []


def test_el_dolor_sobrevive_por_sus_desatendidos_de_varios_productos_y_mas_que_en_el_control():
    from harness.dolores import veredicto
    tarjetas = {f"P{p}.o{i}": {"producto": f"P{p}"} for p in "XY" for i in range(20)}
    tienen = [f"P{p}.o{i}" for p in "XY" for i in range(10)]          # 20 personas, 10 en cada producto
    seg = {"medidas": 60, "tienen": tienen, "resuelto": []}
    control = {"medidas": 60, "tienen": ["PZ.o1"]}
    assert veredicto(seg, control, tarjetas)["pasa"]
    # la mayoría conforme no lo mata: alcanzan 6 desatendidos en dos productos
    mayoria = {**seg, "resuelto": [i for i in tienen if int(i.split("o")[1]) >= 3]}
    assert veredicto(mayoria, control, tarjetas)["pasa"]
    casi_todos = {**seg, "resuelto": tienen[2:]}
    r = veredicto(casi_todos, control, tarjetas)
    assert not r["pasa"] and r["rama"] == "precio_o_acceso"
    un_producto = {**seg, "resuelto": [i for i in tienen if i.startswith("PY")]}
    assert "un solo producto" in veredicto(un_producto, control, tarjetas)["motivo"]
    assert "no es de este grupo" in veredicto(seg, {"medidas": 60, "tienen": tienen[:15]}, tarjetas)["motivo"]
    assert "lo tienen 2" in veredicto({**seg, "tienen": tienen[:2]}, control, tarjetas)["motivo"]


def test_cada_propuesta_deja_una_señal_por_producto_con_las_citas_de_su_gente():
    o = {"id": "G1.O1", "que_traer": "x", "alivia": "sin repuesto", "personas": ["PX.o1", "PX.p1", "PY.o1", "PY.p2"],
         "palabras_clave": ["repuesto"], "busqueda_ml": "x"}
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


# --- De punta a punta --------------------------------------------------------------------

def test_cada_propuesta_de_dev_termina_con_estado_y_motivo():
    subprocess.run([sys.executable, "-m", "harness.correr", "dev"], cwd=RAIZ, check=True, capture_output=True)
    for r in json.loads((RAIZ / "data/serendipia/embudo_dev.json").read_text()):
        assert r["estado"] in {"sobrevive", "condicional", "descartada"} and r["motivo"]
