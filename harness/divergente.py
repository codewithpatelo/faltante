"""La divergencia: el LLM propone, en dos pasos.

    A · por producto  (skills/leer_voces)     lee la elección en la búsqueda y las voces, y
                                               devuelve SEÑALES citando textos.
    B · entre todos   (skills/cruzar_senales)  recibe las señales verificadas de todos los
                                               productos y propone OPORTUNIDADES que conectan
                                               señales de al menos 2 productos distintos.

Mirar un producto solo da ideas obvias (su repuesto, su versión mejorada); lo no obvio sale de
cruzar. En los dos pasos el guardrail (código) revisa lo que cita el LLM y, si hay errores, se
los devuelve una vez para que corrija; lo que sigue mal se descarta en el embudo.

    DEEPSEEK_API_KEY=... python -m harness.divergente test   -> data/serendipia/divergente_test_api.json
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from types import SimpleNamespace

from harness.chequeos import errores_de_citas, es_verificada, medir
from harness.voces import RAIZ, los_mas_informativos, productos, textos_con_id

MODELO = "deepseek-flash"                                     # DeepSeek-V4.1-Flash
USD_POR_MILLON_DE_TOKENS = {"entrada": 0.30, "salida": 1.20}  # precio en hora pico (fuera de pico, la mitad); api-docs.deepseek.com
URL_API = "https://api.deepseek.com/chat/completions"
OPINIONES_QUE_LEE = 22            # además de todas las preguntas
ALTERNATIVAS_QUE_VE = 6           # de cada lado: las más elegidas y las que se dejaron pasar
MAX_TOKENS_DE_SALIDA = 32000      # DeepSeek Flash razona antes de responder (hasta ~27.000 caracteres): con 8.000 se cortaba
REINTENTOS = 1
SKILL_A = RAIZ / "skills/leer_voces/SKILL.md"
SKILL_B = RAIZ / "skills/cruzar_senales/SKILL.md"


# --- Paso A: señales de un producto --------------------------------------------------------

def eleccion_en_la_busqueda(producto: dict, captura: dict | None) -> str:
    """El voto con los pies en la búsqueda del producto: qué más se elige y qué se deja pasar."""
    if not captura:
        return "(no hay captura de la búsqueda)"
    pubs = [p for p in captura["publicaciones"] if p.get("precio")]
    elegidas = sorted((p for p in pubs if p["vendidos"] >= 100), key=lambda p: -p["vendidos"])[:ALTERNATIVAS_QUE_VE]
    dejadas = [p for p in pubs if p["vendidos"] <= 25 and not p["internacional"]][:ALTERNATIVAS_QUE_VE]
    fila = lambda p: f"  - {p['titulo'][:80]} | ${p['precio']:,} | +{p['vendidos']}"
    return "\n".join(["Más elegidas en la búsqueda:", *map(fila, elegidas),
                      "Con stock local pero dejadas pasar (casi sin ventas):", *map(fila, dejadas)])


def prompt_a(producto: dict, eleccion: str) -> str:
    ancla = (f"PRODUCTO ANCLA: {producto['titulo']} | +{producto['vendidos']} vendidos | ${producto['precio']:,} | "
             f"búsqueda: {producto['busqueda']} | {producto.get('calificacion') or ''}")
    textos = los_mas_informativos(textos_con_id(producto), OPINIONES_QUE_LEE)
    lineas = "\n".join(f"[{i}] {t[:300]}" for i, t in textos.items())
    return (f"{SKILL_A.read_text(encoding='utf-8')}\n\n---\n\n{ancla}\n\nELECCIÓN\n{eleccion}\n\nVOCES\n{lineas}\n\n"
            "Respondé SOLO con el JSON de la salida.")


def señales_de(cliente, producto: dict, eleccion: str, traza: list) -> list[dict]:
    textos = textos_con_id(producto)
    validar = lambda d: {s.get("id"): e for s in d.get("señales", []) if (e := errores_de_citas(s, textos))}
    return _con_reintento(cliente, prompt_a(producto, eleccion), validar, traza, f"A {producto['id']}").get("señales", [])


# --- Paso B: oportunidades que cruzan productos -----------------------------------------------

def lineas_de_señales(verificadas: list[dict]) -> str:
    return "\n".join(f"[{s['id']}] ({s['busqueda']} · {s['menciones']} textos) {s.get('tipo', '')}: {s['descripcion']}"
                     f" — \"{s['cita'][:120]}\"" for s in verificadas)


def prompt_b(verificadas: list[dict]) -> str:
    return (f"{SKILL_B.read_text(encoding='utf-8')}\n\n---\n\nSEÑALES VERIFICADAS\n{lineas_de_señales(verificadas)}\n\n"
            "Respondé SOLO con el JSON de la salida.")


def errores_de_cruce(oportunidad: dict, ids: set[str]) -> list[str]:
    """Guardrail del paso B: las señales citadas existen y vienen de 2 o más productos."""
    citadas = oportunidad.get("señales") or []
    errores = [f"cita una señal que no existe o no está verificada: {i}" for i in citadas if i not in ids]
    if len({i.split(".")[0] for i in citadas if i in ids}) < 2:
        errores.append("tiene que conectar señales de al menos 2 productos distintos")
    return errores


def cruzar(cliente, verificadas: list[dict], traza: list, prompt: str | None = None, etiqueta: str = "B") -> list[dict]:
    """Paso B. `prompt` permite probar otra variante del prompt (harness/explorar_prompts.py)."""
    ids = {s["id"] for s in verificadas}
    validar = lambda d: {o.get("id"): e for o in d.get("oportunidades", []) if (e := errores_de_cruce(o, ids))}
    return _con_reintento(cliente, prompt or prompt_b(verificadas), validar, traza, etiqueta).get("oportunidades", [])


def señales_verificadas(señales: dict[str, list], todos: dict[str, dict]) -> list[dict]:
    """Las señales del paso A que pasan el guardrail y C1, con ID global ("P12.S2")."""
    salida = []
    for pid, lista in señales.items():
        textos = textos_con_id(todos[pid])
        for s in lista:
            m = medir(s, textos)
            if not errores_de_citas(s, textos) and es_verificada(m):
                salida.append({**s, "id": f"{pid}.{s['id']}", "busqueda": todos[pid]["busqueda"],
                               "menciones": m["menciones"], "cita": (s.get("citas") or [{}])[0].get("fragmento", "")})
    return salida


# --- Llamada al modelo ------------------------------------------------------------------------

def _con_reintento(cliente, prompt: str, validar, traza: list, etiqueta: str) -> dict:
    mensajes = [{"role": "user", "content": prompt}]
    salida = {}
    for intento in range(REINTENTOS + 1):
        inicio = time.time()
        respuesta = cliente.messages.create(model=MODELO, max_tokens=MAX_TOKENS_DE_SALIDA, messages=mensajes)
        texto = respuesta.content[0].text
        salida = _json(texto)
        errores = validar(salida)
        traza.append({"paso": etiqueta, "intento": intento, "segundos": round(time.time() - inicio, 2),
                      "tokens": {"entrada": respuesta.usage.input_tokens, "salida": respuesta.usage.output_tokens},
                      "errores": errores, "corte": getattr(respuesta, "stop_reason", None),
                      **({"respuesta_ilegible": texto[:1500]} if not salida else {})})
        if not errores:
            break
        mensajes += [{"role": "assistant", "content": texto},
                     {"role": "user", "content": "El validador rechazó esto:\n" + json.dumps(errores, ensure_ascii=False)
                      + "\nCorregí o sacá lo rechazado. Respondé SOLO con el JSON."}]
    return salida


def _json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


class DeepSeek:
    """Cliente mínimo de la API de DeepSeek (formato OpenAI). Devuelve la respuesta con la
    misma forma que usa el resto del programa (texto, tokens, motivo de corte)."""

    def __init__(self, clave: str):
        self.clave = clave
        self.messages = self

    def create(self, model: str, max_tokens: int, messages: list[dict]):
        cuerpo = json.dumps({"model": model, "max_tokens": max_tokens, "messages": messages,
                             "response_format": {"type": "json_object"}}).encode()
        pedido = urllib.request.Request(URL_API, data=cuerpo, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self.clave}"})
        with urllib.request.urlopen(pedido, timeout=300) as r:
            d = json.loads(r.read())
        eleccion = d["choices"][0]
        return SimpleNamespace(content=[SimpleNamespace(text=eleccion["message"].get("content") or "")],
                               stop_reason=eleccion.get("finish_reason"),
                               usage=SimpleNamespace(input_tokens=d["usage"]["prompt_tokens"],
                                                     output_tokens=d["usage"]["completion_tokens"]))


def costo(traza: list) -> dict:
    entrada = sum(t["tokens"]["entrada"] for t in traza)
    salida = sum(t["tokens"]["salida"] for t in traza)
    usd = entrada / 1e6 * USD_POR_MILLON_DE_TOKENS["entrada"] + salida / 1e6 * USD_POR_MILLON_DE_TOKENS["salida"]
    return {"tokens_entrada": entrada, "tokens_salida": salida, "usd": round(usd, 4),
            "segundos": round(sum(t["segundos"] for t in traza), 1)}


def divergir(cliente, particion: str, capturas: dict) -> dict:
    """Paso A sobre cada producto de la partición y paso B sobre todas las señales verificadas."""
    todos, traza = productos(), []
    elegidos = productos(particion)
    señales = {pid: señales_de(cliente, p, eleccion_en_la_busqueda(p, capturas.get(p["busqueda"])), traza)
               for pid, p in elegidos.items()}
    verificadas = señales_verificadas(señales, todos)
    oportunidades = cruzar(cliente, verificadas, traza) if verificadas else []
    return {"quien": MODELO, "costo": costo(traza), "traza": traza, "señales": señales, "oportunidades": oportunidades}


if __name__ == "__main__":
    from harness.correr import busquedas_capturadas
    particion = sys.argv[1] if len(sys.argv) > 1 else "test"
    salida = divergir(DeepSeek(os.environ["DEEPSEEK_API_KEY"]), particion, busquedas_capturadas())
    destino = RAIZ / f"data/serendipia/divergente_{particion}_api.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{destino.relative_to(RAIZ)}: {salida['costo']}, {len(salida['oportunidades'])} oportunidades")
