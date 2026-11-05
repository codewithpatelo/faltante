"""Imprime, por búsqueda, qué publicaciones ganan (venden) y cuáles pierden, con índice para citar.

Es lo que lee el LLM en la etapa divergente, y el baseline de términos al lado.

    python scripts/vista_votos.py data/capturas/captura_ml_2026-11-05.json "olla lenta crock pot" ...
    python scripts/vista_votos.py <captura> --dev     # todas las búsquedas de desarrollo
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from harness.votos import contraste_terminos, vista  # noqa: E402

cap = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["busquedas"]
pedidas = sys.argv[2:]
if pedidas == ["--dev"]:
    pedidas = json.loads((RAIZ / "data/divergente/particion.json").read_text(encoding="utf-8"))["dev"]
for b in pedidas:
    v = vista(cap[b]["publicaciones"])
    c = contraste_terminos(cap[b]["publicaciones"])
    print(f"\n### {b} — ventas visibles {v['ventas_visibles']}")
    print("baseline, términos que ganan:", ", ".join(t for t, _ in c["ganan"]), "| que pierden:", ", ".join(t for t, _ in c["pierden"]))
    print("GANAN:")
    for p in v["ganan"]:
        print(f" [{p['i']}] +{p['vendidos']} ${(p['precio'] or 0)//1000}k {'INTL ' if p['internacional'] else ''}{p['titulo'][:80]}")
    print("PIERDEN:")
    for p in v["pierden"]:
        print(f" [{p['i']}] ${(p['precio'] or 0)//1000}k {'INTL ' if p['internacional'] else ''}{p['titulo'][:70]}")
