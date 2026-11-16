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
"""

from __future__ import annotations

import json
import os
import sys

from harness.modelo import DeepSeek, con_reintento, costo, en_paralelo
from harness.voces import RAIZ

SKILL = RAIZ / "skills/juzgar_equivalencia/SKILL.md"
ARCHIVO = RAIZ / "data/serendipia/equivalencias.json"


def clave(que_traer: str, busqueda: str) -> str:
    return f"{busqueda} || {que_traer}"


def guardadas() -> dict[str, list[str]]:
    return json.loads(ARCHIVO.read_text(encoding="utf-8")) if ARCHIVO.exists() else {}


def juzgar(cliente, que_traer: str, para_que: str, publicaciones: list[dict], traza: list) -> list[str]:
    """Los títulos de `publicaciones` que reemplazan a lo propuesto."""
    lineas = "\n".join(f"[{i}] {x['titulo']} | ${x.get('precio') or '?'}" for i, x in enumerate(publicaciones))
    prompt = (f"{SKILL.read_text(encoding='utf-8')}\n\n---\n\nPROPUESTA: {que_traer}\nPARA QUÉ: {para_que}\n\n"
              f"PUBLICACIONES\n{lineas}\n\nRespondé SOLO con el JSON de la salida.")
    validar = lambda d: {} if all(isinstance(i, int) and 0 <= i < len(publicaciones) for i in d.get("equivalentes", [])) \
        else {"equivalentes": ["índices fuera de la lista"]}
    d = con_reintento(cliente, prompt, validar, traza, f"equivalencia {que_traer[:30]}")
    return sorted({publicaciones[i]["titulo"] for i in d.get("equivalentes", []) if isinstance(i, int) and 0 <= i < len(publicaciones)})


def pendientes(propuestas) -> dict[str, tuple]:
    """Las propuestas con búsqueda capturada que todavía no tienen juicio, sin repetir."""
    hechas, salida = guardadas(), {}
    for p in propuestas:
        k = clave(p.oportunidad["que_traer"], p.oportunidad["busqueda_ml"])
        if p.captura is not None and k not in hechas:
            salida[k] = (p.oportunidad["que_traer"], p.oportunidad.get("alivia") or p.oportunidad.get("para_quien", ""),
                         [x for x in p.captura["publicaciones"] if x["titulo"]])
    return salida


if __name__ == "__main__":
    from harness.correr import propuestas_de_un_archivo
    cliente, traza = DeepSeek(os.environ["DEEPSEEK_API_KEY"]), []
    todas = {k: v for archivo in sys.argv[1:] for k, v in pendientes(propuestas_de_un_archivo(archivo)).items()}
    def juzgar_o_dejar(k):
        """Si la API falla después de los reintentos, esa propuesta queda sin juzgar (se juzga en la
        corrida siguiente) en vez de perder todo lo juzgado."""
        try:
            return juzgar(cliente, *todas[k], traza)
        except Exception as e:  # noqa: BLE001
            print(f"sin juzgar ({type(e).__name__}): {k}", file=sys.stderr)
            return None
    juicios = {k: v for k, v in zip(todas, en_paralelo(juzgar_o_dejar, list(todas))) if v is not None}
    destino = RAIZ / "resultados" / "equivalencias_nuevas.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(juicios, ensure_ascii=False), encoding="utf-8")
    print(f"{len(juicios)} de {len(todas)} propuestas juzgadas, {costo(traza)}")
