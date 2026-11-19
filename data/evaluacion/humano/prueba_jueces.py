"""Prueba de los dos jueces LLM con casos difíciles (reemplaza, como medida de los jueces, a la ronda 1).

La ronda 1 (planilla_*.csv) no medía a los jueces: en equivalencia eran los desacuerdos con el
criterio viejo, casi todos el mismo producto de los dos lados, y en dolor casi todos elogios; la
regla tonta "dolor no, equivalencia sí" acertaba más que el juez. Esta prueba se arma así
(escrito antes de que nadie la conteste):

    equivalencia  10 al azar de los "sí" del juez (¿cuando dice que compite, compite?) y 10 de los
                  "no" del juez entre publicaciones que comparten con lo propuesto al menos tantas
                  palabras como la mediana de los "no" (¿se le escapan competidores parecidos?).
                  Es el error que importa: si no cuenta un competidor, C4 deja viva una idea que ya
                  se vende. Datos: las propuestas de dev y sus búsquedas capturadas.
    dolor         10 al azar de los que el juez marcó con el problema sin resolver (¿cuando dice que
                  sí, es?) y 10 de los que no, pero solo entre gente que se queja de algo (su
                  tarjeta tiene dolor o miedo): el tono no regala la respuesta. Datos: la muestra que
                  midió C1 en la evaluación del dolor (data/evaluacion/dolor_de_la_propuesta/).

Nada de la ronda 1 se repite. Regla, por tipo: el juez sirve si acierta más que la mejor regla
tonta (responder siempre "sí" o siempre "no"); se informa también con intervalos de Wilson.

    python data/evaluacion/humano/prueba_jueces.py          -> prueba_jueces.csv y clave_prueba_jueces.json
    python data/evaluacion/humano/prueba_jueces.py evaluar  -> prueba_jueces_resultado.json
"""
import csv
import json
import random
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ))
from harness import dolor as D  # noqa: E402
from harness.voces import productos  # noqa: E402

POR_LADO = 10
SEMILLA = 11
SI = {"si", "sí", "s"}
PREGUNTA = {
    "dolor": ("¿Esta persona dice que hoy tiene ESTE problema y que no lo resolvió? Sí: lo cuenta y sigue sin "
              "solución. No: se queja de otra cosa, o dice que el producto se lo resolvió, o no se puede saber."),
    "equivalencia": ("Si B estuviera a la venta al lado de A, ¿quien buscaba A podría comprar B en su lugar y quedar "
                     "conforme? No: si es un accesorio, un repuesto, o algo que comparte palabras pero no hace lo mismo."),
}


def palabras(s: str) -> set:
    return set(re.findall(r"[a-záéíóúñ]{4,}", s.lower()))


def armar():
    az = random.Random(SEMILLA)
    ya = {(r["a"], r["b"]) for r in csv.DictReader(open(AQUI / "planilla_dario.csv", encoding="utf-8"))}
    items = []
    # Equivalencia: pares propuesta-publicación que el juez juzgó en dev
    from harness.correr import busquedas_capturadas
    capturas = busquedas_capturadas()
    juicios = json.loads((RAIZ / "data/serendipia/equivalencias.json").read_text(encoding="utf-8"))
    propuestas_dev = {o["busqueda_ml"] for o in json.loads((RAIZ / "data/serendipia/divergente_escala_dev_api.json").read_text(encoding="utf-8"))["oportunidades"]}
    si_, no_ = [], []
    for k, iguales in juicios.items():
        busqueda, _, propuesta = k.partition(" || ")
        if busqueda not in propuestas_dev:
            continue
        for p in (capturas.get(busqueda) or {}).get("publicaciones", []):
            if p.get("titulo") and (propuesta, p["titulo"]) not in ya:
                (si_ if p["titulo"] in iguales else no_).append((propuesta, p["titulo"]))
    solap = lambda par: len(palabras(par[0]) & palabras(par[1]))
    mediana = sorted(map(solap, no_))[len(no_) // 2]
    no_parecidos = [par for par in no_ if solap(par) >= max(1, mediana)]
    for etiqueta, lista in ((True, si_), (False, no_parecidos)):
        for a, b in az.sample(sorted(set(lista)), POR_LADO):
            items.append({"tipo": "equivalencia", "a": a, "b": b, "juez": etiqueta})
    # Dolor: la muestra que midió C1 (se rehace con la misma semilla que harness/dolor.py)
    tarjetas = {t["id"]: t for t in json.loads((RAIZ / "data/serendipia/personas_escala_dev_api.json").read_text(encoding="utf-8"))["tarjetas"]}
    todos = productos()
    pos, neg = [], []
    for f in sorted((RAIZ / "data/evaluacion/dolor_de_la_propuesta").glob("dolor_*.json")):
        props = {o["id"]: o for o in json.loads((RAIZ / "data/evaluacion/versiones_escala_dev" / f.name.removeprefix("dolor_")).read_text(encoding="utf-8"))["oportunidades"]}
        for m in json.loads(f.read_text(encoding="utf-8"))["medidas"]:
            citados = {tarjetas[i]["producto"] for i in props[m["id"]]["personas"] if i in tarjetas}
            de_ellos = [t for t in tarjetas.values() if t["producto"] in citados]
            grupo = de_ellos if len(de_ellos) <= D.PERSONAS_MEDIDAS else random.Random(f"{D.SEMILLA}{m['id']}").sample(de_ellos, D.PERSONAS_MEDIDAS)
            if m["medicion"]["propuesta"]["medidas"] != len(grupo):
                continue
            desatendidos = set(D.desatendidos(m["medicion"]["propuesta"]))
            problema = f"{m['dolor']['trabajo']} / {m['dolor']['obstaculo']}"
            for t in grupo:
                texto = D.texto_original(t, todos)
                if len(texto) < 40 or (problema, texto) in ya:
                    continue
                if t["id"] in desatendidos:
                    pos.append((problema, texto))
                elif t["dolor"] or t["teme"]:
                    neg.append((problema, texto))
    for etiqueta, lista in ((True, pos), (False, neg)):
        for a, b in az.sample(sorted(set(lista)), POR_LADO):
            items.append({"tipo": "dolor", "a": a, "b": b, "juez": etiqueta})
    az.shuffle(items)
    clave = []
    with open(AQUI / "prueba_jueces.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "tipo", "pregunta", "a", "b", "respuesta"])
        w.writeheader()
        for n, it in enumerate(items):
            w.writerow({"id": f"P{n:03d}", "tipo": it["tipo"], "pregunta": PREGUNTA[it["tipo"]], "a": it["a"], "b": it["b"], "respuesta": ""})
            clave.append({"id": f"P{n:03d}", "juez": it["juez"]})
    (AQUI / "clave_prueba_jueces.json").write_text(json.dumps(clave, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} filas; disponibles: {len(si_)} sí y {len(no_parecidos)} no parecidos de equivalencia, "
          f"{len(pos)} sí y {len(neg)} no con queja de dolor")


def wilson(k: int, n: int) -> list:
    from scipy.stats import binomtest
    if not n:
        return [None, None]
    ic = binomtest(k, n).proportion_ci(0.95, method="wilson")
    return [round(ic.low, 3), round(ic.high, 3)]


def evaluar():
    clave = {k["id"]: k["juez"] for k in json.loads((AQUI / "clave_prueba_jueces.json").read_text(encoding="utf-8"))}
    filas = [r for r in csv.DictReader(open(AQUI / "prueba_jueces.csv", encoding="utf-8")) if r["respuesta"].strip()]
    salida = {}
    for t in ("dolor", "equivalencia"):
        rs = [(clave[r["id"]], r["respuesta"].strip().lower() in SI) for r in filas if r["tipo"] == t]
        n = len(rs)
        if not n:
            continue
        acierta = sum(j == h for j, h in rs)
        humanos_si = sum(h for _, h in rs)
        si_juez = [(j, h) for j, h in rs if j]
        no_juez = [(j, h) for j, h in rs if not j]
        salida[t] = {"filas": n, "juez_acierta": acierta, "juez_acierta_ic95": wilson(acierta, n),
                     "regla_tonta_acierta": max(humanos_si, n - humanos_si),
                     "cuando_el_juez_dice_si_es_si": [sum(h for _, h in si_juez), len(si_juez)],
                     "cuando_el_juez_dice_no_es_no": [sum(not h for _, h in no_juez), len(no_juez)],
                     "el_juez_supera_a_la_regla_tonta": acierta > max(humanos_si, n - humanos_si)}
    (AQUI / "prueba_jueces_resultado.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    evaluar() if sys.argv[1:] == ["evaluar"] else armar()
