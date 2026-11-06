"""Paso D: el dolor antes que el producto.

Para cada segmento, el LLM formula hipótesis de dolor (skills/hipotesis_de_dolor): qué trabajo
intenta hacer esa gente, qué se lo impide, con qué lo resuelve hoy y qué hace mal esa solución.
Después otro modelo, que solo ve el dolor y los textos originales (skills/medir_dolor), cuenta
quién lo tiene: en el segmento y en un grupo de control tomado al azar del resto de la gente.
Quien propone no es quien mide. El código decide si el dolor sobrevive; solo los que sobreviven
pasan al paso B (proponer qué traer).

Lo que importa son los DESATENDIDOS: quienes tienen el dolor y no lo resolvieron. Las opiniones
son de compradores de la solución actual y la mayoría suele estar conforme; eso no refuta el dolor,
dice para quién funciona esa solución. El agujero está en la gente a la que le falla.

Cada dolor se mide en tres grupos del mismo tamaño: el segmento, un control y un placebo (los dos
últimos, gente al azar de fuera del segmento). La decisión es una prueba estadística, no un umbral
a ojo: test exacto de Fisher (unilateral) de que el dolor es más frecuente en el segmento que en el
control, con el nivel de significancia corregido por Benjamini-Hochberg sobre todos los dolores de
la corrida. El placebo contra el control mide cuántos falsos positivos da el procedimiento (tendría
que rondar el nivel de significancia).

Un dolor se refuta si:
    no es más frecuente en el segmento que en el control       (Fisher sobre quienes lo tienen)
    la solución actual le sirve al segmento                    (Fisher sobre los desatendidos): sin
                                                               agujero para algo mejor; queda para la
                                                               rama "más barato o más accesible"
    los desatendidos son de un solo producto                   (definición: es el defecto de ese
                                                               producto, no un dolor del grupo)
"""

from __future__ import annotations

import json
import random
from collections import Counter

from scipy.stats import fisher_exact

from harness.modelo import con_reintento, en_paralelo
from harness.voces import RAIZ, textos_con_id

SKILL_D = RAIZ / "skills/hipotesis_de_dolor/SKILL.md"
SKILL_MEDIR = RAIZ / "skills/medir_dolor/SKILL.md"
NIVEL_DE_SIGNIFICANCIA = 0.05        # convención estadística; se corrige por la cantidad de dolores probados
MIN_PRODUCTOS_CON_DESATENDIDOS = 2    # definición: si no, es el defecto de un producto
DESATENDIDOS_POR_PRODUCTO = 2         # el embudo pide 2 textos por señal (harness/chequeos.errores_de_citas)
PERSONAS_MEDIDAS = 150                # del segmento y del control (al azar, con semilla fija, si hay más)
PERSONAS_POR_LLAMADA_AL_MEDIR = 75
SEMILLA = 7


def proponer_dolores(cliente, mapa: dict, traza: list) -> list[dict]:
    prompt = (f"{SKILL_D.read_text(encoding='utf-8')}\n\n---\n\nMAPA DE EMPATÍA DEL SEGMENTO\n"
              f"{json.dumps(mapa, ensure_ascii=False, indent=1)}\n\nRespondé SOLO con el JSON de la salida.")
    validar = lambda d: {} if all(x.get("trabajo") and x.get("obstaculo") for x in d.get("dolores", [])) else {"dolores": ["falta trabajo u obstáculo"]}
    return [{**x, "id": f"{mapa['segmento']}.{x.get('id', 'D')}"}
            for x in con_reintento(cliente, prompt, validar, traza, f"D {mapa['segmento']}").get("dolores", [])
            if x.get("trabajo") and x.get("obstaculo")]


def texto_original(t: dict, todos: dict) -> str:
    return textos_con_id(todos[t["producto"]]).get(t["texto"], "")[:400]


def medir(cliente, dolor: dict, gente: list[dict], todos: dict, traza: list) -> dict:
    """Quién de `gente` tiene el dolor y quién lo resolvió, leyendo sus textos originales."""
    enunciado = (f"Trabajo: {dolor['trabajo']}\nObstáculo: {dolor['obstaculo']}\n"
                 f"Qué hace mal lo que usan hoy: {dolor.get('que_hace_mal', '')}")
    tandas = [gente[i:i + PERSONAS_POR_LLAMADA_AL_MEDIR] for i in range(0, len(gente), PERSONAS_POR_LLAMADA_AL_MEDIR)]

    def una_tanda(tanda):
        ids = {t["id"] for t in tanda}
        lineas = "\n".join(f"[{t['id']}] {texto_original(t, todos)}" for t in tanda)
        prompt = (f"{SKILL_MEDIR.read_text(encoding='utf-8')}\n\n---\n\nDOLOR\n{enunciado}\n\nTEXTOS\n{lineas}\n\n"
                  "Respondé SOLO con el JSON de la salida.")
        d = con_reintento(cliente, prompt, lambda d: {}, traza, f"medir {dolor['id']}", pensar=False)
        tienen = {i for i in d.get("tienen", []) if i in ids}
        return tienen, {i for i in d.get("resuelto", []) if i in tienen}

    partes = en_paralelo(una_tanda, tandas)
    return {"medidas": len(gente), "tienen": sorted(set().union(*[p[0] for p in partes])) if partes else [],
            "resuelto": sorted(set().union(*[p[1] for p in partes])) if partes else []}


def desatendidos(medicion: dict) -> list[str]:
    return [i for i in medicion["tienen"] if i not in set(medicion["resuelto"])]


def p_mas_frecuente(casos: int, medidas: int, casos_ref: int, medidas_ref: int) -> float:
    """Fisher exacto unilateral: ¿la proporción es mayor que en el grupo de referencia?"""
    if medidas == 0 or medidas_ref == 0:
        return 1.0
    return float(fisher_exact([[casos, medidas - casos], [casos_ref, medidas_ref - casos_ref]], alternative="greater")[1])


def benjamini_hochberg(p: list[float], nivel: float = NIVEL_DE_SIGNIFICANCIA) -> list[bool]:
    """Cuáles p-valores son significativos controlando la tasa de falsos descubrimientos."""
    orden = sorted(range(len(p)), key=lambda i: p[i])
    k = max((r + 1 for r, i in enumerate(orden) if p[i] <= (r + 1) / len(p) * nivel), default=0)
    significativos = set(orden[:k])
    return [i in significativos for i in range(len(p))]


def pruebas(m: dict) -> dict:
    """Los p-valores de un dolor medido: segmento y placebo contra control."""
    seg, ctrl, plac = m["segmento"], m["control"], m["placebo"]
    n = lambda g: len(g["tienen"])
    d = lambda g: len(desatendidos(g))
    return {"p_tienen": p_mas_frecuente(n(seg), seg["medidas"], n(ctrl), ctrl["medidas"]),
            "p_desatendidos": p_mas_frecuente(d(seg), seg["medidas"], d(ctrl), ctrl["medidas"]),
            "p_placebo": p_mas_frecuente(d(plac), plac["medidas"], d(ctrl), ctrl["medidas"])}


def decidir(dolores: list[dict], tarjetas: dict) -> dict:
    """Pone el veredicto a todos los dolores de la corrida juntos (la corrección es sobre todos) y
    devuelve la tasa de falsos positivos del placebo."""
    ps = [pruebas(x["medicion"]) for x in dolores]
    tiene_sig = benjamini_hochberg([p["p_tienen"] for p in ps])
    desat_sig = benjamini_hochberg([p["p_desatendidos"] for p in ps])
    for x, p, t, dsig in zip(dolores, ps, tiene_sig, desat_sig):
        seg = x["medicion"]["segmento"]
        sin_resolver = desatendidos(seg)
        productos = sum(k >= DESATENDIDOS_POR_PRODUCTO for k in Counter(tarjetas[i]["producto"] for i in sin_resolver).values())
        datos = {"personas": len(seg["tienen"]), "desatendidos": len(sin_resolver), "de": seg["medidas"],
                 "en_el_control": len(x["medicion"]["control"]["tienen"]), **{k: round(v, 4) for k, v in p.items()},
                 "productos_con_desatendidos": productos}
        if not t:
            v = {"pasa": False, "motivo": "no es más frecuente en el segmento que en el control (Fisher, corregido)"}
        elif not dsig:
            v = {"pasa": False, "rama": "precio_o_acceso", "motivo": "la solución actual le sirve al segmento: sin agujero para algo mejor"}
        elif productos < MIN_PRODUCTOS_CON_DESATENDIDOS:
            v = {"pasa": False, "motivo": "los desatendidos son de un solo producto: es el defecto de ese producto"}
        else:
            v = {"pasa": True, "motivo": f"{len(sin_resolver)} desatendidos de {seg['medidas']}, contra "
                                         f"{len(desatendidos(x['medicion']['control']))} en el control (p = {p['p_desatendidos']:.4f})"}
        x["veredicto"] = {**v, **datos}
    falsos = sum(p["p_placebo"] <= NIVEL_DE_SIGNIFICANCIA for p in ps)
    return {"dolores": len(dolores), "placebo_significativos": falsos,
            "tasa_de_falsos_positivos_del_placebo": round(falsos / max(1, len(ps)), 3)}


def muestra(gente: list[dict], n: int, etiqueta: str) -> list[dict]:
    return gente if len(gente) <= n else random.Random(f"{SEMILLA}{etiqueta}").sample(gente, n)


def dolores_del_segmento(cliente, mapa: dict, miembros: dict, tarjetas: dict, todos: dict, traza: list) -> list[dict]:
    """Hipótesis de dolor del segmento, cada una medida en el segmento, un control y un placebo
    (gente al azar de fuera del segmento, distinta en cada grupo). El veredicto lo pone `decidir`."""
    del_segmento = muestra(list(miembros.values()), PERSONAS_MEDIDAS, mapa["segmento"])
    afuera = muestra([t for i, t in tarjetas.items() if i not in miembros], 2 * len(del_segmento), f"afuera {mapa['segmento']}")
    control, placebo = afuera[:len(del_segmento)], afuera[len(del_segmento):]
    return [{**d, "medicion": {g: medir(cliente, d, gente, todos, traza)
                               for g, gente in (("segmento", del_segmento), ("control", control), ("placebo", placebo))}}
            for d in proponer_dolores(cliente, mapa, traza)]
