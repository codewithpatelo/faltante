"""Costo puesto en Argentina y margen vendiendo en Mercado Libre.

Para un importador Responsable Inscripto: el IVA de importación y las percepciones son
crédito fiscal o pago a cuenta (afectan la caja, no el costo). Todos los supuestos están
acá arriba, con su fuente; los inciertos se prueban en un rango (bajo / base / alto).

Costo puesto por unidad (USD) = FOB + logística integral por m3 x volumen
                                + derecho de importación + tasa de estadística (sobre CIF)
Ingreso neto por unidad (ARS) = precio / 1,21 (IVA) - comisión ML - envío - IIBB
"""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class Producto:
    nombre: str
    fob: tuple[float, float, float]        # USD por unidad: bajo, base, alto
    die: tuple[float, float]               # derecho de importación: base, alto
    volumen_m3: float                      # por unidad, embalaje individual
    envio_ars: float                       # costo de envío gratis a cargo del vendedor, por unidad
    precios_ars: dict[str, float]          # escenarios de precio de venta
    fuentes: str = ""


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


def evaluar(p: Producto, unidades_lote: int | None = None) -> dict:
    escenarios = {}
    for etiqueta_costo, fob, die in (("optimista", p.fob[0], p.die[0]), ("base", p.fob[1], p.die[0]), ("pesimista", p.fob[2], p.die[1])):
        c = costo_puesto_usd(fob, die, p.volumen_m3, unidades_lote)
        costo_ars = c["total"] * TIPO_CAMBIO
        fila = {"costo_puesto_usd": c, "costo_puesto_ars": round(costo_ars)}
        for nombre, precio in p.precios_ars.items():
            neto = ingreso_neto_ars(precio, p.envio_ars)
            fila[nombre] = {"precio": precio, "ingreso_neto": round(neto), "margen_ars": round(neto - costo_ars),
                            "margen_pct_sobre_costo": round((neto - costo_ars) / costo_ars * 100)}
        escenarios[etiqueta_costo] = fila
    unidades_min = int(1 / (p.volumen_m3 * EMBALAJE))   # cuántas entran en el mínimo de 1 m3
    return {"producto": p.nombre, "unidades_lote": unidades_lote or "lleno (1 m3 o más)", "escenarios": escenarios, "unidades_en_1_m3": unidades_min,
            "capital_lote_minimo_ars": round(unidades_min * costo_puesto_usd(p.fob[1], p.die[0], p.volumen_m3)["total"] * TIPO_CAMBIO)}


PRODUCTOS = [
    Producto(
        "Afilador de cuchillos rodante (rodillo + base magnética)",
        fob=(3.44, 5.50, 12.0), die=(0.18, 0.35), volumen_m3=0.147 * 0.125 * 0.06, envio_ars=6500,
        precios_ars={"igual_a_compra_internacional": 21838, "debajo_de_los_locales": 35000, "mediana_locales": 49800},
        fuentes="Alibaba showroom 'knife sharpener magnetic roller': USD 3,44-12 según proveedor; caja 14,7x12,5x6 cm. "
                "DIE: AEC 18% en 8205.51/8205.59 (Marimpex); se prueba 35% por si Argentina tiene excepción.",
    ),
    Producto(
        "Set de 5 recipientes herméticos de acero inoxidable",
        fob=(1.04, 1.69, 7.02), die=(0.35, 0.35), volumen_m3=0.11 * 0.11 * 0.18, envio_ars=6500,
        precios_ars={"igual_a_compra_internacional": 14063, "intermedio": 25000, "mediana_locales": 48400},
        fuentes="Alibaba: USD 0,99-1,58 (5 pcs, silicona), USD 1,69-1,81 (XH-9073, 11x11x18 cm, 0,76 kg), "
                "USD 7,02-8,31 (Lekfre, calidad alta). DIE 35% en 7323.93 (ARCA vía Indicator Gateway).",
    ),
    Producto(
        "Tostador abierto de calor superior / salamandra eléctrica de mesada",
        fob=(167, 190, 216), die=(0.20, 0.20), volumen_m3=0.60 * 0.45 * 0.35, envio_ars=18000,
        precios_ars={"agresivo": 120000, "debajo_de_speedy_grill": 150000, "precio_speedy_grill_hoy": 242347},
        fuentes="Alibaba showroom 'commercial salamander broiler': USD 167-216 (eléctrica, modelo comercial). "
                "DIE 20% en 8516.72 (Marimpex, ARCA 20/10/2026). Volumen supuesto 60x45x35 cm.",
    ),
]


if __name__ == "__main__":
    import json
    from pathlib import Path
    salida = [evaluar(p) for p in PRODUCTOS] + [evaluar(p, 200) for p in PRODUCTOS[:2]]
    destino = Path(__file__).resolve().parent.parent / "data/cross_border/costo_puesto_2026-11-05.json"
    destino.write_text(json.dumps({"supuestos": {"tipo_cambio": TIPO_CAMBIO, "logistica_usd_m3": LOGISTICA_M3, "flete_m3_cif": FLETE_M3_PARA_CIF,
        "seguro": SEGURO, "tasa_estadistica": TASA_ESTADISTICA, "comision_ml": COMISION_ML, "iibb": IIBB, "embalaje": EMBALAJE},
        "fuentes": {p.nombre: p.fuentes for p in PRODUCTOS}, "resultados": salida}, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in salida:
        print(f"\n## {r['producto']} | lote: {r['unidades_lote']} | capital lote lleno ${r['capital_lote_minimo_ars']:,}")
        for esc, f in r["escenarios"].items():
            precios = " | ".join(f"{k} ${v['precio']:,}: {v['margen_pct_sobre_costo']}%" for k, v in f.items() if isinstance(v, dict) and "precio" in v)
            print(f"  {esc:<9} costo ${f['costo_puesto_ars']:,} | {precios}")
