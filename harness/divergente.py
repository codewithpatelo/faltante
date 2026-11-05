"""El paso del LLM: lee las voces de un producto y propone qué traer, citando textos.

Patrón evaluador-optimizador: el LLM propone, el guardrail (código) revisa las citas, y si
hay errores se los devuelve una vez para que corrija. Lo que sigue mal no se descarta acá:
llega al embudo y se descarta en el guardrail, con el motivo a la vista.

    ANTHROPIC_API_KEY=... python -m harness.divergente test   -> data/serendipia/divergente_test_api.json
"""

from __future__ import annotations

import json
import re
import sys
import time

from harness.chequeos import errores_de_citas
from harness.voces import RAIZ, los_mas_informativos, productos, textos_con_id

MODELO = "claude-haiku-4-5"
USD_POR_MILLON_DE_TOKENS = {"entrada": 1.0, "salida": 5.0}   # Haiku 4.5
OPINIONES_QUE_LEE = 22            # además de todas las preguntas
REINTENTOS = 1
SKILL = RAIZ / "skills/leer_voces/SKILL.md"


def prompt(producto: dict) -> str:
    """El skill + los datos del producto ancla (voto con los pies) + los textos elegidos (voto con las manos)."""
    ancla = (f"PRODUCTO ANCLA: {producto['titulo']} | +{producto['vendidos']} vendidos | ${producto['precio']:,} | "
             f"búsqueda: {producto['busqueda']} | {producto.get('calificacion', '')}")
    textos = los_mas_informativos(textos_con_id(producto), OPINIONES_QUE_LEE)
    lineas = "\n".join(f"[{i}] {t[:300]}" for i, t in textos.items())
    return f"{SKILL.read_text(encoding='utf-8')}\n\n---\n\n{ancla}\n{lineas}\n\nRespondé SOLO con el JSON de la salida."


def proponer(cliente, producto: dict, traza: list) -> dict:
    """{"señales": [...], "oportunidades": [...]} para un producto; deja en `traza` tokens, tiempo y errores."""
    textos = textos_con_id(producto)
    mensajes = [{"role": "user", "content": prompt(producto)}]
    salida = {"señales": [], "oportunidades": []}
    for intento in range(REINTENTOS + 1):
        inicio = time.time()
        respuesta = cliente.messages.create(model=MODELO, max_tokens=3000, messages=mensajes)
        texto = respuesta.content[0].text
        salida = _json(texto)
        errores = {s.get("id"): e for s in salida["señales"] if (e := errores_de_citas(s, textos))}
        traza.append({"producto": producto["id"], "intento": intento, "segundos": round(time.time() - inicio, 2),
                      "tokens": {"entrada": respuesta.usage.input_tokens, "salida": respuesta.usage.output_tokens},
                      "errores": errores})
        if not errores:
            break
        mensajes += [{"role": "assistant", "content": texto},
                     {"role": "user", "content": "El validador rechazó estas citas:\n" + json.dumps(errores, ensure_ascii=False)
                      + "\nCorregí o sacá esas señales. Respondé SOLO con el JSON."}]
    return salida


def costo(traza: list) -> dict:
    entrada = sum(t["tokens"]["entrada"] for t in traza)
    salida = sum(t["tokens"]["salida"] for t in traza)
    usd = entrada / 1e6 * USD_POR_MILLON_DE_TOKENS["entrada"] + salida / 1e6 * USD_POR_MILLON_DE_TOKENS["salida"]
    return {"tokens_entrada": entrada, "tokens_salida": salida, "usd": round(usd, 4),
            "segundos": round(sum(t["segundos"] for t in traza), 1)}


def _json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        d = {}
    return {"señales": d.get("señales", []), "oportunidades": d.get("oportunidades", [])}


if __name__ == "__main__":
    import anthropic
    particion = sys.argv[1] if len(sys.argv) > 1 else "test"
    cliente, traza = anthropic.Anthropic(), []
    por_producto = {pid: proponer(cliente, p, traza) for pid, p in productos(particion).items()}
    destino = RAIZ / f"data/serendipia/divergente_{particion}_api.json"
    destino.write_text(json.dumps({"quien": MODELO, "costo": costo(traza), "traza": traza, "por_producto": por_producto},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{destino.relative_to(RAIZ)}: {costo(traza)}")
