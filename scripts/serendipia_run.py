"""Corre el embudo de serendipia sobre una partición y compara el LLM con dos baselines.

    python scripts/serendipia_run.py dev

Entradas
  data/voces/corpus_2026-11-05.json            pies + manos de cada producto (P01..P21)
  data/serendipia/divergente_<part>.json        salida del paso divergente (LLM)
  data/capturas/captura_ml_serendipia_*.json    búsquedas de Mercado Libre para C4
  data/serendipia/fob_2026-11-05.json           referencias de proveedor para C5
Salidas
  data/serendipia/embudo_<part>.json            cada oportunidad con el motivo por el que murió o sobrevivió
  OPORTUNIDADES.md (solo dev por ahora)         las que sobreviven, con la evidencia

Métodos que pasan por el mismo embudo:
  llm  : señales y oportunidades que el LLM propone citando textos (skills/leer_voces)
  B1   : la queja más frecuente del producto (conteo de palabras, sin LLM) -> "mejorar el ancla"
  B2   : regla de repuestos: si 2+ preguntas piden repuesto -> "repuesto del ancla" (sin LLM).
         Ojo: la regla se escribió después de leer las preguntas de dev; test la juzga.
"""

from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from harness.serendipia import (MIN_VENDIDOS_ANCLA, baseline_señal, hueco_local, margen, medir_señal,  # noqa: E402
                                norm, textos_numerados, validar_señal)

REGLA_REPUESTO = re.compile(r"repuesto|respuesto|por separado|venden (los|las|el|la)\b|se consigue")


def cargar(part: str):
    corpus = {p["id"]: p for p in json.loads((RAIZ / "data/voces/corpus_2026-11-05.json").read_text())["productos"]}
    div = json.loads((RAIZ / f"data/serendipia/divergente_{part}.json").read_text())["por_producto"]
    busquedas = {}
    for f in sorted((RAIZ / "data/capturas").glob("captura_ml_serendipia_*.json")):
        busquedas.update(json.loads(f.read_text())["busquedas"])
    fob = json.loads((RAIZ / "data/serendipia/fob_2026-11-05.json").read_text())
    return corpus, div, busquedas, fob


def propuestas_b1(prod, textos):
    s = baseline_señal(textos)
    return [s], [{"id": "B1", "que_traer": f"versión del producto ancla que resuelva la queja '{s['palabras_clave'][0] if s['palabras_clave'] else ''}'",
                  "señales": ["B1"], "busqueda_ml": prod["busqueda"],
                  "criterio_equivalencia": {"todos": [[w] for w in prod["busqueda"].split()[:1]]}, "fob": None}]


def propuestas_b2(prod, textos):
    pedidos = [i for i, t in textos.items() if i.startswith("p") and REGLA_REPUESTO.search(norm(t.split(" || ")[0]))]
    if len(pedidos) < 2:
        return [], []
    s = {"id": "B2", "tipo": "faltante", "descripcion": "preguntas que piden repuesto",
         "palabras_clave": ["repuesto", "respuesto", "por separado"],
         "citas": [{"texto": i, "fragmento": textos[i][:20]} for i in pedidos[:3]]}
    nucleo = prod["busqueda"].split()[0]
    return [s], [{"id": "B2", "que_traer": f"repuesto de {prod['busqueda']}", "señales": ["B2"],
                  "busqueda_ml": f"repuesto {prod['busqueda']}",
                  "criterio_equivalencia": {"empieza_con": ["repuesto", "kit", "pack", "juego"], "todos": [[nucleo]]}}]


# Para C5, B2 usa la referencia de proveedor del mismo tipo de repuesto que el LLM (lo más favorable para ella).
FOB_CATEGORIA = {"afilador": "O1", "minipimer": "O4", "estante": "O6"}


def embudo(part: str) -> dict:
    corpus, div, busquedas, fob = cargar(part)
    resultados = {"llm": [], "B1": [], "B2": []}
    for pid, salida in div.items():
        prod = corpus[pid]
        textos = textos_numerados(prod)
        metodos = {"llm": (salida["señales"], salida["oportunidades"]),
                   "B1": propuestas_b1(prod, textos), "B2": propuestas_b2(prod, textos)}
        for metodo, (señales, oportunidades) in metodos.items():
            med = {}
            for s in señales:
                errores = validar_señal(s, textos) if metodo == "llm" else []
                med[s["id"]] = {"descripcion": s["descripcion"], "errores": errores, **medir_señal(s, textos)}
            for o in oportunidades:
                r = OrderedDict(metodo=metodo, producto=pid, ancla=prod["titulo"][:60], vendidos_ancla=prod["vendidos"],
                                id=o["id"], que_traer=o["que_traer"], busqueda_ml=o["busqueda_ml"])
                sm = [med[i] for i in o["señales"] if i in med]
                r["señales"] = sm
                buenas = [m for m in sm if not m["errores"]]
                r["guardrail"] = bool(buenas)
                r["C1"] = any(m["C1_verificada"] for m in buenas)
                r["C2"] = any(m["C1_verificada"] and m["C2_subatendida"] for m in buenas)
                r["C3"] = prod["vendidos"] >= MIN_VENDIDOS_ANCLA
                r["_criterio"] = o["criterio_equivalencia"]
                resultados[metodo].append(r)
    # C4 y C5 se evalúan una vez por oportunidad distinta (la misma búsqueda puede venir de dos anclas)
    anclas = {norm(p["titulo"]) for p in corpus.values()}
    for metodo, lista in resultados.items():
        for r in lista:
            crit = r.pop("_criterio")
            r["muere_en"] = next((c for c in ("guardrail", "C1", "C2", "C3") if not r[c]), None)
            if r["muere_en"]:
                continue
            cap = busquedas.get(r["busqueda_ml"])
            if cap is None:
                r["muere_en"], r["motivo"] = "C4", "falta capturar la búsqueda"
                continue
            r["C4_detalle"] = hueco_local(cap["publicaciones"], crit, anclas)
            if not r["C4_detalle"]["C4_hueco"]:
                r["muere_en"] = "C4"
                r["motivo"] = f"ya atendido: {r['C4_detalle']['venden']} equivalentes venden +100"
                continue
            palabras = r["busqueda_ml"].split()
            # B1 no nombra un producto cotizable ("una versión que resuelva 'material'"): no hay a quién pedirle precio.
            clave = r["id"] if metodo == "llm" else FOB_CATEGORIA.get(palabras[1]) if metodo == "B2" else None
            precio = r["C4_detalle"]["precio_mediano_equivalentes_que_vendieron"]
            if not clave or clave not in fob or not precio:
                r["muere_en"], r["motivo"] = "C5", "sin referencia de proveedor o de precio"
                continue
            r["C5_detalle"] = margen(fob[clave], precio)
            c5 = r["C5_detalle"]
            if c5["C5_condicional"]:
                r["condicional"] = True
                r["motivo"] = f"margen base {c5['escenarios']['base']['margen_pct']}% a ${precio:,}; sobrevive si el FOB es <= USD {c5['fob_maximo_usd']}"
                continue
            if not c5["C5_margen"]:
                r["muere_en"] = "C5"
                r["motivo"] = f"margen base {c5['escenarios']['base']['margen_pct']}% a ${precio:,} (haría falta FOB <= USD {c5['fob_maximo_usd']})"
                continue
            r["sobrevive"] = True
    return resultados


def resumen(resultados: dict) -> list[str]:
    filas = ["| método | propuestas | guardrail | C1 | C2 | C3 | C4 | C5 = sobreviven | condicionales (FOB) | distintas que sobreviven o quedan condicionales |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for metodo, lista in resultados.items():
        def pasan(etapa):
            orden = ["guardrail", "C1", "C2", "C3", "C4", "C5"]
            return sum(1 for r in lista if not r.get("condicional") and (r["muere_en"] is None or orden.index(r["muere_en"]) > orden.index(etapa)))
        cond = sum(1 for r in lista if r.get("condicional"))
        distintas = len({r["busqueda_ml"] for r in lista if r.get("sobrevive") or r.get("condicional")})
        filas.append(f"| {metodo} | {len(lista)} | " + " | ".join(str(pasan(e) + (cond if e in ("guardrail", "C1", "C2", "C3", "C4") else 0)) for e in ["guardrail", "C1", "C2", "C3", "C4", "C5"]) + f" | {cond} | {distintas} |")
    return filas


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "dev"
    res = embudo(part)
    (RAIZ / f"data/serendipia/embudo_{part}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("\n".join(resumen(res)))
    for metodo, lista in res.items():
        print(f"\n## {metodo}")
        for r in lista:
            estado = "SOBREVIVE" if r.get("sobrevive") else "CONDICIONAL" if r.get("condicional") else f"muere en {r['muere_en']}"
            print(f"  {r['producto']} {r['id']:<3} {estado:<15} {r['que_traer'][:60]:<60} {r.get('motivo', '')}")
