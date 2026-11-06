"""La divergencia: el LLM propone, en dos pasos.

    A · por producto  (skills/leer_voces)     lee la elección en la búsqueda y las voces, y
                                               devuelve SEÑALES citando textos.
    B · entre todos   (skills/cruzar_senales)  recibe las señales verificadas de todos los
                                               productos y propone OPORTUNIDADES que conectan
                                               señales de al menos 2 productos distintos, en dos
                                               tandas (la segunda, distinta de la primera). Cómo
                                               trabajar sale del espacio de prompts y su
                                               optimización (skills/cruzar_senales/como_trabajar.md).

Mirar un producto solo da ideas obvias (su repuesto, su versión mejorada); lo no obvio sale de
cruzar. En los dos pasos el guardrail (código) revisa lo que cita el LLM y, si hay errores, se
los devuelve una vez para que corrija; lo que sigue mal se descarta en el embudo.

    DEEPSEEK_API_KEY=... python -m harness.divergente test   -> data/serendipia/divergente_test_api.json
"""

from __future__ import annotations

import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from harness.chequeos import errores_de_citas, es_verificada, medir
from harness.voces import RAIZ, los_mas_informativos, productos, textos_con_id

MODELO = "deepseek-flash"                                     # DeepSeek-V4.1-Flash
USD_POR_MILLON_DE_TOKENS = {"entrada": 0.30, "salida": 1.20}  # precio en hora pico (fuera de pico, la mitad); api-docs.deepseek.com
URL_API = "https://api.deepseek.com/chat/completions"
OPINIONES_QUE_LEE = 22            # además de todas las preguntas
ALTERNATIVAS_QUE_VE = 6           # de cada lado: las más elegidas y las que se dejaron pasar
MAX_TOKENS_DE_SALIDA = 128000     # DeepSeek Flash razona antes de responder: el paso B con ~250 señales gastó 32.000
                                  # razonando y no llegó a responder (el modelo admite hasta 384.000)
REINTENTOS = 1                    # devolver los errores del guardrail al modelo una vez
EN_PARALELO = 8                   # llamadas simultáneas a la API
SEGUNDOS_POR_LLAMADA = 1800       # razona a ~150 tokens por segundo: 128.000 tokens son ~15 minutos
INTENTOS_DE_RED = 3               # una corrida larga no se cae por un corte de red (al conectar o a mitad de la respuesta)
SKILL_A = RAIZ / "skills/leer_voces/SKILL.md"
SKILL_B = RAIZ / "skills/cruzar_senales/SKILL.md"
# Cómo trabajar en el paso B, congelado antes de test: la ronda 2 de harness/optimizar_prompt.py
# sobre escala_dev (data/serendipia/optimizacion_escala_dev.json), la única que mejoró.
COMO_TRABAJAR_B = RAIZ / "skills/cruzar_senales/como_trabajar.md"
REPREGUNTAR = True                # pedir una segunda tanda distinta: la decisión que más rindió en dev y en escala_dev


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


def señales_de_la_particion(cliente, particion: str, capturas: dict, traza: list) -> dict[str, list]:
    """Paso A sobre cada producto de la partición, en paralelo: {"E001": [señales], ...}."""
    elegidos = productos(particion)
    leer = lambda pid: señales_de(cliente, elegidos[pid], eleccion_en_la_busqueda(elegidos[pid], capturas.get(elegidos[pid]["busqueda"])), traza)
    with ThreadPoolExecutor(EN_PARALELO) as hilos:
        return dict(zip(elegidos, hilos.map(leer, elegidos)))


def señales_del_paso_a(cliente, particion: str, capturas: dict, traza: list) -> dict[str, list]:
    """Las señales del paso A se calculan una vez por partición y se guardan: los experimentos
    de prompts del paso B parten de las mismas, y si el paso B falla no se vuelve a leer todo."""
    archivo = RAIZ / f"data/serendipia/señales_{particion}_api.json"
    if archivo.exists():
        return json.loads(archivo.read_text(encoding="utf-8"))
    señales = señales_de_la_particion(cliente, particion, capturas, traza)
    archivo.write_text(json.dumps(señales, ensure_ascii=False, indent=1), encoding="utf-8")
    return señales


def señales_de(cliente, producto: dict, eleccion: str, traza: list) -> list[dict]:
    textos = textos_con_id(producto)
    validar = lambda d: {s.get("id"): e for s in d.get("señales", []) if (e := errores_de_citas(s, textos))}
    return _con_reintento(cliente, prompt_a(producto, eleccion), validar, traza, f"A {producto['id']}").get("señales", [])


# --- Paso B: oportunidades que cruzan productos -----------------------------------------------

def lineas_de_señales(verificadas: list[dict]) -> str:
    return "\n".join(f"[{s['id']}] ({s['busqueda']} · {s['menciones']} textos) {s.get('tipo', '')}: {s['descripcion']}"
                     f" — \"{s['cita'][:120]}\"" for s in verificadas)


def prompt_b(verificadas: list[dict], instrucciones: str | None = None) -> str:
    """La skill (qué devolver y qué chequea el programa), cómo trabajar y las señales.
    `instrucciones` reemplaza a las congeladas para probar otras (harness/explorar_prompts.py)."""
    return "\n\n".join((SKILL_B.read_text(encoding="utf-8"), "## Cómo trabajar en esta corrida",
                        instrucciones or COMO_TRABAJAR_B.read_text(encoding="utf-8"), "---", "SEÑALES VERIFICADAS",
                        lineas_de_señales(verificadas), "Respondé SOLO con el JSON de la salida."))


def proponer(cliente, verificadas: list[dict], traza: list, instrucciones: str | None = None,
             repreguntar: bool = REPREGUNTAR, etiqueta: str = "B") -> list[dict]:
    """Paso B completo: una tanda de oportunidades y, si `repreguntar`, otra distinta de la primera."""
    prompt = prompt_b(verificadas, instrucciones)
    ops = cruzar(cliente, verificadas, traza, prompt, etiqueta)
    if repreguntar and ops:
        previas = "\n".join(f"- {o.get('que_traer', '')}" for o in ops)
        otra = f"{prompt}\n\nYa propusiste estas:\n{previas}\nProponé hasta 5 MÁS, distintas de todas estas."
        ops += [{**o, "id": f"{o.get('id', 'O')}b"} for o in cruzar(cliente, verificadas, traza, otra, f"{etiqueta} otra")]
    return ops


def errores_de_cruce(oportunidad: dict, ids: set[str]) -> list[str]:
    """Guardrail del paso B: las señales citadas existen y vienen de 2 o más productos."""
    citadas = oportunidad.get("señales") or []
    errores = [f"cita una señal que no existe o no está verificada: {i}" for i in citadas if i not in ids]
    if len({i.split(".")[0] for i in citadas if i in ids}) < 2:
        errores.append("tiene que conectar señales de al menos 2 productos distintos")
    return errores


def cruzar(cliente, verificadas: list[dict], traza: list, prompt: str, etiqueta: str) -> list[dict]:
    """Una llamada del paso B, con el guardrail del cruce y un reintento."""
    ids = {s["id"] for s in verificadas}
    validar = lambda d: {o.get("id"): e for o in d.get("oportunidades", []) if (e := errores_de_cruce(o, ids))}
    return _con_reintento(cliente, prompt, validar, traza, etiqueta).get("oportunidades", [])


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

class RespuestaCortada(RuntimeError):
    """Una respuesta cortada por el tope de tokens no es "cero oportunidades": la corrida se detiene."""


def _con_reintento(cliente, prompt: str, validar, traza: list, etiqueta: str) -> dict:
    mensajes = [{"role": "user", "content": prompt}]
    salida = {}
    for intento in range(REINTENTOS + 1):
        inicio = time.time()
        respuesta = cliente.messages.create(model=MODELO, max_tokens=MAX_TOKENS_DE_SALIDA, messages=mensajes)
        if getattr(respuesta, "stop_reason", None) == "length":
            raise RespuestaCortada(f"{etiqueta}: el modelo usó los {MAX_TOKENS_DE_SALIDA} tokens de salida sin terminar de responder")
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
        for intento in range(INTENTOS_DE_RED):
            try:
                with urllib.request.urlopen(pedido, timeout=SEGUNDOS_POR_LLAMADA) as r:
                    d = json.loads(r.read())
                break
            except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ConnectionError, json.JSONDecodeError):
                if intento == INTENTOS_DE_RED - 1:
                    raise
                time.sleep(30 * (intento + 1))
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
    """Paso A sobre cada producto de la partición (o sus señales ya guardadas) y paso B sobre
    todas las señales verificadas."""
    todos, traza = productos(), []
    señales = señales_del_paso_a(cliente, particion, capturas, traza)
    verificadas = señales_verificadas(señales, todos)
    oportunidades = proponer(cliente, verificadas, traza) if verificadas else []
    return {"quien": MODELO, "costo": costo(traza), "traza": traza, "señales": señales, "oportunidades": oportunidades}


if __name__ == "__main__":
    from harness.correr import busquedas_capturadas
    particion = sys.argv[1] if len(sys.argv) > 1 else "test"
    salida = divergir(DeepSeek(os.environ["DEEPSEEK_API_KEY"]), particion, busquedas_capturadas())
    destino = RAIZ / f"data/serendipia/divergente_{particion}_api.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{destino.relative_to(RAIZ)}: {salida['costo']}, {len(salida['oportunidades'])} oportunidades")
