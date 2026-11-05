"""Corre todo para una partición: junta las propuestas del LLM y de los dos baselines, las
pasa por el embudo y guarda el recorrido de cada una.

    python -m harness.correr dev        # propuestas del LLM en data/serendipia/divergente_dev.json
    python -m harness.correr test
    python -m harness.correr test_api   # las que hizo la API (python -m harness.divergente test)

Salida: data/serendipia/embudo_<particion>.json y una tabla de cuántas pasan cada chequeo.
"""

from __future__ import annotations

import json
import sys

from harness.baselines import b1_queja_mas_frecuente, b2_pedidos_de_repuesto
from harness.embudo import EMBUDO, Propuesta, recorrer
from harness.voces import RAIZ, productos, sin_acentos

SERENDIPIA = RAIZ / "data/serendipia"
METODOS = ["llm", "B1", "B2"]


def propuestas(particion: str) -> list[Propuesta]:
    del_llm = json.loads((SERENDIPIA / f"divergente_{particion}.json").read_text(encoding="utf-8"))["por_producto"]
    capturas = _busquedas_capturadas()
    fobs = json.loads((SERENDIPIA / "fob_2026-11-05.json").read_text(encoding="utf-8"))
    todos = productos()
    anclas = {sin_acentos(p["titulo"]) for p in todos.values()}

    def armar(metodo, producto, oportunidad, señales, fob_ref, verifica_citas):
        return Propuesta(metodo, producto, oportunidad, señales, verifica_citas,
                         fob=fobs.get(fob_ref) if fob_ref else None,
                         captura=capturas.get(oportunidad["busqueda_ml"]), titulos_ancla=anclas)

    salida = []
    for pid, leido in del_llm.items():
        producto = todos[pid]
        señales = {s["id"]: s for s in leido["señales"]}
        for o in leido["oportunidades"]:
            salida.append(armar("llm", producto, o, [señales[i] for i in o["señales"] if i in señales], o["id"], True))
        for metodo, baseline in (("B1", b1_queja_mas_frecuente), ("B2", b2_pedidos_de_repuesto)):
            propuesta = baseline(producto)
            if propuesta:
                señal, oportunidad, fob_ref = propuesta
                salida.append(armar(metodo, producto, oportunidad, [señal], fob_ref, False))
    return salida


def tabla(recorridos: list[dict]) -> str:
    """Cuántas propuestas de cada método pasan cada chequeo."""
    nombres = [ch.nombre for ch in EMBUDO]
    filas = ["| método | propuestas | " + " | ".join(nombres) + " | condicionales | distintas que sobreviven o quedan condicionales |",
             "|---" * (len(nombres) + 4) + "|"]
    for metodo in METODOS:
        rs = [r for r in recorridos if r["metodo"] == metodo]
        pasan = [sum(1 for r in rs if any(x["chequeo"] == n and x["pasa"] for x in r["recorrido"])) for n in nombres]
        cond = sum(1 for r in rs if r["estado"] == "condicional")
        distintas = len({r["busqueda_ml"] for r in rs if r["estado"] != "muere"})
        filas.append(f"| {metodo} | {len(rs)} | " + " | ".join(map(str, pasan)) + f" | {cond} | {distintas} |")
    return "\n".join(filas)


def _busquedas_capturadas() -> dict:
    busquedas = {}
    for f in sorted((RAIZ / "data/capturas").glob("captura_ml_serendipia_*.json")):
        busquedas.update(json.loads(f.read_text(encoding="utf-8"))["busquedas"])
    return busquedas


if __name__ == "__main__":
    particion = sys.argv[1] if len(sys.argv) > 1 else "dev"
    recorridos = [recorrer(p) for p in propuestas(particion)]
    (SERENDIPIA / f"embudo_{particion}.json").write_text(json.dumps(recorridos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"## {particion}\n{tabla(recorridos)}\n")
    for r in recorridos:
        print(f"  {r['metodo']:<3} {r['producto']} {r['estado']:<11} {r['se_detiene_en'] or '':<15} {r['que_traer'][:55]:<55} {r['motivo']}")
