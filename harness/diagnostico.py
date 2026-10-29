"""Diagnóstico: ¿por qué un producto con demanda afuera no se vende acá?

Entrada, por producto, una foto de la primera página de búsqueda en Mercado Libre donde
cada publicación ya viene marcada como "es el producto" o "es otra cosa" (sustituto).
Esa marca la decide el emparejamiento (en el sistema, el LLM).

Cuatro chequeos compiten por explicar la falta de ventas. Cada uno devuelve:
    "explica" | "descarta" | "no_se_puede_saber"  + la evidencia numérica que lo sostiene.

Los umbrales están arriba, a la vista, porque son decisiones discutibles y hay que poder
defenderlas en la exposición.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

# --- Umbrales -------------------------------------------------------------------------
DEMANDA_MINIMA = 100          # ventas visibles en toda la búsqueda para decir "hay demanda"
RATIO_CARO = 1.5              # el producto cuesta 1,5x o más que los sustitutos que venden
RATIO_COMPARABLE = 1.2        # hasta 1,2x se considera "precio parecido"
# --------------------------------------------------------------------------------------


@dataclass
class Publicacion:
    titulo: str
    internacional: bool
    vendidos: int            # piso del contador "+N vendidos"; 0 si no muestra
    precio: int | None       # ARS
    es_producto: bool        # decidido por el emparejamiento


@dataclass
class Foto:
    busqueda: str
    publicaciones: list[Publicacion] = field(default_factory=list)

    def _sel(self, producto: bool | None = None, intl: bool | None = None, vende: bool | None = None):
        out = self.publicaciones
        if producto is not None:
            out = [p for p in out if p.es_producto == producto]
        if intl is not None:
            out = [p for p in out if p.internacional == intl]
        if vende is not None:
            out = [p for p in out if (p.vendidos > 0) == vende]
        return out


def _mediana(pubs):
    precios = [p.precio for p in pubs if p.precio]
    return int(median(precios)) if precios else None


def _resumen(f: Foto) -> dict:
    """Los números que usan los cuatro chequeos, calculados una vez."""
    return {
        "producto_local": len(f._sel(True, False)),
        "producto_local_vende": len(f._sel(True, False, True)),
        "producto_intl": len(f._sel(True, True)),
        "producto_intl_vende": len(f._sel(True, True, True)),
        "precio_producto_local": _mediana(f._sel(True, False)),
        "precio_producto_intl": _mediana(f._sel(True, True)),
        "sustitutos_que_venden": len(f._sel(False, None, True)),
        "precio_sustitutos_que_venden": _mediana(f._sel(False, None, True)),
        "ventas_visibles_total": sum(p.vendidos for p in f.publicaciones),
        "ventas_producto": sum(p.vendidos for p in f._sel(True)),
    }


# --- Los cuatro chequeos ---------------------------------------------------------------

def chequear_demanda(r: dict) -> dict:
    """¿Alguien compra este tipo de producto acá? Si nadie compra nada en la búsqueda, no
    hace falta explicar más."""
    if r["ventas_visibles_total"] < DEMANDA_MINIMA:
        return {"resultado": "explica", "motivo": f"solo {r['ventas_visibles_total']} ventas visibles en toda la búsqueda"}
    return {"resultado": "descarta", "motivo": f"{r['ventas_visibles_total']} ventas visibles en la búsqueda"}


def chequear_precio(r: dict) -> dict:
    """¿El producto sale bastante más caro que lo que la gente sí compra?"""
    ps = r["precio_sustitutos_que_venden"]
    pp = r["precio_producto_intl"] or r["precio_producto_local"]
    if not ps or not pp:
        return {"resultado": "no_se_puede_saber", "motivo": "falta precio del producto o de sustitutos que venden"}
    ratio = round(pp / ps, 2)
    if ratio >= RATIO_CARO:
        return {"resultado": "explica", "ratio": ratio, "motivo": f"el producto cuesta {ratio}x lo que se compra (${pp:,} vs ${ps:,})"}
    return {"resultado": "descarta", "ratio": ratio, "motivo": f"precio parecido o menor ({ratio}x: ${pp:,} vs ${ps:,})"}


def chequear_espera(r: dict) -> dict:
    """¿La gente no compra porque tiene que esperar el envío de afuera?

    Evidencia directa solo cuando el mismo producto está en stock local Y por internacional:
    si el local vende y el internacional no, a precio parecido o menor, lo que se paga es no
    esperar. Si además hay internacionales que venden, hay gente que acepta la espera:
    también es evidencia (de que el producto se quiere aunque haya que esperar)."""
    if r["producto_intl_vende"] > 0:
        return {"resultado": "descarta", "motivo": f"{r['producto_intl_vende']} publicaciones internacionales del producto venden: hay gente que acepta esperar",
                "voto_con_friccion": True}
    if r["producto_local_vende"] == 0 or r["producto_intl"] == 0:
        return {"resultado": "no_se_puede_saber", "motivo": "no está a la vez en stock local con ventas y por internacional"}
    pl, pi = r["precio_producto_local"], r["precio_producto_intl"]
    if pl and pi and pi <= pl * RATIO_COMPARABLE:
        return {"resultado": "explica", "motivo": f"el local vende y el internacional no, aun costando ${pi:,} contra ${pl:,}"}
    return {"resultado": "no_se_puede_saber", "motivo": "el internacional además es más caro: espera y precio se confunden"}


def chequear_preferencia_local(r: dict) -> dict:
    """¿Prefieren otras opciones aunque el producto esté en stock y a precio parecido?

    Solo se puede afirmar si el producto está en stock local (así no hay espera), a precio
    comparable con los sustitutos, y aun así no vende mientras los sustitutos sí."""
    if r["producto_local"] == 0:
        return {"resultado": "no_se_puede_saber", "motivo": "el producto no está en stock local: no se puede separar de la espera"}
    pl, ps = r["precio_producto_local"], r["precio_sustitutos_que_venden"]
    if r["producto_local_vende"] == 0 and r["sustitutos_que_venden"] > 0 and pl and ps and pl <= ps * RATIO_COMPARABLE:
        return {"resultado": "explica", "motivo": f"en stock local a ${pl:,}, parecido a los ${ps:,} de lo que se vende, y no vende"}
    return {"resultado": "descarta", "motivo": "el producto en stock local vende, o es más caro (lo explica el precio)"}


CHEQUEOS = {
    "demanda": chequear_demanda,
    "precio": chequear_precio,
    "espera": chequear_espera,
    "preferencia_local": chequear_preferencia_local,
}


def diagnosticar(f: Foto) -> dict:
    r = _resumen(f)
    res = {k: fn(r) for k, fn in CHEQUEOS.items()}
    # El orden importa: un producto que ya vende con stock local no es un hueco, aunque el
    # chequeo de espera explique por qué su versión internacional no vende.
    if r["producto_local_vende"] > 0:
        conclusion = "ya_atendido"
    elif res["demanda"]["resultado"] == "explica":
        conclusion = "sin_demanda"
    elif res["espera"].get("voto_con_friccion"):
        conclusion = "oportunidad_compran_aunque_esperen"
    elif res["precio"]["resultado"] == "explica":
        conclusion = "no_compite_en_precio"
    elif res["preferencia_local"]["resultado"] == "explica":
        conclusion = "prefieren_otras_opciones"
    else:
        # Sin stock local, a precio comparable y sin ventas: puede ser la espera (oportunidad)
        # o que prefieran otra cosa (no). Estos datos no alcanzan para separarlo.
        conclusion = "candidato_a_probar"
    return {"busqueda": f.busqueda, "resumen": r, "chequeos": res, "conclusion": conclusion}
