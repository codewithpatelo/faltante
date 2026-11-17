"""Planilla a ciegas de calidad: las recomendaciones finales de cada método en dev y test,
mezcladas y sin decir de qué método salió cada una.

    python data/evaluacion/humano/armar_oportunidades.py
        -> oportunidades_<integrante>.csv (mismo contenido, otro orden) y clave_oportunidades.json

Qué entra (prerregistro, data/evaluacion/test/PRERREGISTRO.md):
    llm, B1, B2   las que el embudo no descartó
    B4            todo lo que recomienda el one-shot de punta a punta (su recomendación final);
                  si son más de 20 por partición, 20 sorteadas
B3 no entra: es una ablación de la generación y se mide con el embudo.

Es aditivo: si ya hay planillas, conserva los IDs y las respuestas, y suma las filas nuevas en
posiciones al azar.

Tres preguntas por fila (si / no):
    concreta  ¿Es un producto concreto que se le puede pedir a un proveedor?
    obvia     ¿Se le ocurriría a cualquiera que vende en esa categoría?
    la_cotizaria  Si fueras importador, ¿pedirías una cotización para probarla?
Después: python data/evaluacion/humano/evaluar_oportunidades.py
"""
import csv
import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ))
from harness.voces import productos  # noqa: E402
INTEGRANTES = ["dario", "nilo", "victoria", "patricio"]
SEMILLA = 7
MAX_B4_POR_PARTICION = 20
CAMPOS = ["id", "que_traer", "busqueda_de_origen", "concreta", "obvia", "la_cotizaria"]

deseados = []
for particion in ("escala_dev_api", "escala_test_api"):
    for r in json.loads((RAIZ / f"data/serendipia/embudo_{particion}.json").read_text(encoding="utf-8")):
        if r["metodo"] in ("llm", "B1", "B2") and r["estado"] != "descartada":
            deseados.append({"que_traer": r["que_traer"], "busqueda_de_origen": " / ".join(r["anclas"])[:160],
                             "metodo": r["metodo"], "particion": particion})
    de_una = RAIZ / f"data/serendipia/de_una_{particion}.json"
    if de_una.exists():
        todos = productos()
        b4 = json.loads(de_una.read_text(encoding="utf-8"))["oportunidades"]
        if len(b4) > MAX_B4_POR_PARTICION:
            b4 = random.Random(SEMILLA).sample(b4, MAX_B4_POR_PARTICION)
        deseados += [{"que_traer": o["que_traer"], "busqueda_de_origen": todos[o["producto"]]["titulo"][:160],
                      "metodo": "B4", "particion": particion} for o in b4]

# lo que ya estaba: IDs, textos y respuestas
clave_vieja = {k["id"]: k for k in json.loads((AQUI / "clave_oportunidades.json").read_text(encoding="utf-8"))} \
    if (AQUI / "clave_oportunidades.json").exists() else {}
planillas = {q: list(csv.DictReader(open(AQUI / f"oportunidades_{q}.csv", encoding="utf-8")))
             if (AQUI / f"oportunidades_{q}.csv").exists() else [] for q in INTEGRANTES}
texto_de = {r["id"]: r["que_traer"] for filas in planillas.values() for r in filas}
ya = {(clave_vieja[i]["metodo"], texto_de.get(i)) for i in clave_vieja}   # como antes: una idea repetida en dev y test va una vez

items, vistos = [], set(ya)
for it in deseados:
    k = (it["metodo"], it["que_traer"])
    if k not in vistos:
        vistos.add(k)
        items.append(it)
random.Random(SEMILLA).shuffle(items)
for n, it in enumerate(items, start=len(clave_vieja)):
    it["id"] = f"Q{n:03d}"
clave = list(clave_vieja.values()) + [{k: it[k] for k in ("id", "metodo", "particion")} for it in items]
(AQUI / "clave_oportunidades.json").write_text(json.dumps(clave, ensure_ascii=False, indent=1), encoding="utf-8")
for quien in INTEGRANTES:
    filas = planillas[quien]
    nuevas = [{"id": it["id"], "que_traer": it["que_traer"], "busqueda_de_origen": it["busqueda_de_origen"],
               "concreta": "", "obvia": "", "la_cotizaria": ""} for it in items]
    azar = random.Random(f"{SEMILLA}{quien}{len(clave_vieja)}")
    for fila in nuevas:
        filas.insert(azar.randint(0, len(filas)), fila)
    with open(AQUI / f"oportunidades_{quien}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
print(f"{len(clave)} oportunidades ({len(items)} nuevas)")
