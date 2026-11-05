"""Intenta refutar H1 (voltaje) y H2 (lenguaje) del piloto, solo con búsquedas de desarrollo.

    python scripts/convergencia_piloto.py  ->  data/divergente/convergencia_piloto.json
"""
import json
import re
import statistics as st
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from harness.votos import norm  # noqa: E402

cap = json.loads((RAIZ / "data/capturas/captura_ml_2026-11-05.json").read_text(encoding="utf-8"))["busquedas"]
dev = json.loads((RAIZ / "data/divergente/particion.json").read_text(encoding="utf-8"))["dev"]
COMPATIBLE = re.compile(r"220\s*v|50\s*hz|50\s*/\s*60\s*hz")
SOLO_110 = re.compile(r"\b1[12]0\s*v\b")


def tasa(pubs):
    return {"publicaciones": len(pubs), "venden": sum(1 for p in pubs if p["vendidos"] > 0),
            "mediana_precio": int(st.median([p["precio"] for p in pubs if p["precio"]])) if pubs else None}


salida = {"H1_voltaje": {}, "H2_lenguaje": {}}
for b in ["mixer inmersion turelar", "olla lenta crock pot", "lonchera termica hotor"]:
    assert b in dev
    P = cap[b]["publicaciones"]
    t = [norm(p["titulo"]) for p in P]
    salida["H1_voltaje"][b] = {
        "declara_220_o_50hz": tasa([p for p, x in zip(P, t) if COMPATIBLE.search(x)]),
        "declara_110_120v": tasa([p for p, x in zip(P, t) if SOLO_110.search(x) and not COMPATIBLE.search(x)]),
        "no_menciona": tasa([p for p, x in zip(P, t) if not COMPATIBLE.search(x) and not SOLO_110.search(x)]),
    }
PARES = {"organizador esponja cisily": ("bacha", "fregadero"),
         "mixer inmersion turelar": ("minipimer|mini pimer|pimer", "licuadora de inmersion|batidora de inmersion")}
for b, (aca, traducido) in PARES.items():
    P = [p for p in cap[b]["publicaciones"] if not p["internacional"]]  # solo locales: sin espera
    salida["H2_lenguaje"][b] = {
        f"local con '{aca}'": tasa([p for p in P if re.search(aca, norm(p["titulo"]))]),
        f"local con '{traducido}'": tasa([p for p in P if re.search(traducido, norm(p["titulo"]))]),
    }
out = RAIZ / "data/divergente/convergencia_piloto.json"
out.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(salida, ensure_ascii=False, indent=1))
