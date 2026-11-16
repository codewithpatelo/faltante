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
from pathlib import Path

from harness.baselines import b1_queja_mas_frecuente, b2_pedidos_de_repuesto
from harness.confianza import confianza
from harness.embudo import EMBUDO, Propuesta, recorrer
from harness.voces import RAIZ, productos, sin_acentos

SERENDIPIA = RAIZ / "data/serendipia"
METODOS = ["llm", "B1", "B2"]


def propuestas(particion: str) -> list[Propuesta]:
    return propuestas_de_un_archivo(SERENDIPIA / f"divergente_{particion}.json")


def propuestas_de_un_archivo(archivo) -> list[Propuesta]:
    from harness.equivalencias import clave, guardadas
    del_llm = json.loads(Path(archivo).read_text(encoding="utf-8"))
    juicios = guardadas()
    capturas = busquedas_capturadas()
    fobs = precios_de_proveedor()
    todos = productos()
    titulos_ancla = {sin_acentos(p["titulo"]) for p in todos.values()}

    dolor = del_llm.get("dolor", {})

    def armar(metodo, anclas, oportunidad, señales, fob_ref, verifica_citas, clave_dolor):
        return Propuesta(metodo, anclas, oportunidad, señales, verifica_citas, dolor=dolor.get(metodo, {}).get(clave_dolor),
                         equivalentes_juzgados=juicios.get(clave(oportunidad["que_traer"], oportunidad["busqueda_ml"])),
                         fob=fobs.get(fob_ref) if fob_ref else None,
                         captura=capturas.get(oportunidad["busqueda_ml"]), titulos_ancla=titulos_ancla,
                         capturas_de_origen=[capturas[b] for b in dict.fromkeys(a["busqueda"] for a in anclas) if b in capturas])

    # LLM: cada oportunidad cita señales "P12.S2" de uno o más productos
    señales = {f"{pid}.{s['id']}": {**s, "producto": pid} for pid, lista in del_llm["señales"].items() for s in lista}
    salida = []
    for o in del_llm["oportunidades"]:
        citadas = [señales[i] for i in o["señales"] if i in señales]
        anclas = [todos[pid] for pid in dict.fromkeys(s["producto"] for s in citadas)]
        if anclas:
            salida.append(armar("llm", anclas, o, citadas, o["busqueda_ml"], True, o["id"]))   # el precio de proveedor va por búsqueda: el ID cambia entre corridas
    # Baselines: una propuesta por producto
    for pid in del_llm["señales"]:
        for metodo, baseline in (("B1", b1_queja_mas_frecuente), ("B2", b2_pedidos_de_repuesto)):
            propuesta = baseline(todos[pid])
            if propuesta:
                señal, oportunidad, fob_ref = propuesta
                salida.append(armar(metodo, [todos[pid]], oportunidad, [{**señal, "producto": pid}], fob_ref, False, f"{metodo}.{pid}"))
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
        distintas = len({r["busqueda_ml"] for r in rs if r["estado"] != "descartada"})
        filas.append(f"| {metodo} | {len(rs)} | " + " | ".join(map(str, pasan)) + f" | {cond} | {distintas} |")
    return "\n".join(filas)


def con_confianza(recorridos: list[dict]) -> list[dict]:
    """A cada oportunidad que no se descartó le agrega su confianza. Si la misma oportunidad
    salió de varios productos (misma búsqueda, mismo método), se juzga con todos juntos."""
    grupos = {}
    for r in recorridos:
        if r["estado"] != "descartada":
            grupos.setdefault((r["metodo"], r["busqueda_ml"]), []).append(r)
    for grupo in grupos.values():
        c = confianza(grupo)
        for r in grupo:
            r["confianza"] = c
    return recorridos


def precios_de_proveedor() -> dict:
    """Todas las referencias de proveedor (data/serendipia/fob_*.json), por ID de oportunidad."""
    fobs = {}
    for f in sorted(SERENDIPIA.glob("fob_*.json")):
        fobs.update(json.loads(f.read_text(encoding="utf-8")))
    return fobs


def busquedas_capturadas() -> dict:
    """Todas las búsquedas capturadas (las de C4 y C5 y las de los productos ancla a escala):
    {"texto de la búsqueda": {"total": ..., "publicaciones": [...]}}."""
    busquedas = {}
    for f in sorted((RAIZ / "data/capturas").glob("captura_ml_*.json")):
        busquedas.update(json.loads(f.read_text(encoding="utf-8"))["busquedas"])
    return busquedas


if __name__ == "__main__":
    particion = sys.argv[1] if len(sys.argv) > 1 else "escala_dev_api"
    recorridos = con_confianza([recorrer(p) for p in propuestas(particion)])
    (SERENDIPIA / f"embudo_{particion}.json").write_text(json.dumps(recorridos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"## {particion}\n{tabla(recorridos)}\n")
    for r in recorridos:
        nivel = f"riesgos: {len(r['confianza']['riesgos'])}" if "confianza" in r else ""
        print(f"  {r['metodo']:<3} {','.join(r['productos']):<7} {r['estado']:<11} {r['se_detiene_en'] or '':<15} {r['que_traer'][:55]:<55} {r['motivo']} {nivel}")
