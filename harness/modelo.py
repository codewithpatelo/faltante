"""La llamada al LLM, igual para todos los pasos: DeepSeek Flash por la API, el guardrail con un
reintento (el modelo recibe los errores y corrige una vez) y el costo de cada llamada."""

from __future__ import annotations

import http.client
import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

MODELO = "deepseek-flash"                                     # DeepSeek-V4.1-Flash
USD_POR_MILLON_DE_TOKENS = {"entrada": 0.30, "salida": 1.20}  # precio en hora pico (fuera de pico, la mitad); api-docs.deepseek.com
URL_API = "https://api.deepseek.com/chat/completions"
MAX_TOKENS_DE_SALIDA = 128000     # razonando, un paso con cientos de líneas gastó 32.000 sin llegar a responder (el modelo admite 384.000)
REINTENTOS = 1                    # devolver los errores del guardrail al modelo una vez
EN_PARALELO = 8                   # llamadas simultáneas a la API
SEGUNDOS_POR_LLAMADA = 1800       # razona a ~150 tokens por segundo: 128.000 tokens son ~15 minutos
INTENTOS_DE_RED = 3               # una corrida larga no se cae por un corte de red (al conectar o a mitad de la respuesta)


class RespuestaCortada(RuntimeError):
    """Una respuesta cortada por el tope de tokens no es "no encontré nada": la corrida se detiene."""


def con_reintento(cliente, prompt: str, validar, traza: list, etiqueta: str, pensar: bool = True) -> dict:
    """Pide un JSON; si `validar` devuelve errores, se los manda al modelo una vez para que corrija.
    `pensar`: razonar antes de responder (para leer y clasificar textos no hace falta)."""
    mensajes = [{"role": "user", "content": prompt}]
    salida = {}
    for intento in range(REINTENTOS + 1):
        inicio = time.time()
        respuesta = cliente.messages.create(model=MODELO, max_tokens=MAX_TOKENS_DE_SALIDA, messages=mensajes, pensar=pensar)
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


def en_paralelo(funcion, elementos: list) -> list:
    """Aplica `funcion` a cada elemento con EN_PARALELO llamadas a la vez, conservando el orden."""
    with ThreadPoolExecutor(EN_PARALELO) as hilos:
        return list(hilos.map(funcion, elementos))


def costo(traza: list) -> dict:
    entrada = sum(t["tokens"]["entrada"] for t in traza)
    salida = sum(t["tokens"]["salida"] for t in traza)
    usd = entrada / 1e6 * USD_POR_MILLON_DE_TOKENS["entrada"] + salida / 1e6 * USD_POR_MILLON_DE_TOKENS["salida"]
    return {"tokens_entrada": entrada, "tokens_salida": salida, "usd": round(usd, 4),
            "segundos": round(sum(t["segundos"] for t in traza), 1)}


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

    def create(self, model: str, max_tokens: int, messages: list[dict], pensar: bool = True):
        cuerpo = json.dumps({"model": model, "max_tokens": max_tokens, "messages": messages,
                             "thinking": {"type": "enabled" if pensar else "disabled"},
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
