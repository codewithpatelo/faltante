"""Serendipia computacional: de los votos (pies y manos) a oportunidades de importación.

    pies  = qué se compra y qué no (ventas, precios, origen)            -> Mercado Libre
    manos = qué dicen los compradores (opiniones) y los indecisos (preguntas)

    1. FILTRO (programa)      elige los textos informativos (como Timoshenko y Hauser 2019)
    2. DIVERGENTE (LLM)       propone señales y oportunidades citando textos  -> skills/leer_voces
    3. GUARDRAIL (programa)   las citas tienen que existir y ser literales
    4. CONVERGENTE (programa) embudo que mata lo que no pasa:
         C1 señal verificada  : el programa cuenta las palabras clave en TODOS los textos
         C2 sub-atendida      : puntaje de oportunidad de Ulwick (importancia + brecha)
         C3 demanda           : el producto ancla vende
         C4 hueco local       : no hay equivalente local barato que ya venda (captura + equivalencia)
         C5 margen            : costo puesto contra precio de venta (harness/costo_puesto.py)

Umbrales a la vista, abajo. Cada oportunidad que muere queda registrada con el motivo.
"""

from __future__ import annotations

import json
import re
import unicodedata

# --- Umbrales ---------------------------------------------------------------------------
MIN_MENCIONES = 3            # C1: textos distintos que mencionan la señal
MIN_IMPORTANCIA = 3.0        # C2: importancia (0-10): 10 = el 10% o más de los textos la menciona
MAX_SATISFACCION = 5.0       # C2: satisfacción (0-10): 5 = la mitad de las menciones es queja/deseo/duda
PISO_TEXTOS_IMPORTANCIA = 0.10
MIN_VENDIDOS_ANCLA = 500     # C3: el producto donde aparece la señal vende al menos esto
MIN_VENDIDOS_EQUIV = 100     # C4: un equivalente "ya vende" si muestra +100 vendidos
MAX_EQUIVALENTES_VENDIENDO = 2  # C4: con más de 2 equivalentes que ya venden, la necesidad está atendida
MIN_MARGEN_SOBRE_COSTO = 0.30  # C5: margen sobre costo puesto, escenario base
PISO_ENVIO_GRATIS = 33000    # ARS: desde acá el vendedor paga el envío (algoritmodigital, sept. 2026)
ENVIO_DEBAJO_PISO = 2500     # ARS: costo fijo por unidad debajo del piso (1.330-4.550 según modalidad)
ENVIO_ARRIBA_PISO = 7000     # ARS: envío a cargo del vendedor, paquete chico (6.190-8.290)
LOTE_MAX = 1000              # C5: unidades del primer lote (se llena 1 m3 o hasta este tope)
# ----------------------------------------------------------------------------------------

# Marcadores de insatisfacción: queja, deseo, duda o faltante. Están a la vista porque son
# una decisión discutible; el LLM no los toca.
NEGATIVOS = re.compile(
    r"\bno (tiene|trae|viene|sirve|anda|funciona|dura|alcanza|corta|cierra|tenemos|contamos)\b|"
    r"\bfalt[aó]|\bojal[aá]\b|\bdeber[ií]a\b|\blastima\b|\bl[aá]stima\b|\bse rompi[oó]\b|\bse despeg|"
    r"\bpoco\b|\bmuy chic|\bmal[oa]?\b|\bpero\b|\b(tienen|venden|hay) repuesto|\?|\bno los tenemos\b|"
    r"\bno contamos\b|\bno disponemos\b"
)
INFORMATIVO = re.compile(
    r"\blo (uso|use|usamos|compr[eé])\b|\bpara (mi|el|la|los|las|hacer|usar|cortar|guardar)\b|"
    r"\bojal[aá]\b|\bdeber[ií]a\b|\bfalt|\bpero\b|\brepuesto|\bno (tiene|trae|viene|sirve|dura)\b|"
    r"\bse rompi|\bse despeg|\bmejor (que|seria)\b|\bcomparad|\bprefer"
)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def textos_numerados(prod: dict) -> dict[str, str]:
    """{'o1': opinión, ..., 'p1': 'pregunta || respuesta', ...}"""
    t = {f"o{i+1}": o for i, o in enumerate(prod.get("opiniones", []))}
    for i, qa in enumerate(prod.get("preguntas", [])):
        t[f"p{i+1}"] = " || ".join(qa) if isinstance(qa, list) else qa
    return t


def filtrar_informativos(textos: dict[str, str], k: int = 60) -> dict[str, str]:
    """Paso 1. Todas las preguntas + las k opiniones más informativas (marcadores de uso,
    queja o deseo primero, después las más largas)."""
    preguntas = {i: t for i, t in textos.items() if i.startswith("p")}
    ops = [(i, t) for i, t in textos.items() if i.startswith("o")]
    ops.sort(key=lambda it: (not INFORMATIVO.search(norm(it[1])), -len(it[1])))
    return {**preguntas, **dict(ops[:k])}


def validar_señal(señal: dict, textos: dict[str, str]) -> list[str]:
    """Paso 3. Guardrail: citas existentes, literales, de al menos 2 textos distintos."""
    errores = []
    citas = señal.get("citas") or []
    if len({c.get("texto") for c in citas}) < 2:
        errores.append("tiene que citar al menos 2 textos distintos")
    for c in citas:
        t = textos.get(c.get("texto"))
        if t is None:
            errores.append(f"cita un texto que no existe: {c.get('texto')}")
        elif len(c.get("fragmento", "")) < 4 or norm(c["fragmento"]) not in norm(t):
            errores.append(f"[{c.get('texto')}] el fragmento no está en el texto")
    if not señal.get("palabras_clave"):
        errores.append("faltan palabras_clave para que el programa cuente")
    return errores


def medir_señal(señal: dict, textos: dict[str, str]) -> dict:
    """C1 y C2. Cuenta en TODOS los textos (no solo los que leyó el LLM)."""
    claves = [norm(p) for p in señal.get("palabras_clave", [])]
    menciones = [t for t in textos.values() if any(k in norm(t) for k in claves)]
    n = len(menciones)
    insatisfechas = sum(1 for t in menciones if NEGATIVOS.search(norm(t)))
    share = n / max(1, len(textos))
    importancia = round(min(10.0, 10 * share / PISO_TEXTOS_IMPORTANCIA), 1)
    satisfaccion = round(10 * (1 - insatisfechas / n), 1) if n else 10.0
    puntaje = round(importancia + max(importancia - satisfaccion, 0), 1)  # Ulwick
    return {"menciones": n, "insatisfechas": insatisfechas, "de_textos": len(textos),
            "importancia": importancia, "satisfaccion": satisfaccion, "puntaje_oportunidad": puntaje,
            "C1_verificada": n >= MIN_MENCIONES,
            "C2_subatendida": importancia >= MIN_IMPORTANCIA and satisfaccion <= MAX_SATISFACCION}


def baseline_señal(textos: dict[str, str]) -> dict:
    """Baseline sin LLM: el término más frecuente en los textos insatisfechos (excluyendo
    palabras vacías), como 'señal'. Pasa por el mismo embudo."""
    vacias = set("""que de la el en y a los las un una lo con para por es no se muy mas pero me le
    su al del como esta este son fue tiene ya si porque producto bien todo hay cuando""".split())
    from collections import Counter
    c = Counter()
    for t in textos.values():
        n = norm(t)
        if NEGATIVOS.search(n):
            c.update(w for w in set(re.findall(r"[a-z]{4,}", n)) if w not in vacias)
    termino = c.most_common(1)[0][0] if c else ""
    return {"id": "B1", "tipo": "queja", "descripcion": f"queja más frecuente: '{termino}'",
            "palabras_clave": [termino] if termino else []}


# --- C3, C4, C5 -------------------------------------------------------------------------

def es_equivalente(titulo: str, criterio: dict) -> bool:
    """`criterio`: {"empieza_con": [...], "no_empieza_con": [...], "todos": [[sinónimos], ...],
    "excluir": [...]}. En Mercado Libre el título empieza por lo que se vende ("Disco ...",
    "Afilador ..."), por eso el criterio mira el comienzo. Además tiene que contener al menos un
    término de cada grupo de `todos` y ninguno de `excluir`."""
    t = norm(titulo)
    if any(t.startswith(norm(e)) for e in criterio.get("no_empieza_con", [])):
        return False
    if criterio.get("empieza_con") and not any(t.startswith(norm(e)) for e in criterio["empieza_con"]):
        return False
    if any(norm(x) in t for x in criterio.get("excluir", [])):
        return False
    return all(any(norm(s) in t for s in grupo) for grupo in criterio.get("todos", []))


def hueco_local(publicaciones: list[dict], criterio: dict, excluir_titulos: set[str] = frozenset()) -> dict:
    """C4. ¿Ya hay en Mercado Libre algo equivalente que se venda?"""
    vistos, equivalentes = set(), []
    for p in publicaciones:
        clave = (norm(p["titulo"]), p.get("precio"))
        if clave in vistos or norm(p["titulo"]) in excluir_titulos:
            continue
        vistos.add(clave)
        if es_equivalente(p["titulo"], criterio):
            equivalentes.append(p)
    venden = [p for p in equivalentes if p["vendidos"] >= MIN_VENDIDOS_EQUIV]
    # Precio de referencia: lo que la gente paga. Mediana de los equivalentes con alguna venta;
    # si ninguno vendió, no hay precio de mercado (las publicaciones sin ventas pueden pedir cualquier cosa).
    precios = sorted(p["precio"] for p in equivalentes if p.get("precio") and p["vendidos"] > 0)
    return {"equivalentes": len(equivalentes), "venden": len(venden),
            "ejemplos_que_venden": [f"{p['titulo'][:70]} (+{p['vendidos']}, ${p['precio']:,})" for p in sorted(venden, key=lambda p: -p["vendidos"])[:3]],
            "precio_mediano_equivalentes_que_vendieron": precios[len(precios) // 2] if precios else None,
            "C4_hueco": len(venden) <= MAX_EQUIVALENTES_VENDIENDO}


def margen(fob: dict, precio_ars: float) -> dict:
    """C5. Margen sobre costo puesto, escenarios optimista / base / pesimista, al precio de
    referencia del mercado. Además calcula el FOB máximo que deja el margen mínimo: si el
    escenario base no alcanza pero el optimista sí, la oportunidad queda *condicional* a que un
    proveedor cotice por debajo de ese FOB (es el experimento siguiente)."""
    from harness.costo_puesto import (EMBALAJE, FLETE_M3_PARA_CIF, LOGISTICA_M3, SEGURO, TASA_ESTADISTICA, TIPO_CAMBIO,
                                      costo_puesto_usd, ingreso_neto_ars)
    lote = min(LOTE_MAX, int(1 / (fob["volumen_m3"] * EMBALAJE)))
    envio = ENVIO_DEBAJO_PISO if precio_ars < PISO_ENVIO_GRATIS else ENVIO_ARRIBA_PISO
    neto = ingreso_neto_ars(precio_ars, envio)
    esc = {}
    for nombre, f, d in (("optimista", fob["fob"][0], fob["die"][0]), ("base", fob["fob"][1], fob["die"][0]),
                         ("pesimista", fob["fob"][2], fob["die"][1])):
        costo = costo_puesto_usd(f, d, fob["volumen_m3"], lote)["total"] * TIPO_CAMBIO
        esc[nombre] = {"costo_puesto_ars": round(costo), "margen_pct": round((neto - costo) / costo * 100)}
    vol = max(1.0, fob["volumen_m3"] * EMBALAJE * lote) / lote
    impuestos = fob["die"][0] + TASA_ESTADISTICA
    costo_max_usd = neto / (1 + MIN_MARGEN_SOBRE_COSTO) / TIPO_CAMBIO
    fob_max = (costo_max_usd - LOGISTICA_M3 * vol - FLETE_M3_PARA_CIF * vol * impuestos) / (1 + (1 + SEGURO) * impuestos)
    base_ok = esc["base"]["margen_pct"] >= MIN_MARGEN_SOBRE_COSTO * 100
    opt_ok = esc["optimista"]["margen_pct"] >= MIN_MARGEN_SOBRE_COSTO * 100
    return {"precio_ars": precio_ars, "ingreso_neto_ars": round(neto), "lote": lote, "envio_ars": envio,
            "escenarios": esc, "fob_maximo_usd": round(fob_max, 2),
            "C5_margen": base_ok, "C5_condicional": (not base_ok) and opt_ok}


# --- Paso divergente con la API (lo mismo que se hizo a mano en el chat) -----------------

MODELO = "claude-haiku-4-5"
PRECIO_MTOK = {"entrada": 1.0, "salida": 5.0}  # USD por millón de tokens (Haiku 4.5)


def prompt_voces(prod: dict, textos: dict[str, str]) -> str:
    from pathlib import Path
    skill = (Path(__file__).resolve().parent.parent / "skills/leer_voces/SKILL.md").read_text(encoding="utf-8")
    cab = (f"PRODUCTO ANCLA: {prod['titulo']} | +{prod['vendidos']} vendidos | ${prod['precio']:,} | "
           f"búsqueda: {prod['busqueda']} | {prod.get('calificacion', '')}")
    cuerpo = "\n".join(f"[{i}] {t[:300]}" for i, t in filtrar_informativos(textos, k=22).items())
    return f"{skill}\n\n---\n\n{cab}\n{cuerpo}\n\nRespondé SOLO con el JSON de la salida."


def leer_voces_llm(cliente, prod: dict, traza: list) -> dict:
    """Propone, valida las citas en código y reintenta una vez con los errores (evaluador-optimizador)."""
    import time
    textos = textos_numerados(prod)
    mensajes = [{"role": "user", "content": prompt_voces(prod, textos)}]
    salida = {"señales": [], "oportunidades": []}
    for intento in range(2):
        t0 = time.time()
        r = cliente.messages.create(model=MODELO, max_tokens=3000, messages=mensajes)
        texto = r.content[0].text
        m = re.search(r"\{.*\}", texto, re.S)
        try:
            salida = json.loads(m.group(0)) if m else salida
        except json.JSONDecodeError:
            salida = {"señales": [], "oportunidades": []}
        errores = {s.get("id"): validar_señal(s, textos) for s in salida.get("señales", [])}
        errores = {k: v for k, v in errores.items() if v}
        traza.append({"producto": prod["id"], "intento": intento, "segundos": round(time.time() - t0, 2),
                      "tokens": {"entrada": r.usage.input_tokens, "salida": r.usage.output_tokens}, "errores": errores})
        if not errores:
            break
        mensajes += [{"role": "assistant", "content": texto},
                     {"role": "user", "content": "El validador rechazó estas citas:\n" + json.dumps(errores, ensure_ascii=False)
                      + "\nCorregí o sacá esas señales. Respondé SOLO con el JSON."}]
    salida.setdefault("señales", [])
    salida.setdefault("oportunidades", [])
    return salida


def costo(traza: list) -> dict:
    ent = sum(t["tokens"]["entrada"] for t in traza)
    sal = sum(t["tokens"]["salida"] for t in traza)
    return {"tokens_entrada": ent, "tokens_salida": sal,
            "usd": round(ent / 1e6 * PRECIO_MTOK["entrada"] + sal / 1e6 * PRECIO_MTOK["salida"], 4),
            "segundos": round(sum(t["segundos"] for t in traza), 1)}


if __name__ == "__main__":
    # ANTHROPIC_API_KEY=... python -m harness.serendipia test  -> data/serendipia/divergente_test_api.json
    import sys
    from pathlib import Path
    import anthropic
    raiz = Path(__file__).resolve().parent.parent
    part = sys.argv[1] if len(sys.argv) > 1 else "test"
    corpus = json.loads((raiz / "data/voces/corpus_2026-11-05.json").read_text())["productos"]
    cliente, traza, por_producto = anthropic.Anthropic(), [], {}
    for p in corpus:
        if p["particion"] == part:
            por_producto[p["id"]] = leer_voces_llm(cliente, p, traza)
    destino = raiz / f"data/serendipia/divergente_{part}_api.json"
    destino.write_text(json.dumps({"quien": MODELO, "costo": costo(traza), "traza": traza, "por_producto": por_producto},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{destino}: {costo(traza)}")
