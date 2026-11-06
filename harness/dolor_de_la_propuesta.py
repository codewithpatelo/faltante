"""¿El dolor que dice aliviar la propuesta existe? (prueba, para reemplazar el conteo de palabras de C1 y C2)

C1 y C2 cuentan las palabras clave que eligió el mismo LLM que propuso: una necesidad pasa por
estar bien redactada. Acá el dolor de cada propuesta (para quién, qué alivia, por qué nadie lo
atiende) lo mide otro modelo que no sabe qué se propone ni quién lo propuso (skills/medir_dolor),
leyendo los textos originales de la gente de los productos que cita la propuesta y de un grupo de
control al azar de los demás productos. Decide una prueba, no un umbral:

    los desatendidos (tienen el dolor y no lo resolvieron) son más frecuentes que en el control
        Fisher exacto unilateral, con Benjamini-Hochberg sobre todas las propuestas de la corrida
    los desatendidos aparecen en al menos 2 productos (definición: si no, es el defecto de uno)

    DEEPSEEK_API_KEY=... python -m harness.dolor_de_la_propuesta data/evaluacion/versiones_escala_dev/eval-personas-libres_*.json
        -> resultados/dolor_<archivo>.json
"""

from __future__ import annotations

import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

from harness.modelo import DeepSeek, costo, en_paralelo
from harness.voces import RAIZ, productos

from harness.dolores import (DESATENDIDOS_POR_PRODUCTO, MIN_PRODUCTOS_CON_DESATENDIDOS, PERSONAS_MEDIDAS,
                                      SEMILLA, benjamini_hochberg, desatendidos, medir, p_mas_frecuente)


def enunciado(o: dict) -> dict:
    return {"id": o["id"], "trabajo": o.get("para_quien", ""), "obstaculo": o.get("alivia", ""),
            "que_hace_mal": o.get("por_que", "")}


def medir_propuesta(cliente, o: dict, tarjetas: dict, todos: dict, traza: list) -> dict:
    citados = {tarjetas[i]["producto"] for i in o.get("personas", []) if i in tarjetas}
    azar = random.Random(f"{SEMILLA}{o['id']}")
    de_los_productos = [t for t in tarjetas.values() if t["producto"] in citados]
    resto = [t for t in tarjetas.values() if t["producto"] not in citados]
    grupo = de_los_productos if len(de_los_productos) <= PERSONAS_MEDIDAS else azar.sample(de_los_productos, PERSONAS_MEDIDAS)
    control = azar.sample(resto, min(len(resto), len(grupo)))
    d = enunciado(o)
    return {"id": o["id"], "busqueda_ml": o["busqueda_ml"], "dolor": d,
            "medicion": {"propuesta": medir(cliente, d, grupo, todos, traza),
                         "control": medir(cliente, d, control, todos, traza)}}


def decidir(medidas: list[dict], tarjetas: dict) -> None:
    ps = [p_mas_frecuente(len(desatendidos(m["medicion"]["propuesta"])), m["medicion"]["propuesta"]["medidas"],
                          len(desatendidos(m["medicion"]["control"])), m["medicion"]["control"]["medidas"]) for m in medidas]
    for m, p, sig in zip(medidas, ps, benjamini_hochberg(ps)):
        sin_resolver = desatendidos(m["medicion"]["propuesta"])
        productos_ = sum(k >= DESATENDIDOS_POR_PRODUCTO for k in Counter(tarjetas[i]["producto"] for i in sin_resolver).values())
        m["veredicto"] = {"pasa": bool(sig) and productos_ >= MIN_PRODUCTOS_CON_DESATENDIDOS, "p": round(p, 5),
                          "significativo": bool(sig), "desatendidos": len(sin_resolver),
                          "en_el_control": len(desatendidos(m["medicion"]["control"])), "productos_con_desatendidos": productos_}


if __name__ == "__main__":
    cliente = DeepSeek(os.environ["DEEPSEEK_API_KEY"])
    tarjetas = {t["id"]: t for t in json.loads((RAIZ / "data/serendipia/personas_escala_dev_api.json").read_text(encoding="utf-8"))["tarjetas"]}
    todos = productos()
    salida_dir = RAIZ / "resultados"
    salida_dir.mkdir(exist_ok=True)
    for archivo in sys.argv[1:]:
        corrida, traza = json.loads(Path(archivo).read_text(encoding="utf-8")), []
        medidas = en_paralelo(lambda o: medir_propuesta(cliente, o, tarjetas, todos, traza), corrida["oportunidades"])
        decidir(medidas, tarjetas)
        destino = salida_dir / f"dolor_{Path(archivo).name}"
        destino.write_text(json.dumps({"de": Path(archivo).name, "costo": costo(traza), "medidas": medidas}, ensure_ascii=False), encoding="utf-8")
        print(f"{destino.name}: {costo(traza)}, {sum(m['veredicto']['pasa'] for m in medidas)} de {len(medidas)} pasan")
