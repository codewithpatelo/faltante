"""Calibra los jueces LLM contra el juicio humano a ciegas (planillas completas de cada integrante).

    python data/evaluacion/humano/calibrar.py  -> data/evaluacion/humano/calibracion.json

Para cada juez (dolor, equivalencia): acuerdo entre humanos (kappa de Fleiss), y contra la
mayoría humana: acuerdo, kappa de Cohen, precisión y exhaustividad del modelo. En equivalencias
también el criterio viejo (lo escribía quien proponía) y el etiquetado de Claude. Si hay
jueces_llm.json (juzgar_con_llm.py), también cada modelo que juzgó las mismas filas.
"""
import csv
import json
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SI = {"si", "sí", "s", "1", "true", "x"}


def kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


def fleiss(tablas: list[list[bool]]) -> float | None:
    """tablas: por ítem, la lista de respuestas de los jueces."""
    if not tablas or len(tablas[0]) < 2:
        return None
    k = len(tablas[0])
    p_i = [(sum(r) ** 2 + (k - sum(r)) ** 2 - k) / (k * (k - 1)) for r in tablas]
    p1 = sum(sum(r) for r in tablas) / (len(tablas) * k)
    pe = p1 ** 2 + (1 - p1) ** 2
    return round((sum(p_i) / len(p_i) - pe) / (1 - pe), 3) if pe < 1 else None


clave = {k["id"]: k for k in json.loads((AQUI / "clave.json").read_text(encoding="utf-8"))}
jueces_llm = json.loads((AQUI / "jueces_llm.json").read_text(encoding="utf-8")) if (AQUI / "jueces_llm.json").exists() else {}
for nombre, juicios in jueces_llm.items():         # otros modelos que juzgaron las mismas filas (juzgar_con_llm.py)
    for i, v in juicios.items():
        clave[i][nombre] = v
respuestas, tipo = {}, {}
for f in sorted(AQUI.glob("planilla_*.csv")):
    filas = list(csv.DictReader(open(f, encoding="utf-8")))
    if not all(r["respuesta"].strip() for r in filas):
        continue                                   # planilla incompleta: no cuenta
    respuestas[f.stem.removeprefix("planilla_")] = {r["id"]: r["respuesta"].strip().lower() in SI for r in filas}
    tipo |= {r["id"]: r["tipo"] for r in filas}
salida = {"jueces_humanos": sorted(respuestas)}
for t in ("dolor", "equivalencia"):
    ids = sorted(i for i in tipo if tipo[i] == t)
    if not respuestas or not ids:
        continue
    tabla = [[respuestas[q][i] for q in respuestas] for i in ids]
    mayoria = [Counter(r).most_common(1)[0][0] if len(set(r)) == 1 or r.count(True) != r.count(False) else None for r in tabla]
    validos = [(i, m) for i, m in zip(ids, mayoria) if m is not None]
    humano = [m for _, m in validos]
    res = {"items": len(ids), "empates_humanos": mayoria.count(None), "fleiss_humanos": fleiss(tabla)}
    for quien in ("modelo", "criterio_viejo", "claude", *jueces_llm):
        if quien not in clave[ids[0]]:
            continue
        juez = [clave[i][quien] for i, _ in validos]
        vp = sum(j and h for j, h in zip(juez, humano))
        res[quien] = {"acuerdo": round(sum(j == h for j, h in zip(juez, humano)) / len(humano), 3), "kappa": kappa(juez, humano),
                      "precision": round(vp / max(1, sum(juez)), 3), "exhaustividad": round(vp / max(1, sum(humano)), 3)}
    salida[t] = res
(AQUI / "calibracion.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(salida, ensure_ascii=False, indent=1))
