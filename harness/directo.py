"""Baselines con el mismo modelo, una sola llamada por producto, sin personas ni grupos:

    B3  zero-shot de generación (skills/proponer_directo): lee las opiniones y propone qué traer;
        sus propuestas pasan por el mismo embudo. Es una ablación: ¿leer personas y grupos genera
        mejores ideas que pedírselas directo al modelo?
    B4  one-shot de punta a punta (skills/recomendar_de_una): lee las opiniones Y lo que hoy se
        ofrece en la búsqueda, aplica él mismo los criterios del embudo y devuelve la
        recomendación final. Es el rival de todo el programa: lo que haría alguien que le pregunta
        al modelo qué importar.

A los dos se les mide el dolor igual que a los demás (en la gente de su producto), para poder
auditarlos con el embudo.

    DEEPSEEK_API_KEY=... python -m harness.directo escala_dev [B3|B4]
        -> data/serendipia/directo_escala_dev_api.json (B3) o de_una_escala_dev_api.json (B4)
"""

from __future__ import annotations

import json
import os
import sys

from harness import dolor as D
from harness.modelo import MODELO, DeepSeek, con_reintento, costo, en_paralelo
from harness.voces import RAIZ, los_mas_informativos, productos, textos_con_id

SKILLS = {"B3": RAIZ / "skills/proponer_directo/SKILL.md", "B4": RAIZ / "skills/recomendar_de_una/SKILL.md"}
ARCHIVO = {"B3": "directo", "B4": "de_una"}
OPINIONES_QUE_LEE = 60        # las más informativas, más todas las preguntas: lo mismo que leía el paso viejo por producto
PUBLICACIONES_QUE_VE = 48     # la primera página de la búsqueda, la misma captura que usa el embudo
MIN_CITAS = 2                 # como toda señal del embudo


def lo_que_se_ofrece(producto: dict, capturas: dict) -> str:
    captura = capturas.get(producto["busqueda"])
    if not captura:
        return "(sin captura de la búsqueda)"
    filas = [f"- {x['titulo']} | ${x.get('precio') or '?'} | +{x.get('vendidos', 0)} vendidos"
             f"{' | Compra Internacional' if x.get('internacional') else ''}"
             for x in captura["publicaciones"][:PUBLICACIONES_QUE_VE] if x.get("titulo")]
    return f"{captura.get('total') or ''}\n" + "\n".join(filas)


def proponer(cliente, pid: str, producto: dict, traza: list, metodo: str = "B3", capturas: dict | None = None) -> list[dict]:
    textos = los_mas_informativos(textos_con_id(producto), OPINIONES_QUE_LEE)
    lineas = "\n".join(f"[{i}] {t[:400]}" for i, t in textos.items())
    mercado = f"\n\nLO QUE HOY SE OFRECE EN LA BÚSQUEDA\n{lo_que_se_ofrece(producto, capturas or {})}" if metodo == "B4" else ""
    prompt = (f"{SKILLS[metodo].read_text(encoding='utf-8')}\n\n---\n\nPRODUCTO: {producto['titulo']} (búsqueda: {producto['busqueda']})\n\n"
              f"TEXTOS\n{lineas}{mercado}\n\nRespondé SOLO con el JSON de la salida.")

    def valida(o):
        return len([c for c in o.get("citas", []) if c in textos]) >= MIN_CITAS and o.get("que_traer") and o.get("busqueda_ml")

    def validar(d):
        return {str(k): ["cita textos que no existen o menos de 2", "faltan que_traer o busqueda_ml"]
                for k, o in enumerate(d.get("oportunidades", [])) if not valida(o)}
    ops = con_reintento(cliente, prompt, validar, traza, f"{metodo} {pid}").get("oportunidades", [])
    return [{**o, "id": f"{metodo}.{pid}.{k}", "producto": pid} for k, o in enumerate(ops) if valida(o)]


def correr(cliente, particion: str, metodo: str = "B3") -> dict:
    traza, todos = [], productos()
    from harness.correr import busquedas_capturadas
    from harness.personas import personas_de_la_particion
    tarjetas = {t["id"]: t for t in personas_de_la_particion(cliente, particion, traza)["tarjetas"]}
    ps, capturas = productos(particion), busquedas_capturadas()
    ops = [o for lista in en_paralelo(lambda pid: proponer(cliente, pid, ps[pid], traza, metodo, capturas), list(ps)) for o in lista]
    dolor = D.medir_y_decidir(cliente, [(D.enunciado(o), {o["producto"]}) for o in ops], tarjetas, todos, traza)
    return {"quien": MODELO, "metodo": metodo, "costo": costo(traza), "traza": traza, "oportunidades": ops, "dolor": dolor}


if __name__ == "__main__":
    particion = sys.argv[1] if len(sys.argv) > 1 else "escala_dev"
    metodo = sys.argv[2] if len(sys.argv) > 2 else "B3"
    salida = correr(DeepSeek(os.environ["DEEPSEEK_API_KEY"]), particion, metodo)
    destino = RAIZ / f"data/serendipia/{ARCHIVO[metodo]}_{particion}_api.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{destino.relative_to(RAIZ)}: {salida['costo']}, {len(salida['oportunidades'])} oportunidades")
