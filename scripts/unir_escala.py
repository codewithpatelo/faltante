"""Une lo que juntó scripts/voces_ml.js (opiniones y preguntas) con los productos ancla
elegidos por scripts/elegir_anclas.py, en un corpus que lee el programa.

    python scripts/unir_escala.py 2026-11-05
      lee   data/escala/anclas_<fecha>.json, opiniones_<fecha>*.json, preguntas_<fecha>*.json
      deja  data/escala/corpus_<fecha>.json   (productos E001, E002, ...)

Los productos sin opiniones ni preguntas quedan afuera: no hay voces que leer.

Partición: cada BÚSQUEDA va entera a "escala_dev" o a "escala_test" (así los dos anclas de una
búsqueda no quedan repartidos). Se ordenan las búsquedas por un hash de su texto y la primera
mitad va a dev. Se decide acá, antes de leer nada.
"""

import hashlib
import json
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "data/escala"


def particiones(busquedas: set[str]) -> dict[str, str]:
    orden = sorted(busquedas, key=lambda b: hashlib.md5(b.encode()).hexdigest())
    return {b: "escala_dev" if i < len(orden) / 2 else "escala_test" for i, b in enumerate(orden)}


def unir(fecha: str) -> list[dict]:
    anclas = json.loads((CARPETA / f"anclas_{fecha}.json").read_text(encoding="utf-8"))
    leer = lambda patron: [p for f in sorted(CARPETA.glob(patron)) for p in json.loads(f.read_text(encoding="utf-8"))["productos"]]
    opiniones = {p["url"]: p for p in leer(f"opiniones_{fecha}*.json")}
    preguntas = {p["item"]: p["preguntas"] for p in leer(f"preguntas_{fecha}*.json") if "preguntas" in p}
    parte = particiones({a["busqueda"] for a in anclas})
    corpus = []
    for a in anclas:
        o = opiniones.get(a["url"], {})
        p = preguntas.get(o.get("item"), [])
        if not o.get("opiniones") and not p:
            continue
        corpus.append({"id": f"E{len(corpus) + 1:03d}", "particion": parte[a["busqueda"]], "busqueda": a["busqueda"],
                       "titulo": o.get("titulo") or a["titulo"], "vendidos": a["vendidos"], "precio": a["precio"],
                       "url": a["url"], "calificacion": o.get("calificacion"),
                       "opiniones": o.get("opiniones", []), "preguntas": p})
    return corpus


if __name__ == "__main__":
    fecha = sys.argv[1] if len(sys.argv) > 1 else "2026-11-05"
    corpus = unir(fecha)
    (CARPETA / f"corpus_{fecha}.json").write_text(json.dumps({"fecha": fecha, "productos": corpus}, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
    for parte in ("escala_dev", "escala_test"):
        ps = [p for p in corpus if p["particion"] == parte]
        print(f"{parte}: {len(ps)} productos de {len({p['busqueda'] for p in ps})} búsquedas, "
              f"{sum(len(p['opiniones']) for p in ps)} opiniones, {sum(len(p['preguntas']) for p in ps)} preguntas")
