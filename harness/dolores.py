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

Un dolor se refuta si:
    pocas personas lo tienen                       (MIN_PERSONAS_CON_EL_DOLOR)
    no es más frecuente en el segmento que afuera  (MIN_VECES_MAS_QUE_EN_EL_CONTROL)
    la solución actual le sirve a casi todos       (MIN_PERSONAS_DESATENDIDAS): no hay agujero para algo
                                                    mejor; queda marcado para la rama "más barato o más
                                                    accesible" (todavía no construida)
    los desatendidos son de un solo producto       (MIN_PRODUCTOS_CON_DESATENDIDOS, 2 personas en cada uno):
                                                    es el defecto de un producto, no un dolor del grupo
"""

from __future__ import annotations

import json
import random
from collections import Counter

from harness.modelo import con_reintento, en_paralelo
from harness.voces import RAIZ, textos_con_id

SKILL_D = RAIZ / "skills/hipotesis_de_dolor/SKILL.md"
SKILL_MEDIR = RAIZ / "skills/medir_dolor/SKILL.md"
MIN_PERSONAS_CON_EL_DOLOR = 5
MIN_VECES_MAS_QUE_EN_EL_CONTROL = 2.0  # decisión: el dolor es de este grupo, no de todo el mundo
MIN_PERSONAS_DESATENDIDAS = 5         # decisión: menos que esto no sostiene un lote de importación
MIN_PRODUCTOS_CON_DESATENDIDOS = 2    # con al menos 2 desatendidos en cada uno
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


def veredicto(en_segmento: dict, en_control: dict, tarjetas: dict) -> dict:
    """El código decide si el dolor sobrevive, con los números a la vista."""
    tienen, sin_resolver = en_segmento["tienen"], desatendidos(en_segmento)
    proporcion = len(tienen) / max(1, en_segmento["medidas"])
    proporcion_control = len(en_control["tienen"]) / max(1, en_control["medidas"])
    veces = proporcion / proporcion_control if proporcion_control else float("inf") if tienen else 0.0
    productos = sum(n >= 2 for n in Counter(tarjetas[i]["producto"] for i in sin_resolver).values())
    datos = {"personas": len(tienen), "desatendidos": len(sin_resolver), "de": en_segmento["medidas"],
             "proporcion": round(proporcion, 3), "proporcion_control": round(proporcion_control, 3),
             "veces_mas_que_el_control": round(veces, 2) if veces != float("inf") else "sin casos en el control",
             "productos_con_2_desatendidos_o_mas": productos}
    if len(tienen) < MIN_PERSONAS_CON_EL_DOLOR:
        return {"pasa": False, "motivo": f"lo tienen {len(tienen)} personas (mínimo {MIN_PERSONAS_CON_EL_DOLOR})", **datos}
    if veces < MIN_VECES_MAS_QUE_EN_EL_CONTROL:
        return {"pasa": False, "motivo": f"no es de este grupo: {proporcion:.0%} en el segmento contra {proporcion_control:.0%} en el control", **datos}
    if len(sin_resolver) < MIN_PERSONAS_DESATENDIDAS:
        return {"pasa": False, "rama": "precio_o_acceso", **datos,
                "motivo": f"la solución actual le sirve a casi todos ({len(sin_resolver)} desatendidos): sin agujero para algo mejor"}
    if productos < MIN_PRODUCTOS_CON_DESATENDIDOS:
        return {"pasa": False, "motivo": "los desatendidos son de un solo producto: es el defecto de ese producto", **datos}
    return {"pasa": True, "motivo": f"{len(sin_resolver)} desatendidos (lo tienen {len(tienen)} de {en_segmento['medidas']}, "
                                    f"{datos['veces_mas_que_el_control']} veces más que en el control)", **datos}


def muestra(gente: list[dict], n: int, etiqueta: str) -> list[dict]:
    return gente if len(gente) <= n else random.Random(f"{SEMILLA}{etiqueta}").sample(gente, n)


def dolores_del_segmento(cliente, mapa: dict, miembros: dict, tarjetas: dict, todos: dict, traza: list) -> list[dict]:
    """Hipótesis de dolor del segmento, cada una medida en el segmento y en un control al azar."""
    del_segmento = muestra(list(miembros.values()), PERSONAS_MEDIDAS, mapa["segmento"])
    control = muestra([t for i, t in tarjetas.items() if i not in miembros], len(del_segmento), f"control {mapa['segmento']}")
    salida = []
    for d in proponer_dolores(cliente, mapa, traza):
        en_segmento, en_control = medir(cliente, d, del_segmento, todos, traza), medir(cliente, d, control, todos, traza)
        salida.append({**d, "medicion": {"segmento": en_segmento, "control": {"medidas": en_control["medidas"], "tienen": en_control["tienen"]}},
                       "veredicto": veredicto(en_segmento, en_control, tarjetas)})
    return salida
