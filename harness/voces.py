"""Los textos que lee el programa: opiniones de compradores y preguntas de indecisos.

Cada texto lleva un ID corto ("o12" = opinión 12, "p3" = pregunta 3) para que el LLM pueda
citarlo y el programa pueda verificar la cita.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# Cada corpus es una tanda de productos con sus voces: data/voces/ (los 21 primeros, P01..P21)
# y data/escala/ (los de la recolección a escala, E001...).
CORPUS = sorted(RAIZ.glob("data/voces/corpus_*.json")) + sorted(RAIZ.glob("data/escala/corpus_*.json"))

# Un texto expresa insatisfacción si tiene alguna de estas marcas: queja, deseo, duda o
# faltante. Es una decisión discutible y por eso está a la vista; el LLM no la toca.
MARCAS_DE_INSATISFACCION = re.compile(
    r"\bno (tiene|trae|viene|sirve|anda|funciona|dura|alcanza|corta|cierra|tenemos|contamos)\b|"
    r"\bfalt[aó]|\bojal[aá]\b|\bdeber[ií]a\b|\blastima\b|\bl[aá]stima\b|\bse rompi[oó]\b|\bse despeg|"
    r"\bpoco\b|\bmuy chic|\bmal[oa]?\b|\bpero\b|\b(tienen|venden|hay) repuesto|\?|\bno los tenemos\b|"
    r"\bno contamos\b|\bno disponemos\b"
)

# Una opinión es informativa si cuenta un uso, una comparación, una queja o un deseo
# (Timoshenko y Hauser, 2019: filtrar antes de leer). "Excelente, llegó rápido" no lo es.
MARCAS_DE_OPINION_INFORMATIVA = re.compile(
    r"\blo (uso|use|usamos|compr[eé])\b|\bpara (mi|el|la|los|las|hacer|usar|cortar|guardar)\b|"
    r"\bojal[aá]\b|\bdeber[ií]a\b|\bfalt|\bpero\b|\brepuesto|\bno (tiene|trae|viene|sirve|dura)\b|"
    r"\bse rompi|\bse despeg|\bmejor (que|seria)\b|\bcomparad|\bprefer"
)


def sin_acentos(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar 'Hermético' con 'hermetico'."""
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def productos(particion: str | None = None) -> dict[str, dict]:
    """Los productos ancla del corpus ({"P01": {...}}), opcionalmente de una sola partición."""
    todos = [p for f in CORPUS for p in json.loads(f.read_text(encoding="utf-8"))["productos"]]
    return {p["id"]: p for p in todos if particion is None or p["particion"] == particion}


def textos_con_id(producto: dict) -> dict[str, str]:
    """{"o1": opinión, ..., "p1": "pregunta || respuesta del vendedor", ...}"""
    textos = {f"o{i + 1}": o for i, o in enumerate(producto.get("opiniones", []))}
    for i, qa in enumerate(producto.get("preguntas", [])):
        textos[f"p{i + 1}"] = " || ".join(qa) if isinstance(qa, list) else qa
    return textos


def los_mas_informativos(textos: dict[str, str], opiniones: int) -> dict[str, str]:
    """Lo que lee el LLM: todas las preguntas (los indecisos dicen qué les falta) y las
    opiniones más informativas, primero las que tienen marcas y después las más largas."""
    preguntas = {i: t for i, t in textos.items() if i.startswith("p")}
    ordenadas = sorted(((i, t) for i, t in textos.items() if i.startswith("o")),
                       key=lambda it: (not MARCAS_DE_OPINION_INFORMATIVA.search(sin_acentos(it[1])), -len(it[1])))
    return {**preguntas, **dict(ordenadas[:opiniones])}


def expresa_insatisfaccion(texto: str) -> bool:
    return bool(MARCAS_DE_INSATISFACCION.search(sin_acentos(texto)))
