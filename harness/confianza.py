"""Cuánto sabemos de una oportunidad que pasó las pruebas (o quedó condicional).

Pasar las pruebas dice que nada la descartó; no dice cuán sólida es la evidencia. En vez de sumar
puntos con umbrales a ojo, se muestra cada evidencia con su incertidumbre y se listan los
riesgos que sí tienen una definición:

    dolor        quiénes lo tienen sin resolver, con su intervalo de confianza de Wilson al 95%
    demanda      lo que ya venden los equivalentes ("al menos", por la escala de "+N vendidos")
    precio       de cuántas publicaciones con ventas sale, y su rango
    margen       del escenario pesimista al optimista

    riesgo: en el escenario pesimista no deja la ganancia de referencia del sector
    riesgo: ningún equivalente vendió (el precio no lo pagó nadie todavía)
    riesgo: el precio sale de una sola publicación (no hay dispersión que mirar)
"""

from __future__ import annotations

from scipy.stats import binomtest

from harness import umbrales as U


def datos(r: dict, chequeo: str) -> dict:
    return next((x.get("datos", {}) for x in r["recorrido"] if x["chequeo"] == chequeo), {})


def evidencia(recorridos: list[dict]) -> dict:
    """Lo que sabemos de una oportunidad a partir de sus recorridos por el embudo (uno por cada
    producto ancla donde apareció)."""
    r = recorridos[0]
    dolor, c4, c6 = datos(r, "C1 dolor"), datos(r, "C4 hueco"), datos(r, "C6 margen")
    e = {"productos": len({pid for x in recorridos for pid in x["productos"]})}
    if dolor.get("de"):
        ic = binomtest(dolor["desatendidos"], dolor["de"]).proportion_ci(0.95, method="wilson")
        e["dolor"] = {"desatendidos": dolor["desatendidos"], "de": dolor["de"], "en_el_control": dolor["en_el_control"],
                      "proporcion_ic95": [round(ic.low, 3), round(ic.high, 3)], "p": dolor["p"]}
    e["demanda"] = {"ventas_de_equivalentes_al_menos": c4.get("ventas_visibles", 0), "equivalentes_con_ventas": c4.get("con_alguna_venta", 0)}
    escenarios = c6.get("escenarios", {})
    if escenarios:
        e["margen_neto_pct"] = {k: v["margen_neto_pct"] for k, v in escenarios.items()}
    return e


def confianza(recorridos: list[dict]) -> dict:
    e = evidencia(recorridos)
    riesgos = []
    margen = e.get("margen_neto_pct", {})
    if margen and margen.get("pesimista", -100) < U.MIN_MARGEN_NETO * 100:
        riesgos.append(f"en el escenario pesimista deja {margen['pesimista']}%, menos que la ganancia de referencia")
    con_ventas = e["demanda"]["equivalentes_con_ventas"]
    if con_ventas == 0:
        riesgos.append("ningún equivalente vendió: el precio no lo pagó nadie todavía")
    elif con_ventas == 1:
        riesgos.append("el precio sale de una sola publicación con ventas")
    return {"riesgos": riesgos, "evidencia": e}

