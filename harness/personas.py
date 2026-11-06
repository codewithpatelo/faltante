"""Perfilar a la gente: de cada voz, un mapa de empatía chico; de todas, segmentos de personas
en la misma situación aunque hayan comprado cosas distintas; de cada segmento, su mapa de
empatía con conteos y citas.

    A  tarjetas   (skills/leer_personas)    el LLM lee las voces de cada producto y anota, por
                                             persona: situación, qué quiere lograr, dolor,
                                             ganancia, qué teme, con qué compara y una cita.
    S  segmentos  (skills/agrupar_personas)  el LLM define segmentos por situación y asigna a
                                             cada persona; el programa arma el mapa de empatía
                                             de cada segmento (código, sin LLM).

Las tarjetas y los segmentos se guardan en data/serendipia/personas_<particion>_api.json y se
reusan: si el paso B falla o se cambia, no se vuelve a leer todo.
"""

from __future__ import annotations

import json
import random
from collections import Counter

from harness.modelo import con_reintento, en_paralelo
from harness.voces import RAIZ, productos, sin_acentos, textos_con_id

SKILL_A = RAIZ / "skills/leer_personas/SKILL.md"
SKILL_S = RAIZ / "skills/agrupar_personas/SKILL.md"
MIN_PALABRAS_OPINION = 8          # decisión: "Excelente, llegó rápido" no cuenta nada de quien lo escribe; las preguntas se leen todas
VOCES_POR_LLAMADA = 50
PERSONAS_PARA_DEFINIR = 2500      # las que lee el LLM para definir segmentos (al azar, con semilla fija)
PERSONAS_POR_LLAMADA_AL_ASIGNAR = 150
SEMILLA = 7
MIN_PERSONAS_POR_SEGMENTO = 15    # decisión: un grupo más chico no sostiene un negocio de importación
MIN_BUSQUEDAS_POR_SEGMENTO = 2    # el segmento cruza búsquedas: si no, es "los compradores de X" (los anclas de una búsqueda son casi el mismo producto)
MIN_PERSONAS_POR_BUSQUEDA = 3     # para contar una búsqueda en el segmento
PERSONAS_EN_EL_MAPA = 60          # las que lee el paso B de cada segmento (primero las que tienen dolor o miedo)
ALTERNATIVAS_QUE_VE = 4           # de cada búsqueda: las más elegidas y las que se dejaron pasar
CAMPOS = ("situacion", "quiere_lograr", "dolor", "ganancia", "teme", "compara_con")


# --- A · Una tarjeta por persona -----------------------------------------------------------

def voces_a_leer(producto: dict) -> dict[str, str]:
    return {i: t for i, t in textos_con_id(producto).items()
            if i.startswith("p") or len(t.split()) >= MIN_PALABRAS_OPINION}


def errores_de_tarjeta(tarjeta: dict, voces: dict[str, str]) -> list[str]:
    """Guardrail: la persona existe y la cita está en su texto."""
    texto = voces.get(tarjeta.get("texto"))
    if texto is None:
        return [f"el texto {tarjeta.get('texto')} no está en esta tanda"]
    f = tarjeta.get("fragmento", "")
    if len(f) < 4 or sin_acentos(f) not in sin_acentos(texto):
        return [f"[{tarjeta['texto']}] el fragmento no está en el texto"]
    if not any(tarjeta.get(c) for c in CAMPOS):
        return [f"[{tarjeta['texto']}] no anota nada de la persona"]
    return []


def tarjetas_de_una_tanda(cliente, producto: dict, voces: dict[str, str], traza: list) -> list[dict]:
    lineas = "\n".join(f"[{i}] {t[:400]}" for i, t in voces.items())
    prompt = (f"{SKILL_A.read_text(encoding='utf-8')}\n\n---\n\nPRODUCTO: {producto['titulo']} | búsqueda: "
              f"{producto['busqueda']}\n\nTEXTOS\n{lineas}\n\nRespondé SOLO con el JSON de la salida.")
    validar = lambda d: {t.get("texto"): e for t in d.get("personas", []) if (e := errores_de_tarjeta(t, voces))}
    d = con_reintento(cliente, prompt, validar, traza, f"A {producto['id']}", pensar=False)
    return [{**{c: t.get(c, "") for c in CAMPOS}, "id": f"{producto['id']}.{t['texto']}", "producto": producto["id"],
             "texto": t["texto"], "fragmento": t["fragmento"], "eligio": t["texto"].startswith("o")}
            for t in d.get("personas", []) if not errores_de_tarjeta(t, voces)]


def tarjetas_de_la_particion(cliente, particion: str, traza: list) -> list[dict]:
    tandas = []
    for p in productos(particion).values():
        voces = list(voces_a_leer(p).items())
        tandas += [(p, dict(voces[i:i + VOCES_POR_LLAMADA])) for i in range(0, len(voces), VOCES_POR_LLAMADA)]
    por_tanda = en_paralelo(lambda t: tarjetas_de_una_tanda(cliente, t[0], t[1], traza), tandas)
    vistas = {}
    for t in (t for tanda in por_tanda for t in tanda):
        vistas.setdefault(t["id"], t)         # una persona, una tarjeta
    return list(vistas.values())


# --- S · Segmentos ---------------------------------------------------------------------------

def linea(t: dict) -> str:
    return f"[{t['id']}] {t['situacion']} | {t['quiere_lograr']} | {t['dolor']}"


def linea_con_busqueda(t: dict, todos: dict) -> str:
    """Para definir segmentos el modelo ve de qué búsqueda viene cada persona, y así puede
    juntar situaciones que se repiten en búsquedas distintas."""
    return f"[{t['id']}] ({todos[t['producto']]['busqueda']}) {t['situacion']} | {t['quiere_lograr']} | {t['dolor']}"


def definir_segmentos(cliente, tarjetas: list[dict], traza: list) -> list[dict]:
    todos = productos()
    muestra = random.Random(SEMILLA).sample(tarjetas, min(PERSONAS_PARA_DEFINIR, len(tarjetas)))
    prompt = (f"{SKILL_S.read_text(encoding='utf-8')}\n\n---\n\nTAREA: definir\n\nPERSONAS\n"
              + "\n".join(linea_con_busqueda(t, todos) for t in muestra) + "\n\nRespondé SOLO con el JSON de la tarea \"definir\".")
    validar = lambda d: {} if d.get("segmentos") else {"segmentos": ["no hay segmentos"]}
    return con_reintento(cliente, prompt, validar, traza, "S definir").get("segmentos", [])


def asignar(cliente, segmentos: list[dict], tarjetas: list[dict], traza: list) -> dict[str, str]:
    """{id de persona: id de segmento}. Las que el modelo no asigna, o asigna a un segmento que
    no existe, quedan afuera."""
    ids = {s["id"] for s in segmentos}
    definiciones = "\n".join(f"{s['id']} · {s['nombre']}: {s['quien']} (entra si: {s['criterio']})" for s in segmentos)
    tandas = [tarjetas[i:i + PERSONAS_POR_LLAMADA_AL_ASIGNAR] for i in range(0, len(tarjetas), PERSONAS_POR_LLAMADA_AL_ASIGNAR)]

    def una_tanda(tanda):
        prompt = (f"{SKILL_S.read_text(encoding='utf-8')}\n\n---\n\nTAREA: asignar\n\nSEGMENTOS\n{definiciones}\n\n"
                  "PERSONAS\n" + "\n".join(map(linea, tanda)) + "\n\nRespondé SOLO con el JSON de la tarea \"asignar\".")
        d = con_reintento(cliente, prompt, lambda d: {}, traza, "S asignar", pensar=False)
        de_la_tanda = {t["id"] for t in tanda}
        return {a[0]: a[1] for a in d.get("asignaciones", [])
                if isinstance(a, list) and len(a) == 2 and a[0] in de_la_tanda and a[1] in ids}

    return {k: v for parte in en_paralelo(una_tanda, tandas) for k, v in parte.items()}


def personas_de_la_particion(cliente, particion: str, traza: list) -> dict:
    """Tarjetas, segmentos y asignaciones de la partición; se calculan una vez y se guardan."""
    archivo = RAIZ / f"data/serendipia/personas_{particion}_api.json"
    guardado = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    if "tarjetas" not in guardado:
        guardado["tarjetas"] = tarjetas_de_la_particion(cliente, particion, traza)
        archivo.write_text(json.dumps(guardado, ensure_ascii=False, indent=1), encoding="utf-8")
    if "segmentos" not in guardado:
        segmentos = definir_segmentos(cliente, guardado["tarjetas"], traza)
        guardado |= {"segmentos": segmentos, "asignaciones": asignar(cliente, segmentos, guardado["tarjetas"], traza)}
        archivo.write_text(json.dumps(guardado, ensure_ascii=False, indent=1), encoding="utf-8")
    return guardado


# --- El mapa de empatía de un segmento (código) ----------------------------------------------

def eleccion_en_la_busqueda(captura: dict | None) -> dict:
    """Voto con los pies en una búsqueda: lo que se elige y lo que se ofrece y se deja pasar."""
    if not captura:
        return {"elegidas": [], "dejadas": []}
    pubs = [p for p in captura["publicaciones"] if p.get("precio")]
    fila = lambda p: f"{p['titulo'][:70]} | ${p['precio']:,} | +{p['vendidos']}"
    return {"elegidas": [fila(p) for p in sorted((p for p in pubs if p["vendidos"] >= 100), key=lambda p: -p["vendidos"])[:ALTERNATIVAS_QUE_VE]],
            "dejadas": [fila(p) for p in pubs if p["vendidos"] <= 25 and not p["internacional"]][:ALTERNATIVAS_QUE_VE]}


def mapa_de_empatia(segmento: dict, miembros: list[dict], todos: dict, capturas: dict) -> dict:
    """Lo que el paso B lee del segmento: quiénes son, qué hacen, qué ven, qué dicen y qué temen."""
    por_producto = Counter(t["producto"] for t in miembros)
    por_busqueda = Counter(todos[t["producto"]]["busqueda"] for t in miembros)
    # primero las personas con dolor o miedo, repartidas entre productos
    orden = sorted(miembros, key=lambda t: (not (t["dolor"] or t["teme"]), t["id"]))
    rondas, vistas = {}, []
    for t in orden:
        rondas.setdefault(t["producto"], []).append(t)
    while len(vistas) < min(PERSONAS_EN_EL_MAPA, len(miembros)):
        for pid in list(rondas):
            if rondas[pid] and len(vistas) < PERSONAS_EN_EL_MAPA:
                vistas.append(rondas[pid].pop(0))
    return {"segmento": segmento["id"], "nombre": segmento["nombre"], "quien": segmento["quien"],
            "personas": len(miembros), "compraron": sum(t["eligio"] for t in miembros),
            "dudan": sum(not t["eligio"] for t in miembros),
            "productos": {pid: {"titulo": todos[pid]["titulo"][:70], "vendidos": todos[pid]["vendidos"],
                                "precio": todos[pid]["precio"], "personas": n} for pid, n in por_producto.most_common()},
            "personas_por_busqueda": dict(por_busqueda.most_common()),
            "busquedas": {b: eleccion_en_la_busqueda(capturas.get(b)) for b in sorted(por_busqueda)},
            "cuentan": {c: sum(1 for t in miembros if t[c]) for c in CAMPOS},
            "voces": [{"id": t["id"], **{c: t[c] for c in CAMPOS if t[c]}} for t in vistas]}


def es_segmento_suficiente(mapa: dict) -> bool:
    """Bastante gente, y de varias búsquedas: una situación de vida, no los compradores de un producto."""
    busquedas = sum(n >= MIN_PERSONAS_POR_BUSQUEDA for n in mapa["personas_por_busqueda"].values())
    return mapa["personas"] >= MIN_PERSONAS_POR_SEGMENTO and busquedas >= MIN_BUSQUEDAS_POR_SEGMENTO
