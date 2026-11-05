"""Precisión, recall y F1 de cada método de emparejamiento contra las etiquetas humanas.

    python scripts/calcular_equivalencia.py   # lee data/evaluacion/equivalencia_*.csv
"""
import csv
import json
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data/evaluacion"
clave = json.loads((D / "clave_equivalencia.json").read_text())
etiquetas = {}
for f in sorted(D.glob("equivalencia_*.csv")):
    for r in csv.DictReader(f.open()):
        v = r["equivalente_si_no"].strip().lower()
        if v in ("si", "sí", "no"):
            etiquetas.setdefault(r["item"], []).append(v != "no")
if not etiquetas:
    raise SystemExit("Todavía no hay etiquetas: copiá planilla_equivalencia.csv a equivalencia_<nombre>.csv y completala")
oro = {k: sum(v) > len(v) / 2 for k, v in etiquetas.items()}  # mayoría
print(f"{len(oro)} publicaciones etiquetadas por {len(list(D.glob('equivalencia_*.csv')))} persona(s)\n")
for metodo in ("baseline", "regla_llm", "equivalencia_llm"):
    tp = sum(1 for k, y in oro.items() if y and clave[k][metodo])
    fp = sum(1 for k, y in oro.items() if not y and clave[k][metodo])
    fn = sum(1 for k, y in oro.items() if y and not clave[k][metodo])
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * p * r / (p + r) if p + r else 0
    print(f"{metodo:<17} precisión {p:.2f}  recall {r:.2f}  F1 {f1:.2f}")
