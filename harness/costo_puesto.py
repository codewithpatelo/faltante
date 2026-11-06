"""Costo puesto en Argentina y margen vendiendo en Mercado Libre.

Para un importador Responsable Inscripto: el IVA de importación y las percepciones son
crédito fiscal o pago a cuenta (afectan la caja, no el costo). Todos los supuestos están
acá arriba, con su fuente; los inciertos se prueban en un rango (bajo / base / alto).

Lo usa C6 (harness/chequeos.py). Los FOB de cada oportunidad están en
data/serendipia/fob_<fecha>.json.

Costo puesto por unidad (USD) = FOB + logística integral por m3 x volumen
                                + derecho de importación + tasa de estadística (sobre CIF)
Ingreso neto por unidad (ARS) = (precio / 1,21 (IVA) - comisión ML - envío - IIBB - publicidad)
                                x (1 - devoluciones)

Cada supuesto incierto va como (optimista, base, pesimista), con la fuente de cada extremo. Las
devoluciones se cuentan como unidad perdida (cota conservadora: no se revende).
"""

from __future__ import annotations

# --- Supuestos generales (05/11/2026) ---------------------------------------------------
TIPO_CAMBIO = 1570          # ARS por USD, BNA venta 05/11/2026 (Ámbito)
LOGISTICA_M3 = 450          # USD/m3 integral LCL China->CABA con despacho y entrega (GSI); mínimo 1 m3
FLETE_M3_PARA_CIF = 200     # USD/m3 de flete marítimo dentro de la tarifa, para armar el CIF (DTFU: 180-280 para 1-3 m3)
TASA_ESTADISTICA = 0.03     # 3% del CIF (Decreto 1140/2024; Chilat)
EMBALAJE = 1.15             # volumen extra por caja master (PENDIENTE de fuente)
ESCENARIOS = ("optimista", "base", "pesimista")
SEGURO = (0.003, 0.004, 0.005)       # prima sobre CIF + 10%, carga marítima general 0,3-0,5% (Suaid Global)
COMISION_ML = (0.13, 0.14, 0.15)     # Premium Hogar 13-15% del precio (Jaguar Sheet)
IIBB = (0.03, 0.04, 0.05)            # sobre la venta neta de IVA; PENDIENTE de la Ley Tarifaria vigente (3-5% según actividad y facturación)
PUBLICIDAD = (0.12, 0.18, 0.25)      # Product Ads, ACOS Hogar 12-25%, "bueno" < 18% (Jaguar Sheet); se cobra sobre todas las ventas (producto nuevo, sin ventas orgánicas)
DEVOLUCIONES = (0.05, 0.05, 0.20)    # 5%: tasa de referencia para vendedores de ML (Jaguar Sheet); 20%: e-commerce en general (SaleCycle/Red Stag)
# ----------------------------------------------------------------------------------------


def costo_puesto_usd(fob: float, die: float, vol: float, unidades_lote: int | None = None, escenario: int = 1) -> dict:
    """Si se da `unidades_lote`, la logística se reparte con el mínimo de 1 m3 por embarque."""
    vol = vol * EMBALAJE
    vol_cobrado = vol if unidades_lote is None else max(1.0, vol * unidades_lote) / unidades_lote
    cif = fob * (1 + SEGURO[escenario] * 1.1) + FLETE_M3_PARA_CIF * vol_cobrado
    derechos = cif * die
    estadistica = cif * TASA_ESTADISTICA
    logistica = LOGISTICA_M3 * vol_cobrado
    total = fob + logistica + derechos + estadistica
    return {"fob": fob, "logistica": round(logistica, 2), "derechos": round(derechos, 2),
            "estadistica": round(estadistica, 2), "total": round(total, 2)}


def ingreso_neto_ars(precio: float, envio: float, escenario: int = 1) -> float:
    neto_iva = precio / 1.21
    neto = neto_iva - precio * COMISION_ML[escenario] - envio - neto_iva * IIBB[escenario] - precio * PUBLICIDAD[escenario]
    return neto * (1 - DEVOLUCIONES[escenario])
