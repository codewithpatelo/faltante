"""Promedios por fuente (llm vs baseline) y acuerdo entre jueces (kappa de Cohen ponderado).

    python scripts/calcular_juicios.py   # lee data/evaluacion/juicios_*.csv
"""
import csv
import itertools
import json
import statistics as st
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data/evaluacion"
CRIT = ["sostenida_1a3", "no_obvia_1a3", "accionable_1a3"]
clave = json.loads((D / "clave_fuentes.json").read_text())
jueces = {}
for f in sorted(D.glob("juicios_*.csv")):
    filas = [r for r in csv.DictReader(f.open()) if all(r[c].strip() for c in CRIT)]
    jueces[f.stem.replace("juicios_", "")] = {r["item"]: {c: int(r[c]) for c in CRIT} for r in filas}
if not jueces:
    raise SystemExit("Todavía no hay juicios: ver data/evaluacion/COMO_JUZGAR.md")


def kappa_ponderado(a, b, k=3):
    """Kappa de Cohen con pesos lineales para escala ordinal 1..k."""
    n = len(a)
    w = lambda i, j: 1 - abs(i - j) / (k - 1)
    po = sum(w(x, y) for x, y in zip(a, b)) / n
    pa = [a.count(i) / n for i in range(1, k + 1)]
    pb = [b.count(i) / n for i in range(1, k + 1)]
    pe = sum(w(i + 1, j + 1) * pa[i] * pb[j] for i in range(k) for j in range(k))
    return round((po - pe) / (1 - pe), 2) if pe < 1 else 1.0


print("Promedio por fuente (todos los jueces):")
for fuente in ("llm", "baseline"):
    items = [i for i, s in clave.items() if s == fuente]
    fila = {c: round(st.mean(j[i][c] for j in jueces.values() for i in items if i in j), 2) for c in CRIT}
    print(f"  {fuente:<9}", fila)
print("\nAcuerdo entre jueces (kappa ponderado):")
for (n1, j1), (n2, j2) in itertools.combinations(jueces.items(), 2):
    comunes = sorted(set(j1) & set(j2))
    print(f"  {n1} vs {n2}:", {c: kappa_ponderado([j1[i][c] for i in comunes], [j2[i][c] for i in comunes]) for c in CRIT})
