"""Convierte una captura del listado (scripts/captura_ml.js) en la foto que usa el diagnóstico.

Marca cada publicación como "es el producto" o "es otra cosa" con el criterio por palabras
de data/diagnostico/criterios.json (lo escribió el LLM a partir del título de Amazon) y
excluye accesorios ("funda para Stanley" no es un Stanley).

    python scripts/emparejar.py captura_ml_2026-11-05.json [salida.json]

Es la versión por reglas del emparejamiento. La versión con LLM se compara contra esta.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CRITERIOS = RAIZ / "data/diagnostico/criterios.json"
ACCESORIO_INICIO = ("protector", "funda", "repuesto", "tapa", "correa", "pajita", "sorbete",
                    "accesorio", "cepillo", "kit de", "sticker")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def es_accesorio(titulo: str, marcas: list[str]) -> bool:
    t = norm(titulo)
    if t.startswith(ACCESORIO_INICIO) or "compatible" in t:
        return True
    return any(re.search(rf"\bpara (el |la |los |las |tu |vaso |botella |termo )?{re.escape(m)}", t) for m in marcas)


def emparejar(titulo: str, grupos: list[list[str]]) -> tuple[bool, bool]:
    """Devuelve (es_producto, es_accesorio)."""
    t = norm(titulo)
    coincide = all(any(norm(p) in t for p in g) for g in grupos)
    acc = coincide and es_accesorio(titulo, [norm(p) for p in grupos[0]])
    return coincide and not acc, acc


def main(entrada: Path, salida: Path | None) -> Path:
    cap = json.loads(entrada.read_text(encoding="utf-8"))
    crit = {k: v for k, v in json.loads(CRITERIOS.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    foto = {
        "fecha": cap["fecha"],
        "fuente": cap["fuente"],
        "emparejamiento": "por reglas: scripts/emparejar.py con data/diagnostico/criterios.json",
        "busquedas": {},
    }
    for b, d in cap["busquedas"].items():
        if b not in crit:
            print(f"aviso: '{b}' no tiene criterio en criterios.json; se saltea")
            continue
        pubs = []
        for p in d["publicaciones"]:
            prod, acc = emparejar(p["titulo"], crit[b])
            pubs.append({**p, "es_producto": int(prod), "accesorio": acc})
        foto["busquedas"][b] = {"total": d.get("total"), "publicaciones": pubs}
        n = sum(p["es_producto"] for p in pubs)
        print(f"{b:<32} {len(pubs):>3} publicaciones, {n:>3} son el producto")
    salida = salida or RAIZ / f"data/diagnostico/foto_ml_{cap['fecha']}.json"
    salida.write_text(json.dumps(foto, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nfoto escrita en {salida.relative_to(RAIZ) if salida.is_relative_to(RAIZ) else salida}")
    return salida


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).expanduser(), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
