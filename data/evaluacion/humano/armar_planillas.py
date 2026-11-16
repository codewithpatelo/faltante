"""Arma las planillas para el juicio humano a ciegas (una por integrante, mismo contenido, otro orden).

Calibra contra personas los dos jueces LLM del embudo, que hasta ahora se validaron con controles
y con un etiquetado de Claude, no de humanos:

    dolor         C1: ¿este texto muestra que la persona tiene el dolor descrito y no lo resolvió?
                  20 que el clasificador marcó como desatendidos y 20 que no (mismo grupo medido)
    equivalencia  C4 a C6: ¿un comprador de lo propuesto podría comprar esta publicación en su lugar?
                  los 40 desacuerdos de data/evaluacion/equivalencias/a_ciegas.json

Nadie ve qué dijo el modelo. Cada uno completa la columna "respuesta" con si / no y commitea su
archivo. Después: python data/evaluacion/humano/calibrar.py

    python data/evaluacion/humano/armar_planillas.py
"""
import csv
import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ))
from harness import dolor as D  # noqa: E402
from harness.voces import productos  # noqa: E402

INTEGRANTES = ["dario", "nilo", "victoria", "patricio"]
POR_CLASE = 20
SEMILLA = 7

tarjetas = {t["id"]: t for t in json.loads((RAIZ / "data/serendipia/personas_escala_dev_api.json").read_text(encoding="utf-8"))["tarjetas"]}
todos = productos()
azar = random.Random(SEMILLA)
items, clave = [], []

# Dolor: se rehace la muestra medida (misma semilla que harness/dolor.py) para tener los negativos.
positivos, negativos = [], []
for f in sorted((RAIZ / "data/evaluacion/dolor_de_la_propuesta").glob("dolor_*.json")):
    propuestas = {o["id"]: o for o in json.loads((RAIZ / "data/evaluacion/versiones_escala_dev" / f.name.removeprefix("dolor_")).read_text(encoding="utf-8"))["oportunidades"]}
    for m in json.loads(f.read_text(encoding="utf-8"))["medidas"]:
        citados = {tarjetas[i]["producto"] for i in propuestas[m["id"]]["personas"] if i in tarjetas}
        r = random.Random(f"{D.SEMILLA}{m['id']}")
        de_los_productos = [t for t in tarjetas.values() if t["producto"] in citados]
        grupo = de_los_productos if len(de_los_productos) <= D.PERSONAS_MEDIDAS else r.sample(de_los_productos, D.PERSONAS_MEDIDAS)
        if m["medicion"]["propuesta"]["medidas"] != len(grupo):
            continue                                     # no se pudo rehacer la misma muestra: se saltea
        desatendidos = set(D.desatendidos(m["medicion"]["propuesta"]))
        for t in grupo:
            texto = D.texto_original(t, todos)
            if len(texto) < 40:
                continue
            par = {"dolor": f"{m['dolor']['trabajo']} / {m['dolor']['obstaculo']}", "texto": texto}
            (positivos if t["id"] in desatendidos else negativos).append(par)
for etiqueta, lista in ((True, positivos), (False, negativos)):
    for par in azar.sample(lista, POR_CLASE):
        items.append({"tipo": "dolor", "pregunta": "¿El texto muestra que esta persona tiene este problema y no lo resolvió?",
                      "a": par["dolor"], "b": par["texto"]})
        clave.append({"modelo": etiqueta})

for d, k in zip(json.loads((RAIZ / "data/evaluacion/equivalencias/a_ciegas.json").read_text(encoding="utf-8")),
                json.loads((RAIZ / "data/evaluacion/equivalencias/clave.json").read_text(encoding="utf-8"))):
    items.append({"tipo": "equivalencia", "pregunta": "¿Un comprador de lo propuesto podría comprar esta publicación en su lugar?",
                  "a": f"{d['propuesta']} (para: {d['para_que']})", "b": d["publicacion"]})
    clave.append({"modelo": k["juez"], "criterio_viejo": k["viejo"], "claude": d["es_equivalente"]})

for i, (it, k) in enumerate(zip(items, clave)):
    it["id"], k["id"] = f"H{i:03d}", f"H{i:03d}"
(AQUI / "clave.json").write_text(json.dumps(clave, ensure_ascii=False, indent=1), encoding="utf-8")
for quien in INTEGRANTES:
    orden = items[:]
    random.Random(f"{SEMILLA}{quien}").shuffle(orden)
    with open(AQUI / f"planilla_{quien}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "tipo", "pregunta", "a", "b", "respuesta"])
        w.writeheader()
        for it in orden:
            w.writerow({**it, "respuesta": ""})
print(f"{len(items)} ítems por planilla ({len(positivos)} positivos y {len(negativos)} negativos de dolor disponibles)")
