"""Elige los productos ancla de cada búsqueda: los 2 más elegidos (más "+N vendidos") con
stock local, sin publicidades. Esos son los productos cuyas voces se leen.

    python scripts/elegir_anclas.py data/capturas/captura_ml_escala_<fecha>.json <fecha>
      deja data/escala/anclas_<fecha>.json e imprime las URLs para scripts/voces_ml.js
"""

import json
import sys

ANCLAS_POR_BUSQUEDA = 2
MIN_VENDIDOS = 500       # mismo piso que C3: si el más elegido vende menos, la búsqueda no aporta


def anclas(captura: dict) -> list[dict]:
    elegidas = []
    for busqueda, datos in captura["busquedas"].items():
        candidatas = [p for p in datos["publicaciones"]
                      if p.get("url") and not p["internacional"] and p["vendidos"] >= MIN_VENDIDOS]
        vistas, top = set(), []
        for p in sorted(candidatas, key=lambda p: -p["vendidos"]):
            if p["titulo"].lower() not in vistas:
                vistas.add(p["titulo"].lower())
                top.append({"busqueda": busqueda, **p})
        elegidas += top[:ANCLAS_POR_BUSQUEDA]
    return elegidas


if __name__ == "__main__":
    from pathlib import Path
    elegidas = anclas(json.loads(open(sys.argv[1], encoding="utf-8").read()))
    destino = Path(__file__).resolve().parent.parent / f"data/escala/anclas_{sys.argv[2]}.json"
    destino.write_text(json.dumps(elegidas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps([a["url"] for a in elegidas], ensure_ascii=False))
    print(f"{len(elegidas)} productos ancla -> {destino}", file=sys.stderr)
