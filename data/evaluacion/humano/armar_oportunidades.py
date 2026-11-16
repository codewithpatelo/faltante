"""Planilla a ciegas de calidad: todas las oportunidades no descartadas de dev y test, del LLM y de
los baselines, mezcladas y sin decir de qué método salió cada una.

    python data/evaluacion/humano/armar_oportunidades.py
        -> oportunidades_<integrante>.csv (mismo contenido, otro orden) y clave_oportunidades.json

Tres preguntas por fila (si / no):
    concreta  ¿Es un producto concreto que se le puede pedir a un proveedor?
    obvia     ¿Se le ocurriría a cualquiera que vende en esa categoría?
    la_cotizaria  Si fueras importador, ¿pedirías una cotización para probarla?
Después: python data/evaluacion/humano/evaluar_oportunidades.py
"""
import csv
import json
import random
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
INTEGRANTES = ["dario", "nilo", "victoria", "patricio"]
SEMILLA = 7

items, vistos = [], set()
for particion in ("escala_dev_api", "escala_test_api"):
    for r in json.loads((RAIZ / f"data/serendipia/embudo_{particion}.json").read_text(encoding="utf-8")):
        clave = (r["metodo"], r["que_traer"])
        if r["estado"] == "descartada" or clave in vistos:
            continue
        vistos.add(clave)
        items.append({"que_traer": r["que_traer"], "busqueda_de_origen": " / ".join(r["anclas"])[:160],
                      "metodo": r["metodo"], "particion": particion})
random.Random(SEMILLA).shuffle(items)
for i, it in enumerate(items):
    it["id"] = f"Q{i:03d}"
(AQUI / "clave_oportunidades.json").write_text(json.dumps([{k: it[k] for k in ("id", "metodo", "particion")} for it in items],
                                                           ensure_ascii=False, indent=1), encoding="utf-8")
for quien in INTEGRANTES:
    orden = items[:]
    random.Random(f"{SEMILLA}{quien}").shuffle(orden)
    with open(AQUI / f"oportunidades_{quien}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "que_traer", "busqueda_de_origen", "concreta", "obvia", "la_cotizaria"])
        w.writeheader()
        for it in orden:
            w.writerow({"id": it["id"], "que_traer": it["que_traer"], "busqueda_de_origen": it["busqueda_de_origen"],
                        "concreta": "", "obvia": "", "la_cotizaria": ""})
print(f"{len(items)} oportunidades")
