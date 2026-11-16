"""La llamada al LLM, igual para todos los pasos: DeepSeek Flash por la API (o Claude, con el SDK de
Anthropic), el guardrail con un reintento (el modelo recibe los errores y corrige una vez) y el costo
de cada llamada."""

from __future__ import annotations

import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

MODELO = "deepseek-flash"                                     # DeepSeek-V4.1-Flash: el modelo con el que se corrió todo
# USD por millón de tokens de entrada y de salida. DeepSeek: precio en hora pico (fuera de pico, la
# mitad), api-docs.deepseek.com. Claude: lista de precios de Anthropic al 2026-11-03; Haiku 5.5 cobra
# 0,50 / 2,50 en las llamadas de más de 100.000 tokens de entrada (acá no pasan de eso).
PRECIOS = {
    "deepseek-flash": {"entrada": 0.30, "salida": 1.20},
    "claude-opus-5-5": {"entrada": 4.00, "salida": 20.00},
    "claude-sonnet-5-5": {"entrada": 2.00, "salida": 10.00},
    "claude-haiku-5-5": {"entrada": 0.10, "salida": 0.50},
}
USD_POR_MILLON_DE_TOKENS = PRECIOS[MODELO]
MODELO_CLAUDE = "claude-opus-5-5"  # el modelo por defecto de Claude si no se pide otro (variable MODELO_LLM)
ESFUERZO_CLAUDE = {True: "high", False: "low"}  # razonar o no: Claude no deja apagar el razonamiento, se baja el esfuerzo
URL_API = "https://api.deepseek.com/chat/completions"
MAX_TOKENS_DE_SALIDA = 128000     # razonando, un paso con cientos de líneas gastó 32.000 sin llegar a responder (el modelo admite 384.000)
REINTENTOS = 1                    # devolver los errores del guardrail al modelo una vez
EN_PARALELO = 8                   # llamadas simultáneas a la API
SEGUNDOS_POR_LLAMADA = 1800       # razona a ~150 tokens por segundo: 128.000 tokens son ~15 minutos
INTENTOS_DE_RED = 3               # una corrida larga no se cae por un corte de red (al conectar o a mitad de la respuesta)


class RespuestaCortada(RuntimeError):
    """Una respuesta cortada por el tope de tokens no es "no encontré nada": la corrida se detiene."""


class RespuestaRechazada(RuntimeError):
    """Claude puede negarse a responder (stop_reason "refusal"): tampoco es "no encontré nada"."""


def con_reintento(cliente, prompt: str, validar, traza: list, etiqueta: str, pensar: bool = True) -> dict:
    """Pide un JSON; si `validar` devuelve errores, se los manda al modelo una vez para que corrija.
    `pensar`: razonar antes de responder (para leer y clasificar textos no hace falta)."""
    mensajes = [{"role": "user", "content": prompt}]
    salida = {}
    for intento in range(REINTENTOS + 1):
        inicio = time.time()
        respuesta = cliente.messages.create(model=getattr(cliente, "modelo", MODELO), max_tokens=MAX_TOKENS_DE_SALIDA,
                                            messages=mensajes, pensar=pensar)
        if getattr(respuesta, "stop_reason", None) == "length":
            raise RespuestaCortada(f"{etiqueta}: el modelo usó los {MAX_TOKENS_DE_SALIDA} tokens de salida sin terminar de responder")
        if getattr(respuesta, "stop_reason", None) == "refusal":
            raise RespuestaRechazada(f"{etiqueta}: el modelo se negó a responder")
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


def costo(traza: list, modelo: str = MODELO) -> dict:
    """USD de una traza; `modelo` es con el que se hicieron las llamadas (para Claude, `cliente.modelo`)."""
    precio = PRECIOS[modelo]
    entrada = sum(t["tokens"]["entrada"] for t in traza)
    salida = sum(t["tokens"]["salida"] for t in traza)
    usd = entrada / 1e6 * precio["entrada"] + salida / 1e6 * precio["salida"]
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

    modelo = MODELO

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


class Claude:
    """Cliente de Claude con el SDK oficial de Anthropic, con la misma forma que `DeepSeek`.
    La credencial la resuelve el SDK (ANTHROPIC_API_KEY, o el perfil de `ant auth login`).
    Claude no deja apagar el razonamiento ni fijar la temperatura: `pensar` se traduce en el
    esfuerzo (ESFUERZO_CLAUDE). Va por streaming porque el tope de salida es muy grande."""

    def __init__(self, modelo: str = MODELO_CLAUDE, api=None):
        if modelo not in PRECIOS or not modelo.startswith("claude-"):
            raise ValueError(f"modelo de Claude desconocido: {modelo} (los que tienen precio: {[m for m in PRECIOS if m.startswith('claude-')]})")
        if api is None:
            import anthropic   # acá y no arriba: correr el embudo y los tests no necesita el SDK
            api = anthropic.Anthropic(max_retries=INTENTOS_DE_RED, timeout=SEGUNDOS_POR_LLAMADA)
        self.modelo, self.api, self.messages = modelo, api, self

    def create(self, model: str, max_tokens: int, messages: list[dict], pensar: bool = True):
        with self.api.messages.stream(model=self.modelo, max_tokens=max_tokens, messages=messages,
                                      output_config={"effort": ESFUERZO_CLAUDE[pensar]}) as flujo:
            r = flujo.get_final_message()
        texto = "".join(b.text for b in r.content if b.type == "text")   # antes del texto puede venir un bloque de razonamiento
        return SimpleNamespace(content=[SimpleNamespace(text=texto)],
                               stop_reason={"max_tokens": "length"}.get(r.stop_reason, r.stop_reason),
                               usage=SimpleNamespace(input_tokens=r.usage.input_tokens, output_tokens=r.usage.output_tokens))


def sufijo(modelo: str, juez: str | None = None) -> str:
    """Para que una corrida con otro modelo no pise los archivos de DeepSeek: nada para DeepSeek Flash,
    `__<modelo>` para el resto (`divergente_escala_dev_api__claude-opus-5-5.json`), y `__juez-<modelo>`
    si quien juzgó no es quien propuso (`..._api__juez-claude-sonnet-5-5.json`)."""
    s = "" if modelo == MODELO else f"__{modelo}"
    return s + (f"__juez-{juez}" if juez and juez != modelo else "")


def costos(trazas: dict[str, list]) -> dict:
    """El costo de una corrida a partir de la traza de cada modelo. Con un solo modelo es `costo`, igual
    que siempre; con dos suma y agrega `por_modelo` (el precio de cada uno es el suyo)."""
    por = {m: costo(t, m) for m, t in trazas.items()}
    if len(por) == 1:
        return next(iter(por.values()))
    return {"tokens_entrada": sum(c["tokens_entrada"] for c in por.values()),
            "tokens_salida": sum(c["tokens_salida"] for c in por.values()),
            "usd": round(sum(c["usd"] for c in por.values()), 4),
            "segundos": round(sum(c["segundos"] for c in por.values()), 1), "por_modelo": por}


def cliente_llm(modelo: str | None = None, variable: str = "MODELO_LLM"):
    """El cliente del modelo pedido, o el de la variable de entorno, o DeepSeek Flash (con lo que se corrió todo)."""
    modelo = modelo or os.environ.get(variable) or MODELO
    if modelo.startswith("claude-"):
        return Claude(modelo)
    if modelo != MODELO:
        raise ValueError(f"modelo desconocido: {modelo}")
    return DeepSeek(os.environ["DEEPSEEK_API_KEY"])


def clientes():
    """(quien propone, quien juzga). Juzga el de MODELO_JUEZ si está y es otro modelo; si no, el mismo cliente:
    la regla de fondo del proyecto es que quien propone no mide, así que conviene que sean de familias distintas."""
    propone = cliente_llm()
    juzga = cliente_llm(variable="MODELO_JUEZ") if os.environ.get("MODELO_JUEZ") else propone
    return propone, (propone if juzga.modelo == propone.modelo else juzga)


def juez_para_rejuzgar(particion: str):
    """El juez de `--rejuzgar`: el de MODELO_JUEZ. Test se corre una sola vez, con prerregistro: no se re-juzga."""
    if "test" in particion:
        raise SystemExit(f"{particion}: test se corre una sola vez, con un prerregistro escrito antes (data/evaluacion/test/)")
    if not os.environ.get("MODELO_JUEZ"):
        raise SystemExit("--rejuzgar necesita MODELO_JUEZ=<modelo> (uno que no haya propuesto)")
    return cliente_llm(variable="MODELO_JUEZ")
