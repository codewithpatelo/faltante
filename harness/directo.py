"""Baseline B3, zero-shot: el mismo modelo lee UN producto y propone qué traer en una sola llamada,
sin personas ni grupos (skills/proponer_directo). Responde si la arquitectura (personas →
segmentos → propuestas) aporta algo frente a preguntarle directamente al LLM. Pasa por el mismo
embudo: el dolor se mide igual que para los demás baselines (en la gente de su producto).

    DEEPSEEK_API_KEY=... python -m harness.directo escala_dev   -> data/serendipia/directo_escala_dev_api.json
"""

from __future__ import annotations

import json
import os
import sys

from harness import dolor as D
from harness.modelo import MODELO, DeepSeek, con_reintento, costo, en_paralelo
from harness.voces import RAIZ, los_mas_informativos, productos, textos_con_id

SKILL = RAIZ / "skills/proponer_directo/SKILL.md"
OPINIONES_QUE_LEE = 60        # las más informativas, más todas las preguntas: lo mismo que leía el paso viejo por producto
MIN_CITAS = 2                 # como toda señal del embudo


def proponer(cliente, pid: str, producto: dict, traza: list) -> list[dict]:
    textos = los_mas_informativos(textos_con_id(producto), OPINIONES_QUE_LEE)
    lineas = "\n".join(f"[{i}] {t[:400]}" for i, t in textos.items())
    prompt = (f"{SKILL.read_text(encoding='utf-8')}\n\n---\n\nPRODUCTO: {producto['titulo']} (búsqueda: {producto['busqueda']})\n\n"
              f"TEXTOS\n{lineas}\n\nRespondé SOLO con el JSON de la salida.")

    def validar(d):
        return {str(k): ["cita textos que no existen o menos de 2", "faltan que_traer o busqueda_ml"]
                for k, o in enumerate(d.get("oportunidades", []))
                if len([c for c in o.get("citas", []) if c in textos]) < MIN_CITAS or not o.get("que_traer") or not o.get("busqueda_ml")}
    ops = con_reintento(cliente, prompt, validar, traza, f"B3 {pid}").get("oportunidades", [])
    return [{**o, "id": f"B3.{pid}.{k}", "producto": pid} for k, o in enumerate(ops)
            if len([c for c in o.get("citas", []) if c in textos]) >= MIN_CITAS and o.get("que_traer") and o.get("busqueda_ml")]


def correr(cliente, particion: str) -> dict:
    traza, todos = [], productos()
    from harness.personas import personas_de_la_particion
    tarjetas = {t["id"]: t for t in personas_de_la_particion(cliente, particion, traza)["tarjetas"]}
    ps = productos(particion)
    ops = [o for lista in en_paralelo(lambda pid: proponer(cliente, pid, ps[pid], traza), list(ps)) for o in lista]
    dolor = D.medir_y_decidir(cliente, [(D.enunciado(o), {o["producto"]}) for o in ops], tarjetas, todos, traza)
    return {"quien": MODELO, "costo": costo(traza), "traza": traza, "oportunidades": ops, "dolor": dolor}


if __name__ == "__main__":
    particion = sys.argv[1] if len(sys.argv) > 1 else "escala_dev"
    salida = correr(DeepSeek(os.environ["DEEPSEEK_API_KEY"]), particion)
    destino = RAIZ / f"data/serendipia/directo_{particion}_api.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{destino.relative_to(RAIZ)}: {salida['costo']}, {len(salida['oportunidades'])} oportunidades")
