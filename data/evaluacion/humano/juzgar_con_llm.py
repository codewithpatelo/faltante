"""Hace juzgar a un LLM las mismas 80 filas que las planillas humanas, con los jueces del embudo.

    MODELO_JUEZ=claude-sonnet-5-5 python data/evaluacion/humano/juzgar_con_llm.py  -> data/evaluacion/humano/jueces_llm.json

Usa los mismos prompts que el programa: el de dolor (harness/dolor.py, skills/medir_dolor) y el de
equivalencia (harness/equivalencias.py, skills/juzgar_equivalencia). Una fila de dolor es "desatendida"
(sí) si el modelo dice que la persona tiene el dolor y no lo resolvió. Una fila de equivalencia es sí
si el modelo marca esa publicación como equivalente.

Diferencias con la corrida real, para tenerlas presentes al leer la calibración:
  - las filas se agrupan por dolor (o por propuesta), no por búsqueda completa: el juez de
    equivalencia ve solo las publicaciones de la muestra, no las 50 de la búsqueda;
  - el dolor de la planilla es "trabajo / obstáculo" en un texto: se parte en el primer " / " y falta
    "qué hace mal lo que usan hoy" (queda vacío).

Cada corrida agrega el resultado de ese modelo a jueces_llm.json (lo lee calibrar.py).
"""
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ))
from harness import dolor as D  # noqa: E402
from harness.equivalencias import juzgar  # noqa: E402
from harness.modelo import cliente_llm, costos, en_paralelo  # noqa: E402

ARCHIVO = AQUI / "jueces_llm.json"


def filas_de_la_planilla() -> list[dict]:
    import csv
    return [{k: r[k] for k in ("id", "tipo", "a", "b")}
            for r in csv.DictReader(open(AQUI / "planilla_dario.csv", encoding="utf-8"))]   # el contenido es el mismo en todas


def juzgar_dolor(cliente, filas: list[dict], traza: list) -> dict[str, bool]:
    por_dolor: dict[str, list[dict]] = {}
    for f in filas:
        por_dolor.setdefault(f["a"], []).append(f)

    def uno(par):
        a, grupo = par
        trabajo, _, obstaculo = a.partition(" / ")
        tienen, resuelto = D.leer_textos(cliente, {"id": f"humano.{grupo[0]['id']}", "trabajo": trabajo, "obstaculo": obstaculo},
                                         {f["id"]: f["b"] for f in grupo}, traza)
        return {f["id"]: f["id"] in tienen and f["id"] not in resuelto for f in grupo}

    return {k: v for parcial in en_paralelo(uno, list(por_dolor.items())) for k, v in parcial.items()}


def juzgar_equivalencia(cliente, filas: list[dict], traza: list) -> dict[str, bool]:
    por_propuesta: dict[str, list[dict]] = {}
    for f in filas:
        por_propuesta.setdefault(f["a"], []).append(f)

    def uno(par):
        a, grupo = par
        m = re.match(r"^(.*) \(para: (.*)\)$", a, re.S)
        que_traer, para_que = (m.group(1), m.group(2)) if m else (a, "")
        publicaciones = [{"titulo": f["b"]} for f in grupo]
        equivalentes = set(juzgar(cliente, que_traer, para_que, publicaciones, traza))
        return {f["id"]: f["b"] in equivalentes for f in grupo}

    return {k: v for parcial in en_paralelo(uno, list(por_propuesta.items())) for k, v in parcial.items()}


if __name__ == "__main__":
    import os
    if not os.environ.get("MODELO_JUEZ"):
        raise SystemExit("falta MODELO_JUEZ=<modelo>")
    cliente, traza = cliente_llm(variable="MODELO_JUEZ"), []
    filas = filas_de_la_planilla()
    juicios = {**juzgar_dolor(cliente, [f for f in filas if f["tipo"] == "dolor"], traza),
               **juzgar_equivalencia(cliente, [f for f in filas if f["tipo"] == "equivalencia"], traza)}
    todos = json.loads(ARCHIVO.read_text(encoding="utf-8")) if ARCHIVO.exists() else {}
    ARCHIVO.write_text(json.dumps({**todos, cliente.modelo: dict(sorted(juicios.items()))}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{cliente.modelo}: {len(juicios)} filas juzgadas, {costos({cliente.modelo: traza})}")
