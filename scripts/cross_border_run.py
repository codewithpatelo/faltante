"""Productos que se compran por Compra Internacional: ¿hay equivalente con stock local?

    python scripts/cross_border_run.py data/capturas/captura_ml_locales_cross_border_2026-11-05.json

Para cada producto de data/cross_border/emparejamiento.json toma la búsqueda local, marca
como equivalentes las publicaciones LOCALES que cumplen el criterio, y decide con
harness/cross_border.py. Lo corre tres veces:
- `baseline`: sin LLM, las dos primeras palabras de contenido del título internacional;
- `regla_llm`: búsqueda y palabras elegidas por el LLM para ese producto;
- `equivalencia_llm`: el LLM juzga publicación por publicación cuáles son equivalentes de
  verdad (tamaño, gama), en data/cross_border/equivalencia_llm.json, si existe para ese producto.
Escribe data/cross_border/resultado_<fecha>.json.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from harness.cross_border import evaluar  # noqa: E402
from harness.votos import norm, tokens  # noqa: E402


def cumple(titulo: str, criterio: list[list[str]]) -> bool:
    t = norm(titulo)
    return all(any(norm(p) in t for p in grupo) for grupo in criterio)


def main(ruta_captura: Path) -> list[dict]:
    cap = json.loads(ruta_captura.read_text(encoding="utf-8"))
    emp = json.loads((RAIZ / "data/cross_border/emparejamiento.json").read_text(encoding="utf-8"))["productos"]
    ruta_eq = RAIZ / "data/cross_border/equivalencia_llm.json"
    equiv = json.loads(ruta_eq.read_text(encoding="utf-8"))["productos"] if ruta_eq.exists() else {}
    salida = []
    for p in emp:
        pubs = cap["busquedas"][p["busqueda"]]["publicaciones"]
        locales = [x for x in pubs if not x["internacional"]]
        intl = {"titulo": p["intl"], "vendidos": p["vendidos"], "precio": p["precio"]}
        crit_base = [[w] for w in tokens(p["intl"])[:2]]
        fila = {"id": p["id"], "producto_intl": p["intl"], "intl_vendidos": p["vendidos"], "intl_precio": p["precio"],
                "busqueda": p["busqueda"], "locales_en_pagina": len(locales)}
        variantes = [("baseline", crit_base, None), ("regla_llm", p["criterio"], None)]
        if p["id"] in equiv:
            variantes.append(("equivalencia_llm", None, equiv[p["id"]]["equivalentes"]))
        for nombre, crit, indices in variantes:
            if indices is not None:
                assert all(not pubs[i]["internacional"] for i in indices), f"{p['id']}: equivalencia cita una internacional"
                eq = [pubs[i] for i in indices]
            else:
                eq = [x for x in locales if cumple(x["titulo"], crit)]
            fila[nombre] = {"criterio": crit, "indices": indices, "equivalentes_locales": len(eq),
                            "equivalentes_que_venden": sum(1 for x in eq if x["vendidos"] > 0),
                            "ventas_visibles_equivalentes": sum(x["vendidos"] for x in eq), **evaluar(intl, eq)}
        salida.append(fila)
    out = RAIZ / f"data/cross_border/resultado_{cap['fecha']}.json"
    out.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    return salida


if __name__ == "__main__":
    for f in main(Path(sys.argv[1])):
        e = f.get("equivalencia_llm")
        extra = f" | equivalencia LLM: {e['veredicto']:<12} ({e['equivalentes_que_venden']}/{e['equivalentes_locales']} venden, ratio {e.get('ratio_local_intl')})" if e else ""
        print(f"{f['id']} {f['producto_intl'][:44]:<44} +{f['intl_vendidos']:<5} ${f['intl_precio']//1000}k | "
              f"base: {f['baseline']['veredicto']:<12} | regla LLM: {f['regla_llm']['veredicto']:<12}{extra}")
