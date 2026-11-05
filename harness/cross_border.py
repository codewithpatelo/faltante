"""Demanda probada por Compra Internacional: ¿hay lugar para traerlo con stock local?

El voto con los pies más fuerte a favor de importar es comprar por Compra Internacional:
la persona paga y además espera semanas. Si un producto así vende, la demanda está probada
con fricción. Ya vimos (diagnóstico) que la espera pesa: donde hay stock local, se elige el
local. Entonces, para cada producto internacional que vende, buscamos su equivalente con
stock local (el emparejamiento lo hace el LLM) y decidimos:

- `oportunidad`: no hay equivalente local que venda, o el local que vende cuesta bastante más.
- `ya_atendido`: hay equivalente local que vende a precio parecido o menor.
- `insuficiente`: el producto internacional vende poco para afirmar algo.

Umbrales a la vista.
"""

from __future__ import annotations

from statistics import median

VENTAS_MIN_INTL = 100        # piso del contador para decir "demanda probada"
RATIO_LOCAL_CARO = 1.3       # local que vende 1,3x o más caro que el internacional: no compite


def evaluar(intl: dict, locales_equivalentes: list[dict]) -> dict:
    """`intl`: la publicación internacional que vende. `locales_equivalentes`: publicaciones
    locales que el emparejamiento marcó como el mismo producto o equivalente directo."""
    if intl["vendidos"] < VENTAS_MIN_INTL:
        return {"veredicto": "insuficiente", "motivo": f"el internacional muestra +{intl['vendidos']}, debajo de {VENTAS_MIN_INTL}"}
    venden = [p for p in locales_equivalentes if p["vendidos"] > 0 and p.get("precio")]
    if not venden:
        return {"veredicto": "oportunidad", "motivo": f"+{intl['vendidos']} por Compra Internacional y ningún equivalente local que venda ({len(locales_equivalentes)} publicados)"}
    pl = median(p["precio"] for p in venden)
    ratio = round(pl / intl["precio"], 2) if intl.get("precio") else None
    if ratio and ratio >= RATIO_LOCAL_CARO:
        return {"veredicto": "oportunidad", "ratio_local_intl": ratio,
                "motivo": f"el local que vende cuesta {ratio}x el internacional (${int(pl):,} vs ${intl['precio']:,})"}
    return {"veredicto": "ya_atendido", "ratio_local_intl": ratio,
            "motivo": f"{len(venden)} equivalentes locales venden a ${int(pl):,} (ratio {ratio})"}
