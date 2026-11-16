"""Calidad de las oportunidades no descartadas según el juicio humano a ciegas, por método.

    python data/evaluacion/humano/evaluar_oportunidades.py -> calidad_oportunidades.json

Por método y partición: cuántas oportunidades, y qué proporción la mayoría humana juzgó concreta,
no obvia y "la cotizaría"; y las que cumplen las tres a la vez (la medida de calidad).
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SI = {"si", "sí", "s", "1", "true", "x"}
clave = {k["id"]: k for k in json.loads((AQUI / "clave_oportunidades.json").read_text(encoding="utf-8"))}
votos = defaultdict(lambda: defaultdict(list))
jueces = []
for f in sorted(AQUI.glob("oportunidades_*.csv")):
    filas = list(csv.DictReader(open(f, encoding="utf-8")))
    if not all(r[c].strip() for r in filas for c in ("concreta", "obvia", "la_cotizaria")):
        continue
    jueces.append(f.stem.removeprefix("oportunidades_"))
    for r in filas:
        for c in ("concreta", "obvia", "la_cotizaria"):
            votos[r["id"]][c].append(r[c].strip().lower() in SI)
mayoria = lambda vs: Counter(vs).most_common(1)[0][0] if vs and vs.count(True) != vs.count(False) else None
salida = {"jueces": jueces}
grupos = defaultdict(list)
for i, k in clave.items():
    if i in votos:
        grupos[f"{k['metodo']} {k['particion']}"].append({c: mayoria(votos[i][c]) for c in ("concreta", "obvia", "la_cotizaria")})
for g, vs in sorted(grupos.items()):
    buena = [v["concreta"] and v["obvia"] is False and v["la_cotizaria"] for v in vs]
    salida[g] = {"oportunidades": len(vs), **{c: sum(v[c] is True for v in vs) for c in ("concreta", "obvia", "la_cotizaria")},
                 "concreta_no_obvia_y_la_cotizaria": sum(bool(b) for b in buena)}
(AQUI / "calidad_oportunidades.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(salida, ensure_ascii=False, indent=1))
