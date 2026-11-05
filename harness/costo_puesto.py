"""Costo puesto en Argentina y margen vendiendo en Mercado Libre.

Para un importador Responsable Inscripto: el IVA de importación y las percepciones son
crédito fiscal o pago a cuenta (afectan la caja, no el costo). Todos los supuestos están
acá arriba, con su fuente; los inciertos se prueban en un rango (bajo / base / alto).

Lo usa C5 en harness/serendipia.py. Los FOB de cada oportunidad están en
data/serendipia/fob_<fecha>.json.

Costo puesto por unidad (USD) = FOB + logística integral por m3 x volumen
                                + derecho de importación + tasa de estadística (sobre CIF)
Ingreso neto por unidad (ARS) = precio / 1,21 (IVA) - comisión ML - envío - IIBB
"""

from __future__ import annotations

# --- Supuestos generales (05/11/2026) ---------------------------------------------------
TIPO_CAMBIO = 1570          # ARS por USD, BNA venta 05/11/2026 (Ámbito)
LOGISTICA_M3 = 450          # USD/m3 integral LCL China->CABA con despacho y entrega (GSI); mínimo 1 m3
FLETE_M3_PARA_CIF = 200     # USD/m3 de flete marítimo dentro de la tarifa, para armar el CIF (DTFU: 180-280 para 1-3 m3)
SEGURO = 0.01               # 1% del FOB
TASA_ESTADISTICA = 0.03     # 3% del CIF (Decreto 1140/2024; Chilat)
COMISION_ML = 0.14          # Premium Hogar 13-15% (Jaguar Sheet)
IIBB = 0.035                # Ingresos Brutos sobre la venta neta (supuesto, varía por jurisdicción)
EMBALAJE = 1.15             # volumen extra por caja master
# ----------------------------------------------------------------------------------------


def costo_puesto_usd(fob: float, die: float, vol: float, unidades_lote: int | None = None) -> dict:
    """Si se da `unidades_lote`, la logística se reparte con el mínimo de 1 m3 por embarque."""
    vol = vol * EMBALAJE
    vol_cobrado = vol if unidades_lote is None else max(1.0, vol * unidades_lote) / unidades_lote
    cif = fob * (1 + SEGURO) + FLETE_M3_PARA_CIF * vol_cobrado
    derechos = cif * die
    estadistica = cif * TASA_ESTADISTICA
    logistica = LOGISTICA_M3 * vol_cobrado
    total = fob + logistica + derechos + estadistica
    return {"fob": fob, "logistica": round(logistica, 2), "derechos": round(derechos, 2),
            "estadistica": round(estadistica, 2), "total": round(total, 2)}


def ingreso_neto_ars(precio: float, envio: float) -> float:
    neto_iva = precio / 1.21
    return neto_iva - precio * COMISION_ML - envio - neto_iva * IIBB
