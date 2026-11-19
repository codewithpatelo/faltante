"""Hace juzgar a un LLM las 63 oportunidades finales con las tres preguntas que contestaron las personas.

    MODELO_JUEZ=claude-sonnet-5-5 python data/evaluacion/humano/juzgar_oportunidades_con_llm.py
        -> oportunidades_llm.json (veredictos por modelo) y oportunidades_llm_resultado.json

Ve lo mismo que una persona (qué traer y la publicación de origen), sin saber de qué método salió.
Informa, por pregunta, el acuerdo con la mayoría humana (solo donde hay mayoría) contra la regla
tonta (responder siempre lo mismo), y la regla del prerregistro (programa contra B4, Fisher) con
los veredictos del modelo en las 63 filas.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ))
from harness.modelo import cliente_llm, costo, con_reintento, en_paralelo  # noqa: E402

SI = {"si", "sí", "s", "1", "true", "x"}
COLUMNAS = ("concreta", "obvia", "la_cotizaria")
ARCHIVO = AQUI / "oportunidades_llm.json"
PROMPT = """Sos un importador argentino que vende en Mercado Libre. Te proponen una idea de producto para traer.

IDEA: {que_traer}
(salió de mirar esta publicación: {origen})

Contestá tres preguntas, cada una con true o false:
- concreta: ¿es un producto concreto que se le puede pedir a un proveedor?
- obvia: ¿se le ocurriría a cualquiera que vende en esa categoría?
- la_cotizaria: si fueras importador, ¿pedirías una cotización para probarla?

Respondé SOLO con el JSON: {{"concreta": true|false, "obvia": true|false, "la_cotizaria": true|false}}"""


def filas() -> list[dict]:
    return list(csv.DictReader(open(AQUI / "oportunidades_dario.csv", encoding="utf-8")))   # mismo contenido en todas


def mayoria_humana() -> dict[str, dict]:
    votos: dict[str, dict] = {}
    for f in sorted(AQUI.glob("oportunidades_*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if all(r[c].strip() for c in COLUMNAS):
                for c in COLUMNAS:
                    votos.setdefault(r["id"], {}).setdefault(c, []).append(r[c].strip().lower() in SI)
    return {i: {c: (v.count(True) > v.count(False)) if v.count(True) != v.count(False) else None for c, v in cs.items()}
            for i, cs in votos.items()}


def juzgar_todas(cliente, traza: list) -> dict[str, dict]:
    def una(r):
        validar = lambda d: {} if all(isinstance(d.get(c), bool) for c in COLUMNAS) else {"formato": ["faltan true/false"]}
        d = con_reintento(cliente, PROMPT.format(que_traer=r["que_traer"], origen=r["busqueda_de_origen"]),
                          validar, traza, f"oportunidad {r['id']}")
        return r["id"], {c: d.get(c) for c in COLUMNAS}
    return dict(en_paralelo(una, filas()))


def comparar(juicios: dict, humanos: dict) -> dict:
    salida = {}
    for c in COLUMNAS:
        pares = [(juicios[i][c], h[c]) for i, h in humanos.items() if i in juicios and h.get(c) is not None and juicios[i][c] is not None]
        n, acierta = len(pares), sum(a == b for a, b in pares)
        humanos_si = sum(b for _, b in pares)
        salida[c] = {"filas_con_mayoria": n, "acierta": acierta, "regla_tonta": max(humanos_si, n - humanos_si),
                     "dice_si_y_es_si": [sum(a and b for a, b in pares), sum(a for a, _ in pares)]}
    return salida


def programa_contra_b4(juicios: dict) -> dict:
    from scipy.stats import fisher_exact
    clave = {k["id"]: k["metodo"] for k in json.loads((AQUI / "clave_oportunidades.json").read_text(encoding="utf-8"))}
    buena = lambda j: bool(j["concreta"] and j["obvia"] is False and j["la_cotizaria"])
    por = {m: [buena(j) for i, j in juicios.items() if clave.get(i) == m] for m in ("llm", "B4")}
    (bl, nl), (bb, nb) = (sum(por["llm"]), len(por["llm"])), (sum(por["B4"]), len(por["B4"]))
    return {"programa": [bl, nl], "B4": [bb, nb],
            "p_unilateral": round(fisher_exact([[bl, nl - bl], [bb, nb - bb]], alternative="greater").pvalue, 4) if nl and nb else None}


if __name__ == "__main__":
    cliente, traza = cliente_llm(variable="MODELO_JUEZ"), []
    todos = json.loads(ARCHIVO.read_text(encoding="utf-8")) if ARCHIVO.exists() else {}
    todos[cliente.modelo] = juzgar_todas(cliente, traza)
    ARCHIVO.write_text(json.dumps(todos, ensure_ascii=False, indent=1), encoding="utf-8")
    resultado = {m: {"contra_la_mayoria_humana": comparar(j, mayoria_humana()), "programa_contra_B4": programa_contra_b4(j)}
                 for m, j in todos.items()}
    (AQUI / "oportunidades_llm_resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(resultado[cliente.modelo], ensure_ascii=False, indent=1), f"\n{costo(traza, cliente.modelo)}")
