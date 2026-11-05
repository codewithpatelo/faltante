"""Une productos (pies), opiniones y preguntas (manos) en un solo archivo por producto.

    python scripts/unir_voces.py 2026-11-05  ->  data/voces/corpus_<fecha>.json
"""
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data/voces"
f = sys.argv[1] if len(sys.argv) > 1 else "2026-11-05"
prods = json.loads((D / f"productos_{f}.json").read_text(encoding="utf-8"))["productos"]
ops = json.loads((D / f"opiniones_{f}.json").read_text(encoding="utf-8"))["productos"]
pregs = json.loads((D / f"preguntas_{f}.json").read_text(encoding="utf-8"))["preguntas"]
salida = []
for i, p in enumerate(prods):
    camino = p["url"].replace("https://www.mercadolibre.com.ar", "")
    o = ops.get(camino)
    if o is None:
        print(f"sin opiniones: {p['titulo'][:50]}")
        continue
    qid = (o.get("preguntas_url") or "").rsplit("/", 1)[-1]
    salida.append({"id": f"P{i+1:02d}", **p, "calificacion": o.get("calificacion"),
                   "opiniones": o["opiniones"], "preguntas": [q[0] for q in pregs.get(qid, []) if q and len(q[0]) > 8]})
(D / f"corpus_{f}.json").write_text(json.dumps({"fecha": f, "productos": salida}, ensure_ascii=False, indent=1), encoding="utf-8")
for s in salida:
    print(f"{s['id']} {s['particion']:<4} {len(s['opiniones']):>3} op {len(s['preguntas']):>2} pr  +{s['vendidos']:<6} {s['titulo'][:55]}")
