"""C1 · ¿El dolor que dice aliviar la propuesta existe? Lo mide alguien que no propuso.

Antes C1 y C2 contaban las palabras clave que elegía el mismo LLM que proponía: una necesidad
pasaba por estar bien redactada (y el conteo mataba ideas que la gente sí elige). Ahora el dolor
de cada propuesta (para quién, qué alivia, por qué nadie lo atiende) lo mide otro modelo que no
sabe qué se propone ni quién lo propuso (skills/medir_dolor), leyendo los textos originales de la
gente de los productos que cita la propuesta y de un grupo de control al azar de los demás
productos. Decide una prueba, no un umbral:

    los DESATENDIDOS (tienen el dolor y no lo resolvieron) son más frecuentes que en el control:
        Fisher exacto unilateral, con Benjamini-Hochberg sobre todas las propuestas del método
    los desatendidos aparecen en cada producto que cita, hasta 2 (definición: si la propuesta
        dice que la necesidad cruza productos y aparece en uno solo, es el defecto de ese producto)

Lo que importa son los desatendidos: las opiniones son de compradores de la solución actual y la
mayoría suele estar conforme; eso no refuta el dolor, dice para quién funciona esa solución.
Corre con la divergencia (necesita la API) y deja el veredicto de cada propuesta, del LLM y de
los baselines, en la salida; el embudo lo lee. Evaluación: data/evaluacion/dolor_de_la_propuesta/.
"""

from __future__ import annotations

import random
from collections import Counter

from scipy.stats import fisher_exact

from harness import umbrales as U
from harness.modelo import con_reintento, en_paralelo
from harness.voces import RAIZ, textos_con_id

SKILL_MEDIR = RAIZ / "skills/medir_dolor/SKILL.md"
PERSONAS_MEDIDAS = 150                # por grupo (al azar, con semilla fija, si hay más) (PENDIENTE: análisis de potencia)
PERSONAS_POR_LLAMADA_AL_MEDIR = 75
MAX_PRODUCTOS_CON_DESATENDIDOS = 2    # el guardrail del paso B pide que la necesidad cruce 2 productos
DESATENDIDOS_POR_PRODUCTO = 2         # como toda señal del embudo: 2 textos (harness/chequeos.errores_de_citas)
SEMILLA = 7


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


def benjamini_hochberg(p: list[float], nivel: float = U.NIVEL_DE_SIGNIFICANCIA) -> list[bool]:
    """Cuáles p-valores son significativos controlando la tasa de falsos descubrimientos."""
    orden = sorted(range(len(p)), key=lambda i: p[i])
    k = max((r + 1 for r, i in enumerate(orden) if p[i] <= (r + 1) / len(p) * nivel), default=0)
    return [i in set(orden[:k]) for i in range(len(p))]


def enunciado(o: dict) -> dict:
    """El dolor de una propuesta del LLM, sin el producto que propone."""
    return {"id": o["id"], "trabajo": o.get("para_quien", ""), "obstaculo": o.get("alivia", ""), "que_hace_mal": o.get("por_que", "")}


def medir_dolor(cliente, dolor: dict, productos_citados: set, tarjetas: dict, todos: dict, traza: list) -> dict:
    """Mide `dolor` en la gente de los productos citados y en un control del mismo tamaño."""
    azar = random.Random(f"{SEMILLA}{dolor['id']}")
    de_los_productos = [t for t in tarjetas.values() if t["producto"] in productos_citados]
    resto = [t for t in tarjetas.values() if t["producto"] not in productos_citados]
    grupo = de_los_productos if len(de_los_productos) <= PERSONAS_MEDIDAS else azar.sample(de_los_productos, PERSONAS_MEDIDAS)
    control = azar.sample(resto, min(len(resto), len(grupo)))
    return {"dolor": dolor, "productos": sorted(productos_citados),
            "medicion": {"propuesta": medir(cliente, dolor, grupo, todos, traza),
                         "control": medir(cliente, dolor, control, todos, traza)}}


def decidir(medidas: list[dict], tarjetas: dict) -> dict[str, dict]:
    """El veredicto de cada dolor medido de un mismo método (la corrección es sobre todos juntos)."""
    ps = [p_mas_frecuente(len(desatendidos(m["medicion"]["propuesta"])), m["medicion"]["propuesta"]["medidas"],
                          len(desatendidos(m["medicion"]["control"])), m["medicion"]["control"]["medidas"]) for m in medidas]
    veredictos = {}
    for m, p, sig in zip(medidas, ps, benjamini_hochberg(ps)):
        sin_resolver = desatendidos(m["medicion"]["propuesta"])
        por_producto = Counter(tarjetas[i]["producto"] for i in sin_resolver)
        productos = sum(k >= DESATENDIDOS_POR_PRODUCTO for k in por_producto.values())
        hacen_falta = min(MAX_PRODUCTOS_CON_DESATENDIDOS, len(m["productos"]))
        veredictos[m["dolor"]["id"]] = {
            "pasa": bool(sig) and productos >= hacen_falta, "significativo": bool(sig), "p": round(p, 5),
            "desatendidos": len(sin_resolver), "de": m["medicion"]["propuesta"]["medidas"],
            "en_el_control": len(desatendidos(m["medicion"]["control"])), "productos_con_desatendidos": productos,
            "hacen_falta": hacen_falta, "ejemplos": sin_resolver[:5]}
    return veredictos


def medir_y_decidir(cliente, dolores: list[tuple[dict, set]], tarjetas: dict, todos: dict, traza: list) -> dict[str, dict]:
    medidas = en_paralelo(lambda d: medir_dolor(cliente, d[0], d[1], tarjetas, todos, traza), dolores)
    return decidir(medidas, tarjetas)
