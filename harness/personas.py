"""Perfilar a la gente y agruparla por el trabajo que intenta hacer, no por lo que compró.

    A  tarjetas  (skills/leer_personas)     el LLM lee las voces de cada producto y anota, por
                                             persona: situación, qué quiere lograr, dolor,
                                             ganancia, qué teme, con qué compara y una cita.
    J  trabajos  (skills/formular_trabajos) el LLM reescribe cada tarjeta como el trabajo que la
                                             persona intenta hacer, un nivel por encima del
                                             producto y sin nombrarlo, y lo que le sale mal
                                             (Ulwick, Jobs-to-be-Done; etapa de resumen orientado
                                             al uso de TnT-LLM, Wan et al. 2024).
    S  grupos    (código, sin LLM)          los trabajos se agrupan por significado: un modelo de
                                             oraciones multilingüe (sentence-transformers) y
                                             clustering jerárquico de Ward, como Timoshenko y
                                             Hauser (2019) con las necesidades. El corte del árbol
                                             es el que deja más grupos que cruzan búsquedas con la
                                             evidencia que pide el paso B.

Antes los grupos los definía el LLM en una sola llamada a partir de la "situación" de cada
persona; como el 70% de las reseñas no cuenta la situación, salían por categoría de producto
("convivencia con gatos"). El trabajo, en cambio, está en casi todas.

Tarjetas, trabajos y grupos se guardan en data/serendipia/personas_<particion>_api.json y se
reusan.
"""

from __future__ import annotations

import json
from collections import Counter

from harness.modelo import con_reintento, en_paralelo
from harness.voces import RAIZ, productos, sin_acentos, textos_con_id

SKILL_A = RAIZ / "skills/leer_personas/SKILL.md"
SKILL_J = RAIZ / "skills/formular_trabajos/SKILL.md"
MIN_PALABRAS_OPINION = 8          # decisión: "Excelente, llegó rápido" no cuenta nada de quien lo escribe; las preguntas se leen todas
VOCES_POR_LLAMADA = 50
TARJETAS_POR_LLAMADA_J = 80
MIN_PERSONAS_POR_BUSQUEDA = 2    # lo que el paso B necesita para proponer: 2 personas de cada una de 2 búsquedas
MIN_BUSQUEDAS_POR_GRUPO = 2       # el grupo cruza búsquedas: los 2 productos ancla de una misma búsqueda son la misma categoría
MODELO_DE_ORACIONES = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
PASO_DEL_CORTE = 10               # cortes del árbol que se prueban: 10, 20, 30... grupos
PERSONAS_EN_EL_MAPA = 60          # las que lee el paso B de cada grupo (primero aquellas a las que algo les sale mal)
ALTERNATIVAS_QUE_VE = 4           # de cada búsqueda: las más elegidas y las que se dejaron pasar
CAMPOS = ("situacion", "quiere_lograr", "dolor", "ganancia", "teme", "compara_con")
AGRUPACION = "trabajos_mpnet_ward_busquedas"      # versión de los grupos guardados: si cambia, se recalculan


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


def tarjetas_de_la_particion(cliente, particion: str, traza: list, saltear: set = frozenset()) -> list[dict]:
    tandas = []
    for p in (p for pid, p in productos(particion).items() if pid not in saltear):
        voces = list(voces_a_leer(p).items())
        tandas += [(p, dict(voces[i:i + VOCES_POR_LLAMADA])) for i in range(0, len(voces), VOCES_POR_LLAMADA)]
    por_tanda = en_paralelo(lambda t: tarjetas_de_una_tanda(cliente, t[0], t[1], traza), tandas)
    vistas = {}
    for t in (t for tanda in por_tanda for t in tanda):
        vistas.setdefault(t["id"], t)         # una persona, una tarjeta
    return list(vistas.values())


# --- J · El trabajo de cada persona --------------------------------------------------------

def linea_j(t: dict, todos: dict) -> str:
    return (f"[{t['id']}] {todos[t['producto']]['titulo'][:60]} | "
            + " | ".join(t[c] for c in ("situacion", "quiere_lograr", "dolor", "teme", "compara_con")))


def trabajos(cliente, tarjetas: list[dict], traza: list) -> dict[str, dict]:
    """{id de persona: {trabajo, le_sale_mal}}. La que no se puede formular queda afuera."""
    todos = productos()
    tandas = [tarjetas[i:i + TARJETAS_POR_LLAMADA_J] for i in range(0, len(tarjetas), TARJETAS_POR_LLAMADA_J)]

    def una_tanda(tanda):
        prompt = (f"{SKILL_J.read_text(encoding='utf-8')}\n\n---\n\nPERSONAS\n" + "\n".join(linea_j(t, todos) for t in tanda)
                  + "\n\nRespondé SOLO con el JSON de la salida.")
        de_la_tanda = {t["id"] for t in tanda}
        validar = lambda d: {str(x.get("id")): ["no es de esta tanda o no tiene trabajo"] for x in d.get("trabajos", [])
                             if x.get("id") not in de_la_tanda or not x.get("trabajo")}
        d = con_reintento(cliente, prompt, validar, traza, "J trabajos", pensar=False)
        return {x["id"]: {"trabajo": x["trabajo"], "le_sale_mal": x.get("le_sale_mal", "")}
                for x in d.get("trabajos", []) if x.get("id") in de_la_tanda and x.get("trabajo")}

    return {k: v for parte in en_paralelo(una_tanda, tandas) for k, v in parte.items()}


# --- S · Grupos por trabajo (código) ---------------------------------------------------------

def vectores(textos: list[str]):
    """Un vector por trabajo, normalizado, con un modelo de oraciones multilingüe. Corre en el
    workflow (requirements-llm.txt); los grupos quedan guardados y no hace falta para reproducir."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELO_DE_ORACIONES).encode(textos, batch_size=64, normalize_embeddings=True)


def cruza_busquedas(busquedas_de_miembros: list[str]) -> bool:
    por_busqueda = Counter(busquedas_de_miembros)
    return sum(n >= MIN_PERSONAS_POR_BUSQUEDA for n in por_busqueda.values()) >= MIN_BUSQUEDAS_POR_GRUPO


def agrupar_por_trabajo(tarjetas: dict[str, dict], trabajos_: dict[str, dict]) -> tuple[list[dict], dict[str, str]]:
    """Ward sobre los trabajos. De los cortes del árbol, el que deja más grupos que cruzan
    búsquedas (a igualdad, el de menos grupos): la granularidad más fina que todavía tiene la
    evidencia que el paso B necesita para proponer."""
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage
    todos = productos()
    ids = [i for i in trabajos_ if i in tarjetas]
    V = np.asarray(vectores([trabajos_[i]["trabajo"] for i in ids]))
    arbol = linkage(V, method="ward")
    busq = [todos[tarjetas[i]["producto"]]["busqueda"] for i in ids]
    mejor = None
    for k in range(PASO_DEL_CORTE, len(ids) // (MIN_PERSONAS_POR_BUSQUEDA * MIN_BUSQUEDAS_POR_GRUPO) + 1, PASO_DEL_CORTE):
        etiquetas = fcluster(arbol, k, criterion="maxclust")
        grupos = {}
        for b, e in zip(busq, etiquetas):
            grupos.setdefault(e, []).append(b)
        n = sum(cruza_busquedas(g) for g in grupos.values())
        if mejor is None or n > mejor[0]:
            mejor = (n, k, etiquetas)
    _, k, etiquetas = mejor
    miembros = {}
    for i, e, v in zip(ids, etiquetas, V):
        miembros.setdefault(int(e), []).append((i, v))
    segmentos, asignaciones = [], {}
    for n, (_, ms) in enumerate(sorted(miembros.items(), key=lambda x: -len(x[1])), start=1):
        centro = np.mean([v for _, v in ms], axis=0)
        orden = sorted(ms, key=lambda m: -float(m[1] @ centro))      # el más típico primero
        sid = f"T{n:03d}"
        segmentos.append({"id": sid, "nombre": trabajos_[orden[0][0]]["trabajo"],
                          "quien": "; ".join(dict.fromkeys(trabajos_[i]["trabajo"] for i, _ in orden[:5])),
                          "corte": k})
        asignaciones |= {i: sid for i, _ in ms}
    return segmentos, asignaciones


def personas_de_la_particion(cliente, particion: str, traza: list) -> dict:
    """Tarjetas, trabajos y grupos de la partición; se calculan una vez y se guardan."""
    archivo = RAIZ / f"data/serendipia/personas_{particion}_api.json"
    guardado = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    guardar = lambda: archivo.write_text(json.dumps(guardado, ensure_ascii=False, indent=1), encoding="utf-8")
    leidos = {t["producto"] for t in guardado.get("tarjetas", [])}
    if "tarjetas" not in guardado or set(productos(particion)) - leidos:
        # Solo se leen los productos nuevos (la partición creció); los ya leídos no se repiten.
        guardado["tarjetas"] = guardado.get("tarjetas", []) + tarjetas_de_la_particion(cliente, particion, traza, saltear=leidos)
        guardado.pop("trabajos", None)
        guardado.pop("agrupacion", None)
        guardar()
    if "trabajos" not in guardado:
        guardado["trabajos"] = trabajos(cliente, guardado["tarjetas"], traza)
        guardado.pop("agrupacion", None)
        guardar()
    if guardado.get("agrupacion") != AGRUPACION:
        tarjetas = {t["id"]: t for t in guardado["tarjetas"]}
        segmentos, asignaciones = agrupar_por_trabajo(tarjetas, guardado["trabajos"])
        guardado |= {"agrupacion": AGRUPACION, "segmentos": segmentos, "asignaciones": asignaciones}
        guardar()
    return guardado


# --- El mapa de empatía de un grupo (código) -------------------------------------------------

def eleccion_en_la_busqueda(captura: dict | None) -> dict:
    """Voto con los pies en una búsqueda: lo que se elige y lo que se ofrece y se deja pasar."""
    if not captura:
        return {"elegidas": [], "dejadas": []}
    pubs = [p for p in captura["publicaciones"] if p.get("precio")]
    fila = lambda p: f"{p['titulo'][:70]} | ${p['precio']:,} | +{p['vendidos']}"
    return {"elegidas": [fila(p) for p in sorted((p for p in pubs if p["vendidos"] >= 100), key=lambda p: -p["vendidos"])[:ALTERNATIVAS_QUE_VE]],
            "dejadas": [fila(p) for p in pubs if p["vendidos"] <= 25 and not p["internacional"]][:ALTERNATIVAS_QUE_VE]}


def mapa_de_empatia(segmento: dict, miembros: list[dict], todos: dict, capturas: dict, trabajos_: dict | None = None) -> dict:
    """Lo que el paso B lee del grupo: el trabajo que comparten, quiénes son, qué eligen y qué
    dejan pasar, qué ven, qué dicen y qué les sale mal."""
    trabajos_ = trabajos_ or {}
    le_sale_mal = lambda t: bool(trabajos_.get(t["id"], {}).get("le_sale_mal") or t["dolor"] or t["teme"])
    por_producto = Counter(t["producto"] for t in miembros)
    busquedas = sorted({todos[pid]["busqueda"] for pid in por_producto})
    # primero aquellas a las que algo les sale mal, repartidas entre productos
    orden = sorted(miembros, key=lambda t: (not le_sale_mal(t), t["id"]))
    rondas, vistas = {}, []
    for t in orden:
        rondas.setdefault(t["producto"], []).append(t)
    while len(vistas) < min(PERSONAS_EN_EL_MAPA, len(miembros)):
        for pid in list(rondas):
            if rondas[pid] and len(vistas) < PERSONAS_EN_EL_MAPA:
                vistas.append(rondas[pid].pop(0))
    return {"segmento": segmento["id"], "trabajo": segmento["nombre"], "quien": segmento["quien"],
            "personas": len(miembros), "les_sale_mal": sum(map(le_sale_mal, miembros)),
            "compraron": sum(t["eligio"] for t in miembros), "dudan": sum(not t["eligio"] for t in miembros),
            "productos": {pid: {"titulo": todos[pid]["titulo"][:70], "vendidos": todos[pid]["vendidos"],
                                "precio": todos[pid]["precio"], "personas": n} for pid, n in por_producto.most_common()},
            "busquedas": {b: eleccion_en_la_busqueda(capturas.get(b)) for b in busquedas},
            "personas_por_busqueda": dict(Counter(todos[t["producto"]]["busqueda"] for t in miembros)),
            "voces": [{"id": t["id"], **trabajos_.get(t["id"], {}), **{c: t[c] for c in CAMPOS if t[c]}} for t in vistas]}


def es_segmento_suficiente(mapa: dict) -> bool:
    """Tiene la evidencia que el paso B necesita: 2 personas en cada una de 2 búsquedas."""
    return sum(n >= MIN_PERSONAS_POR_BUSQUEDA for n in mapa["personas_por_busqueda"].values()) >= MIN_BUSQUEDAS_POR_GRUPO
