"""Qué publicaciones ya son lo que se propone (lo usan C4, C5 y C6). Lo juzga quien no propuso.

Antes el criterio de equivalencia lo escribía el mismo LLM que proponía, con palabras del título,
y a veces dejaba afuera lo obvio (para "saca pelos de mascotas de tapizados" no contaba el
"Quita Pelo Mascota Ropa Tapizados" que vende +10.000): la propuesta sobrevivía C4 porque su autor
definía qué era competencia. Ahora otro modelo, que solo ve qué se propone, para qué, y las
publicaciones de la búsqueda (skills/juzgar_equivalencia), dice cuáles la reemplazan. Las
publicaciones ancla se sacan antes (no compiten con lo que se les ocurrió a sus compradores).

Se corre después de capturar las búsquedas y queda guardado (data/serendipia/equivalencias.json,
solo se agrega): el embudo lo lee y no llama a la API.

    DEEPSEEK_API_KEY=... python -m harness.equivalencias data/serendipia/divergente_escala_dev_api.json
    MODELO_JUEZ=claude-... python -m harness.equivalencias data/serendipia/divergente_escala_dev_api__juez-claude-....json
    (otro juez: juzga todo lo que él no juzgó y lo agrega a equivalencias__<modelo>.json, que el embudo lee cuando
    el nombre de la salida termina en __juez-<modelo>; equivalencias.json, el de DeepSeek, no se toca)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from harness.modelo import MODELO, clientes, con_reintento, costo, en_paralelo, sufijo
from harness.voces import RAIZ

SKILL = RAIZ / "skills/juzgar_equivalencia/SKILL.md"
ARCHIVO = RAIZ / "data/serendipia/equivalencias.json"


def clave(que_traer: str, busqueda: str) -> str:
    return f"{busqueda} || {que_traer}"


def archivo_de(juez: str | None = None) -> Path:
    """Donde están los juicios de ese juez: `equivalencias.json` para DeepSeek Flash, `equivalencias__<modelo>.json` para otro."""
    return RAIZ / f"data/serendipia/equivalencias{sufijo(juez) if juez else ''}.json"


def juez_de(archivo) -> str | None:
    """Quién juzgó lo de una salida de la divergencia, según su nombre (`..._api__juez-<modelo>.json`); None si DeepSeek Flash."""
    m = re.search(r"__juez-(.+)\.json$", Path(archivo).name)
    return m.group(1) if m else None


def guardadas(juez: str | None = None) -> dict[str, list[str]]:
    archivo = archivo_de(juez)
    return json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}


def juzgar(cliente, que_traer: str, para_que: str, publicaciones: list[dict], traza: list) -> list[str]:
    """Los títulos de `publicaciones` que reemplazan a lo propuesto."""
    lineas = "\n".join(f"[{i}] {x['titulo']} | ${x.get('precio') or '?'}" for i, x in enumerate(publicaciones))
    prompt = (f"{SKILL.read_text(encoding='utf-8')}\n\n---\n\nPROPUESTA: {que_traer}\nPARA QUÉ: {para_que}\n\n"
              f"PUBLICACIONES\n{lineas}\n\nRespondé SOLO con el JSON de la salida.")
    validar = lambda d: {} if all(isinstance(i, int) and 0 <= i < len(publicaciones) for i in d.get("equivalentes", [])) \
        else {"equivalentes": ["índices fuera de la lista"]}
    d = con_reintento(cliente, prompt, validar, traza, f"equivalencia {que_traer[:30]}")
    return sorted({publicaciones[i]["titulo"] for i in d.get("equivalentes", []) if isinstance(i, int) and 0 <= i < len(publicaciones)})


def pendientes(propuestas, juez: str | None = None) -> dict[str, tuple]:
    """Las propuestas con búsqueda capturada que todavía no tienen juicio de ese juez, sin repetir."""
    hechas, salida = guardadas(juez), {}
    for p in propuestas:
        k = clave(p.oportunidad["que_traer"], p.oportunidad["busqueda_ml"])
        if p.captura is not None and k not in hechas:
            salida[k] = (p.oportunidad["que_traer"], p.oportunidad.get("alivia") or p.oportunidad.get("para_quien", ""),
                         [x for x in p.captura["publicaciones"] if x["titulo"]])
    return salida


if __name__ == "__main__":
    from harness.correr import propuestas_de_un_archivo
    cliente, traza = clientes()[1], []   # el que juzga: MODELO_JUEZ, o MODELO_LLM si no hay
    for archivo in sys.argv[1:]:
        if (juez_de(archivo) or MODELO) != cliente.modelo:
            raise SystemExit(f"{archivo} se juzga con {juez_de(archivo) or MODELO}, no con {cliente.modelo} (MODELO_JUEZ)")
    aparte = cliente.modelo != MODELO
    todas = {k: v for archivo in sys.argv[1:]
             for k, v in pendientes(propuestas_de_un_archivo(archivo), cliente.modelo if aparte else None).items()}
    def juzgar_o_dejar(k):
        """Si la API falla después de los reintentos, esa propuesta queda sin juzgar (se juzga en la
        corrida siguiente) en vez de perder todo lo juzgado."""
        try:
            return juzgar(cliente, *todas[k], traza)
        except Exception as e:  # noqa: BLE001
            print(f"sin juzgar ({type(e).__name__}): {k}", file=sys.stderr)
            return None
    juicios = {k: v for k, v in zip(todas, en_paralelo(juzgar_o_dejar, list(todas))) if v is not None}
    if aparte:    # otro juez: su propio archivo, solo se agrega; el de DeepSeek no se toca
        destino = archivo_de(cliente.modelo)
        destino.write_text(json.dumps({**guardadas(cliente.modelo), **juicios}, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        destino = RAIZ / "resultados" / "equivalencias_nuevas.json"
        destino.parent.mkdir(exist_ok=True)
        destino.write_text(json.dumps(juicios, ensure_ascii=False), encoding="utf-8")
    print(f"{len(juicios)} de {len(todas)} propuestas juzgadas, {costo(traza, cliente.modelo)}")
