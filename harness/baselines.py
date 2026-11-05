"""Dos formas de proponer qué traer SIN LLM. Pasan por el mismo embudo; si el LLM no les
gana, el LLM sobra.

B1 · Queja más frecuente: la palabra que más se repite en los textos insatisfechos, y
     "traer una versión que la resuelva". Es lo que daría un análisis de palabras.
B2 · Pedidos de repuesto: si 2 o más preguntas piden un repuesto, "traer el repuesto".
     Es una regla fuerte, escrita después de leer dev: test la juzga.
"""

from __future__ import annotations

import re
from collections import Counter

from harness.voces import expresa_insatisfaccion, sin_acentos, textos_con_id

PALABRAS_VACIAS = set("""que de la el en y a los las un una lo con para por es no se muy mas pero me le
su al del como esta este son fue tiene ya si porque producto bien todo hay cuando""".split())
PIDE_REPUESTO = re.compile(r"repuesto|respuesto|por separado|venden (los|las|el|la)\b|se consigue")
MIN_PREGUNTAS_QUE_PIDEN_REPUESTO = 2

# B1 no nombra un producto cotizable ("una versión que resuelva 'material'"), así que no tiene
# precio de proveedor. B2 usa el del mismo repuesto que propuso el LLM: lo más favorable para B2.
FOB_DEL_REPUESTO = {"afilador": "O1", "minipimer": "O4", "estante": "O6"}


def b1_queja_mas_frecuente(producto: dict) -> tuple[dict, dict, str | None]:
    conteo = Counter()
    for t in textos_con_id(producto).values():
        if expresa_insatisfaccion(t):
            conteo.update(w for w in set(re.findall(r"[a-z]{4,}", sin_acentos(t))) if w not in PALABRAS_VACIAS)
    # Desempate alfabético para que el resultado no dependa del orden interno de Python.
    queja = min(conteo.items(), key=lambda kv: (-kv[1], kv[0]))[0] if conteo else ""
    señal = {"id": "B1", "descripcion": f"queja más frecuente: '{queja}'", "palabras_clave": [queja] if queja else []}
    oportunidad = {"id": "B1", "que_traer": f"versión del producto ancla que resuelva la queja '{queja}'",
                   "busqueda_ml": producto["busqueda"],
                   "criterio_equivalencia": {"todos": [[producto["busqueda"].split()[0]]]}}
    return señal, oportunidad, None


def b2_pedidos_de_repuesto(producto: dict) -> tuple[dict, dict, str | None] | None:
    textos = textos_con_id(producto)
    pedidos = [i for i, t in textos.items() if i.startswith("p") and PIDE_REPUESTO.search(sin_acentos(t.split(" || ")[0]))]
    if len(pedidos) < MIN_PREGUNTAS_QUE_PIDEN_REPUESTO:
        return None
    nucleo = producto["busqueda"].split()[0]
    señal = {"id": "B2", "descripcion": "preguntas que piden repuesto", "palabras_clave": ["repuesto", "respuesto", "por separado"]}
    oportunidad = {"id": "B2", "que_traer": f"repuesto de {producto['busqueda']}",
                   "busqueda_ml": f"repuesto {producto['busqueda']}",
                   "criterio_equivalencia": {"empieza_con": ["repuesto", "kit", "pack", "juego"], "todos": [[nucleo]]}}
    return señal, oportunidad, FOB_DEL_REPUESTO.get(nucleo)
