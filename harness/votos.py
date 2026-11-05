"""Etapa divergente: leer cómo vota la gente en una búsqueda.

En cada búsqueda de Mercado Libre conviven publicaciones que venden ("+N vendidos") y
publicaciones que no. Ese contraste es el voto con los pies: qué formato, marca, precio u
origen eligió la gente y cuál dejó pasar. De ahí se abducen hipótesis de oportunidad.

Tres piezas:
- `vista`: la búsqueda ordenada en ganadoras y perdedoras, con índice estable para citar.
- `contraste_terminos`: el BASELINE sin LLM. Log-odds con prior informativo
  (Monroe et al. 2008) de los términos del título en ganadoras contra perdedoras.
- `validar_hipotesis`: el GUARDRAIL. Toda hipótesis tiene que citar publicaciones
  concretas, con un fragmento literal de su título, y la cita tiene que coincidir con lo
  que afirma (si dice que algo gana, la publicación citada tiene que vender).
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

STOP = set("""de la el en y con para por a o los las del al un una 1 2 x cm ml l lts lt
oz kg g mm color negro blanco gris rojo azul verde rosa acero inoxidable""".split())


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def tokens(titulo: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", norm(titulo)) if t not in STOP and len(t) > 2 and not t.isdigit()]


def vista(pubs: list[dict]) -> dict:
    """Publicaciones con índice estable (posición en la página), separadas por voto."""
    con_idx = [{"i": i, **p} for i, p in enumerate(pubs)]
    ganan = sorted((p for p in con_idx if p["vendidos"] > 0), key=lambda p: -p["vendidos"])
    pierden = [p for p in con_idx if p["vendidos"] == 0]
    return {"ganan": ganan, "pierden": pierden, "ventas_visibles": sum(p["vendidos"] for p in ganan)}


def contraste_terminos(pubs: list[dict], k: int = 6, alfa: float = 0.5) -> dict:
    """Baseline: qué términos distinguen a lo que vende de lo que no.

    Cada ganadora pesa log(1 + vendidos) para que una publicación con +10.000 no tape
    todo. Devuelve los k términos con mayor z-score de cada lado.
    """
    v = vista(pubs)
    a, b = Counter(), Counter()
    for p in v["ganan"]:
        w = math.log1p(p["vendidos"])
        for t in set(tokens(p["titulo"])):
            a[t] += w
    for p in v["pierden"]:
        for t in set(tokens(p["titulo"])):
            b[t] += 1
    vocab = set(a) | set(b)
    if not a or not b:
        return {"ganan": [], "pierden": []}
    na, nb = sum(a.values()), sum(b.values())
    prior = {t: alfa * (a[t] / na + b[t] / nb) / 2 * len(vocab) for t in vocab}
    a0 = sum(prior.values())
    z = {}
    for t in vocab:
        pa = (a[t] + prior[t]) / (na + a0 - a[t] - prior[t])
        pb = (b[t] + prior[t]) / (nb + a0 - b[t] - prior[t])
        d = math.log(pa) - math.log(pb)
        var = 1 / (a[t] + prior[t]) + 1 / (b[t] + prior[t])
        z[t] = d / math.sqrt(var)
    orden = sorted(z, key=z.get)
    return {"ganan": [(t, round(z[t], 2)) for t in reversed(orden[-k:])],
            "pierden": [(t, round(z[t], 2)) for t in orden[:k]]}


def validar_hipotesis(h: dict, fuente: dict[str, list[dict]]) -> list[str]:
    """Guardrail en código. Devuelve la lista de problemas; vacía si la hipótesis pasa.

    `fuente` es {búsqueda: publicaciones}. Formato esperado de la hipótesis:
        {"id": str, "busquedas": [str, ...], "necesidad": str, "tipo": str, "oportunidad": str,
         "evidencia": [{"busqueda": str, "i": int, "vota": "gana"|"pierde", "fragmento": str}, ...],
         "rivales": [str, ...]}
    Una hipótesis puede cruzar búsquedas: cada cita dice de qué búsqueda sale.
    """
    errores = []
    for campo in ("necesidad", "tipo", "oportunidad", "evidencia", "rivales"):
        if not h.get(campo):
            errores.append(f"falta '{campo}'")
    ev = h.get("evidencia") or []
    if len({e.get("vota") for e in ev}) < 2:
        errores.append("la evidencia tiene que citar al menos una publicación que gana y una que pierde")
    for e in ev:
        pubs = fuente.get(e.get("busqueda"))
        if pubs is None:
            errores.append(f"cita una búsqueda que no existe: {e.get('busqueda')!r}")
            continue
        i = e.get("i")
        if not isinstance(i, int) or not 0 <= i < len(pubs):
            errores.append(f"cita una publicación que no existe: {i}")
            continue
        p = pubs[i]
        if norm(e.get("fragmento", "")) not in norm(p["titulo"]) or len(e.get("fragmento", "")) < 4:
            errores.append(f"[{i}] el fragmento '{e.get('fragmento')}' no está en el título")
        if e.get("vota") == "gana" and p["vendidos"] == 0:
            errores.append(f"[{i}] dice que gana pero no tiene ventas visibles")
        if e.get("vota") == "pierde" and p["vendidos"] > 0:
            errores.append(f"[{i}] dice que pierde pero tiene +{p['vendidos']} vendidos")
    return errores
