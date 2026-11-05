"""Los chequeos con los que el programa intenta matar cada propuesta.

Cada chequeo recibe una propuesta y devuelve un Resultado: si pasa, por qué, y los datos
que lo sostienen. El orden y la descripción de cada uno están en `harness/embudo.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from harness import costo_puesto as cp
from harness import umbrales as U
from harness.voces import expresa_insatisfaccion, sin_acentos


@dataclass
class Resultado:
    pasa: bool
    motivo: str
    datos: dict = field(default_factory=dict)
    condicional: bool = False   # no pasa del todo, pero pasaría si se cumple una condición (C5: un FOB)


# --- Sobre las señales que cita la propuesta ---------------------------------------------

def errores_de_citas(señal: dict, textos: dict[str, str]) -> list[str]:
    """Guardrail: el LLM no puede citar textos que no existen ni inventar fragmentos, y una
    señal tiene que venir de al menos 2 textos distintos."""
    errores, citas = [], señal.get("citas") or []
    if len({c.get("texto") for c in citas}) < 2:
        errores.append("tiene que citar al menos 2 textos distintos")
    for c in citas:
        texto = textos.get(c.get("texto"))
        if texto is None:
            errores.append(f"cita un texto que no existe: {c.get('texto')}")
        elif len(c.get("fragmento", "")) < 4 or sin_acentos(c["fragmento"]) not in sin_acentos(texto):
            errores.append(f"[{c.get('texto')}] el fragmento no está en el texto")
    if not señal.get("palabras_clave"):
        errores.append("faltan palabras_clave para que el programa cuente")
    return errores


def medir(señal: dict, textos: dict[str, str]) -> dict:
    """Cuenta la señal en TODOS los textos del producto, no solo en los que leyó el LLM, y
    calcula el puntaje de oportunidad de Ulwick: importancia + máx(importancia − satisfacción, 0)."""
    claves = [sin_acentos(p) for p in señal.get("palabras_clave", [])]
    menciones = [t for t in textos.values() if any(k in sin_acentos(t) for k in claves)]
    insatisfechas = sum(1 for t in menciones if expresa_insatisfaccion(t))
    proporcion = len(menciones) / max(1, len(textos))
    importancia = round(min(10.0, 10 * proporcion / U.PROPORCION_PARA_IMPORTANCIA_10), 1)
    satisfaccion = round(10 * (1 - insatisfechas / len(menciones)), 1) if menciones else 10.0
    return {"menciones": len(menciones), "insatisfechas": insatisfechas, "de_textos": len(textos),
            "importancia": importancia, "satisfaccion": satisfaccion,
            "puntaje_oportunidad": round(importancia + max(importancia - satisfaccion, 0), 1)}


def es_verificada(m: dict) -> bool:
    return m["menciones"] >= U.MIN_TEXTOS_CON_LA_SEÑAL


def es_subatendida(m: dict) -> bool:
    return m["importancia"] >= U.MIN_IMPORTANCIA and m["satisfaccion"] <= U.MAX_SATISFACCION


# --- Chequeos ------------------------------------------------------------------------------

def guardrail(p) -> Resultado:
    if not p.verifica_citas:
        return Resultado(True, "los baselines no citan textos")
    buenas = [s for s in p.señales if not s["errores"]]
    errores = [e for s in p.señales for e in s["errores"]]
    return Resultado(bool(buenas), "citas verificadas" if buenas else "; ".join(errores))


def c1_verificada(p) -> Resultado:
    mejor = max((s["medida"]["menciones"] for s in p.señales_validas), default=0)
    return Resultado(any(es_verificada(s["medida"]) for s in p.señales_validas),
                     f"la señal aparece en {mejor} textos (mínimo {U.MIN_TEXTOS_CON_LA_SEÑAL})")


def c2_subatendida(p) -> Resultado:
    ok = [s for s in p.señales_validas if es_verificada(s["medida"]) and es_subatendida(s["medida"])]
    m = (ok or p.señales_validas or [{"medida": {"importancia": 0, "satisfaccion": 10}}])[0]["medida"]
    return Resultado(bool(ok), f"importancia {m['importancia']}, satisfacción {m['satisfaccion']} "
                               f"(hace falta ≥ {U.MIN_IMPORTANCIA} y ≤ {U.MAX_SATISFACCION})")


def c3_demanda(p) -> Resultado:
    v = p.producto["vendidos"]
    return Resultado(v >= U.MIN_VENDIDOS_DEL_ANCLA, f"el producto ancla vende +{v} (mínimo {U.MIN_VENDIDOS_DEL_ANCLA})")


def c4_hueco(p) -> Resultado:
    if p.captura is None:
        return Resultado(False, "falta capturar la búsqueda (scripts/captura_ml.js)")
    eq = equivalentes(p)
    venden = [x for x in eq if x["vendidos"] >= U.VENDIDOS_PARA_DECIR_QUE_YA_VENDE]
    datos = {"equivalentes": len(eq), "venden": len(venden),
             "ejemplos_que_venden": [f"{x['titulo'][:70]} (+{x['vendidos']}, ${x['precio']:,})"
                                     for x in sorted(venden, key=lambda x: -x["vendidos"])[:3]]}
    if len(venden) > U.MAX_EQUIVALENTES_QUE_YA_VENDEN:
        return Resultado(False, f"ya atendido: {len(venden)} equivalentes venden +{U.VENDIDOS_PARA_DECIR_QUE_YA_VENDE}", datos)
    return Resultado(True, f"{len(eq)} equivalentes, {len(venden)} venden +{U.VENDIDOS_PARA_DECIR_QUE_YA_VENDE}", datos)


def c5_margen(p) -> Resultado:
    precio = precio_de_mercado(p)
    if p.fob is None or precio is None:
        return Resultado(False, "sin precio de proveedor o sin precio de mercado")
    m = margen(p.fob, precio)
    base, piso = m["escenarios"]["base"]["margen_pct"], round(U.MIN_MARGEN_SOBRE_COSTO * 100)
    if base >= piso:
        return Resultado(True, f"margen base {base}% a ${precio:,}", m)
    if m["escenarios"]["optimista"]["margen_pct"] >= piso:
        return Resultado(False, f"margen base {base}% a ${precio:,}; pasa si el FOB es ≤ USD {m['fob_maximo_usd']}",
                         m, condicional=True)
    return Resultado(False, f"margen base {base}% a ${precio:,} (haría falta FOB ≤ USD {m['fob_maximo_usd']})", m)


# --- Ayudas de C4 y C5 -----------------------------------------------------------------------

def es_equivalente(titulo: str, criterio: dict) -> bool:
    """En Mercado Libre el título empieza por lo que se vende ("Disco …" es un disco;
    "Afilador … con discos" es un afilador). El criterio lo escribe el LLM:
    empieza_con / no_empieza_con, `todos` (un término de cada grupo) y `excluir`."""
    t = sin_acentos(titulo)
    if any(t.startswith(sin_acentos(e)) for e in criterio.get("no_empieza_con", [])):
        return False
    if criterio.get("empieza_con") and not any(t.startswith(sin_acentos(e)) for e in criterio["empieza_con"]):
        return False
    if any(sin_acentos(x) in t for x in criterio.get("excluir", [])):
        return False
    return all(any(sin_acentos(s) in t for s in grupo) for grupo in criterio.get("todos", []))


def equivalentes(p) -> list[dict]:
    """Publicaciones de la búsqueda que son lo mismo que se propone traer, sin repetidas y
    sin los productos ancla (el ancla no compite con lo que se le ocurrió a sus compradores)."""
    vistos, salida = set(), []
    for x in p.captura["publicaciones"]:
        clave = (sin_acentos(x["titulo"]), x.get("precio"))
        if clave in vistos or clave[0] in p.titulos_ancla:
            continue
        vistos.add(clave)
        if es_equivalente(x["titulo"], p.oportunidad["criterio_equivalencia"]):
            salida.append(x)
    return salida


def precio_de_mercado(p) -> int | None:
    """Lo que la gente paga: mediana de los equivalentes que vendieron algo. Una publicación
    sin ventas puede pedir cualquier precio, así que no cuenta."""
    if p.captura is None:
        return None
    precios = sorted(x["precio"] for x in equivalentes(p) if x.get("precio") and x["vendidos"] > 0)
    return precios[len(precios) // 2] if precios else None


def margen(fob: dict, precio_ars: float) -> dict:
    """Margen sobre costo puesto en tres escenarios (optimista, base, pesimista) y el FOB
    máximo que todavía deja el margen mínimo: es lo que hay que pedirle al proveedor."""
    lote = min(U.UNIDADES_MAX_PRIMER_LOTE, int(1 / (fob["volumen_m3"] * cp.EMBALAJE)))
    envio = U.ENVIO_DEBAJO_DEL_PISO if precio_ars < U.PRECIO_DESDE_EL_QUE_EL_ENVIO_ES_GRATIS else U.ENVIO_ARRIBA_DEL_PISO
    neto = cp.ingreso_neto_ars(precio_ars, envio)
    escenarios = {}
    for nombre, f, die in (("optimista", fob["fob"][0], fob["die"][0]), ("base", fob["fob"][1], fob["die"][0]),
                           ("pesimista", fob["fob"][2], fob["die"][1])):
        costo = cp.costo_puesto_usd(f, die, fob["volumen_m3"], lote)["total"] * cp.TIPO_CAMBIO
        escenarios[nombre] = {"costo_puesto_ars": round(costo), "margen_pct": round((neto - costo) / costo * 100)}
    return {"precio_ars": precio_ars, "ingreso_neto_ars": round(neto), "lote": lote, "envio_ars": envio,
            "escenarios": escenarios, "fob_maximo_usd": fob_maximo(fob, neto, lote)}


def fob_maximo(fob: dict, ingreso_neto_ars: float, lote: int) -> float:
    """Despeja el FOB de costo_puesto_usd para que el costo deje justo el margen mínimo."""
    vol = max(1.0, fob["volumen_m3"] * cp.EMBALAJE * lote) / lote
    impuestos = fob["die"][0] + cp.TASA_ESTADISTICA
    costo_max = ingreso_neto_ars / (1 + U.MIN_MARGEN_SOBRE_COSTO) / cp.TIPO_CAMBIO
    return round((costo_max - cp.LOGISTICA_M3 * vol - cp.FLETE_M3_PARA_CIF * vol * impuestos)
                 / (1 + (1 + cp.SEGURO) * impuestos), 2)

