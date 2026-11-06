"""Cuántas personas medir por grupo en C1: potencia de Fisher (unilateral, 5%) para el efecto chico observado.

    python data/evaluacion/dolor_de_la_propuesta/potencia.py
"""
import glob
import json
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact

AQUI = Path(__file__).resolve().parent
propuesta, control = [], []
for f in glob.glob(str(AQUI / "dolor_*.json")):
    for m in json.loads(Path(f).read_text(encoding="utf-8"))["medidas"]:
        propuesta.append(m["veredicto"]["desatendidos"] / m["medicion"]["propuesta"]["medidas"])
        control.append(m["veredicto"]["en_el_control"] / m["medicion"]["control"]["medidas"])
efecto, base = np.percentile(propuesta, 25), np.percentile(control, 50)
rng = np.random.default_rng(7)


def potencia(n, sims=2000):
    x, y = rng.binomial(n, efecto, sims), rng.binomial(n, base, sims)
    return np.mean([fisher_exact([[i, n - i], [j, n - j]], alternative="greater")[1] < 0.05 for i, j in zip(x, y)])


print(f"efecto (cuartil 1 de desatendidos): {efecto:.3f}; control (mediana): {base:.3f}")
for n in range(50, 210, 10):
    print(n, round(potencia(n), 3))
