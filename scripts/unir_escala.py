"""Une lo que juntó scripts/voces_ml.js (opiniones y preguntas) con los productos ancla
elegidos por scripts/elegir_anclas.py, en un corpus que lee el programa.

    python scripts/unir_escala.py 2026-11-05
      lee   data/escala/anclas_<fecha>.json, opiniones_<fecha>.json, preguntas_<fecha>.json
      deja  data/escala/corpus_<fecha>.json   (productos E001, E002, ...; partición "escala")

Los productos sin opiniones ni preguntas quedan afuera: no hay voces que leer.
"""

import json
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "data/escala"


def unir(fecha: str) -> list[dict]:
    anclas = json.loads((CARPETA / f"anclas_{fecha}.json").read_text(encoding="utf-8"))
    opiniones = {p["url"]: p for p in json.loads((CARPETA / f"opiniones_{fecha}.json").read_text(encoding="utf-8"))["productos"]}
    preguntas = {p["item"]: p["preguntas"] for p in json.loads((CARPETA / f"preguntas_{fecha}.json").read_text(encoding="utf-8"))["productos"]
                 if "preguntas" in p}
    corpus = []
    for a in anclas:
        o = opiniones.get(a["url"], {})
        p = preguntas.get(o.get("item"), [])
        if not o.get("opiniones") and not p:
            continue
        corpus.append({"id": f"E{len(corpus) + 1:03d}", "particion": "escala", "busqueda": a["busqueda"],
                       "titulo": o.get("titulo") or a["titulo"], "vendidos": a["vendidos"], "precio": a["precio"],
                       "url": a["url"], "calificacion": o.get("calificacion"),
                       "opiniones": o.get("opiniones", []), "preguntas": p})
    return corpus


if __name__ == "__main__":
    fecha = sys.argv[1] if len(sys.argv) > 1 else "2026-11-05"
    corpus = unir(fecha)
    (CARPETA / f"corpus_{fecha}.json").write_text(json.dumps({"fecha": fecha, "productos": corpus}, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
    print(f"{len(corpus)} productos, {sum(len(p['opiniones']) for p in corpus)} opiniones, "
          f"{sum(len(p['preguntas']) for p in corpus)} preguntas -> data/escala/corpus_{fecha}.json")
