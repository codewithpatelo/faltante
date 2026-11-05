"""Pasa un archivo de hipótesis por el guardrail de citas.

    python scripts/validar_hipotesis.py data/divergente/hipotesis_piloto.json
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from harness.votos import validar_hipotesis  # noqa: E402

datos = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cap = json.loads((RAIZ / datos["captura"]).read_text(encoding="utf-8"))["busquedas"]
fuente = {b: d["publicaciones"] for b, d in cap.items()}
mal = 0
for h in datos["hipotesis"]:
    errores = validar_hipotesis(h, fuente)
    mal += bool(errores)
    print(f"{h['id']}: {'pasa' if not errores else 'RECHAZADA'}  {h['necesidad'][:90]}")
    for e in errores:
        print("    -", e)
sys.exit(1 if mal else 0)
