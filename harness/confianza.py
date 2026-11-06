"""Cuánto confiar en una oportunidad que pasó las pruebas (o quedó condicional).

Pasar las pruebas dice que nada la descartó; no dice cuán sólida es la evidencia. La
confianza la calcula el programa (no el LLM) con cinco factores de sí o no. Cuantos más se
cumplen, más alta. Los umbrales están en `harness/umbrales.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from harness import umbrales as U


@dataclass(frozen=True)
class Factor:
    a_favor: str
    en_contra: str
    se_cumple: object   # función: lo que sabemos de la oportunidad -> bool


FACTORES = [
    Factor("la misma necesidad aparece en 2 o más productos distintos",
           "aparece en un solo producto",
           lambda o: o["anclas"] >= U.MIN_ANCLAS_CON_LA_NECESIDAD),
    Factor("la mencionan 10 o más textos", "la mencionan menos de 10 textos",
           lambda o: o["max_menciones"] >= U.MIN_TEXTOS_PARA_CONFIANZA),
    Factor("la gente ya elige este tipo de producto: los equivalentes suman +500 ventas",
           "los equivalentes casi no se venden: puede que no lo quiera tanta gente",
           lambda o: o["ventas_de_equivalentes"] >= U.MIN_VENTAS_DE_EQUIVALENTES),
    Factor("el precio de referencia sale de 3 o más publicaciones con ventas",
           "el precio de referencia sale de pocas publicaciones",
           lambda o: o["publicaciones_con_precio"] >= U.MIN_PUBLICACIONES_PARA_PRECIO),
    Factor("deja la ganancia de referencia aun en el escenario pesimista",
           "en el escenario pesimista no deja la ganancia de referencia",
           lambda o: o["margen_pesimista_pct"] >= U.MIN_MARGEN_NETO * 100),
]


def evidencia(recorridos: list[dict]) -> dict:
    """Junta lo que sabemos de una oportunidad a partir de sus recorridos por el embudo (uno
    por cada producto ancla donde apareció)."""
    def datos(r, chequeo):
        return next((x.get("datos", {}) for x in r["recorrido"] if x["chequeo"] == chequeo), {})
    c4, c5 = datos(recorridos[0], "C4 hueco"), datos(recorridos[0], "C6 margen")
    return {"anclas": len({pid for r in recorridos for pid in r["productos"]}),
            "max_menciones": max((s["medida"]["menciones"] for r in recorridos for s in r["señales"] if not s["errores"]), default=0),
            "ventas_de_equivalentes": c4.get("ventas_visibles", 0),
            "publicaciones_con_precio": c4.get("con_alguna_venta", 0),
            "margen_pesimista_pct": c5.get("escenarios", {}).get("pesimista", {}).get("margen_neto_pct", -100)}


def confianza(recorridos: list[dict]) -> dict:
    e = evidencia(recorridos)
    cumplidos = [f for f in FACTORES if f.se_cumple(e)]
    n = len(cumplidos)
    nivel = "alta" if n >= U.FACTORES_PARA_CONFIANZA_ALTA else "media" if n >= U.FACTORES_PARA_CONFIANZA_MEDIA else "baja"
    return {"nivel": nivel, "factores_que_se_cumplen": f"{n} de {len(FACTORES)}",
            "a_favor": [f.a_favor for f in cumplidos],
            "en_contra": [f.en_contra for f in FACTORES if f not in cumplidos], "evidencia": e}
