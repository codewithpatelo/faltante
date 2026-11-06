"""Optimiza las instrucciones de la mejor variante del paso B, al estilo GEPA (Agrawal et al.,
ICLR 2026): en cada ronda el modelo lee POR QUÉ fallaron sus propuestas (obvias, repetidas,
descartadas por el guardrail o C1 a C3), reescribe las instrucciones, y la versión nueva se
queda solo si mejora la medida. Es aprender de feedback en palabras, no de un número. Como el
mismo prompt varía mucho entre corridas, cada versión se mide varias veces (REPETICIONES en
harness/explorar_prompts.py) y se compara el promedio.

    DEEPSEEK_API_KEY=... python -m harness.optimizar_prompt dev   -> data/serendipia/optimizacion_dev.json

Parte de data/serendipia/espacio_<particion>.json (harness/explorar_prompts.py).
"""

from __future__ import annotations

import json
import os
import sys

from harness.divergente import DeepSeek, _con_reintento, costo, señales_del_paso_a, señales_verificadas
from harness.espacio_de_prompts import variantes
from harness.explorar_prompts import SERENDIPIA, medir_repetido
from harness.voces import productos

RONDAS = 4
REFLEXION = """Sos el autor de las instrucciones de un paso de generación de hipótesis: a partir de señales
de consumidores de productos distintos, proponer qué importar que nadie trae y que no sea obvio.

Estas son las instrucciones actuales:
<<<
{instrucciones}
>>>

Con ellas, el modelo propuso esto, y así le fue a cada propuesta:
{feedback}

Puntaje: {no_obvias} propuestas válidas, distintas y no obvias (de {propuestas}).

Diagnosticá qué en las instrucciones produce propuestas obvias, repetidas o inválidas, y qué
produce las buenas. Después reescribí las instrucciones completas para que salgan más propuestas
válidas, distintas y no obvias. No cambies el formato de salida ni las reglas que chequea el
programa (eso está en otra parte del prompt). Respondé SOLO con un JSON:
{{"diagnostico": "...", "instrucciones": "..."}}"""


def puntaje(r: dict) -> tuple:
    return (r["no_obvias"], r["validas_distintas"])


def optimizar(cliente, particion: str, capturas: dict) -> dict:
    espacio = json.loads((SERENDIPIA / f"espacio_{particion}.json").read_text(encoding="utf-8"))
    mejor_id = espacio["variantes"][0]["variante"]
    variante = next(v for v in variantes() if v.id == mejor_id)
    todos, traza = productos(), []
    señales = señales_del_paso_a(cliente, particion, capturas, traza)
    verificadas = señales_verificadas(señales, todos)

    instrucciones = variante.instrucciones()
    medir = lambda ins: medir_repetido(cliente, [(variante, ins)], verificadas, señales, todos)[0]
    actual = medir(instrucciones)
    historia = [{"ronda": 0, "instrucciones": instrucciones, **{k: actual[k] for k in ("propuestas", "validas_distintas", "no_obvias")}}]
    print(f"ronda 0 ({mejor_id} sin cambios): {actual['no_obvias']} no obvias en promedio", flush=True)
    for ronda in range(1, RONDAS + 1):
        feedback = "\n".join(f"- {f['que_traer']} → {f['resultado']}" for f in actual["feedback"][:40])
        pedido = REFLEXION.format(instrucciones=instrucciones, feedback=feedback, no_obvias=actual["no_obvias"],
                                  propuestas=actual["propuestas"])
        nueva = _con_reintento(cliente, pedido, lambda d: {} if d.get("instrucciones") else {"x": ["falta instrucciones"]},
                               traza, f"reflexión {ronda}")
        if not nueva.get("instrucciones"):
            continue
        candidata = medir(nueva["instrucciones"])
        se_queda = puntaje(candidata) > puntaje(actual)
        historia.append({"ronda": ronda, "diagnostico": nueva.get("diagnostico"), "instrucciones": nueva["instrucciones"],
                         "se_queda": se_queda, **{k: candidata[k] for k in ("propuestas", "validas_distintas", "no_obvias")}})
        print(f"ronda {ronda}: {candidata['no_obvias']} no obvias en promedio, de {candidata['propuestas']} propuestas "
              f"({'se queda' if se_queda else 'se descarta'})", flush=True)
        if se_queda:
            instrucciones, actual = nueva["instrucciones"], candidata
    return {"particion": particion, "variante_de_partida": mejor_id, "opciones": variante.opciones,
            "instrucciones_finales": instrucciones, "resultado_final": actual, "historia": historia,
            "costo_reflexiones_y_paso_a": costo(traza)}


if __name__ == "__main__":
    from harness.correr import busquedas_capturadas
    particion = sys.argv[1] if len(sys.argv) > 1 else "dev"
    salida = optimizar(DeepSeek(os.environ["DEEPSEEK_API_KEY"]), particion, busquedas_capturadas())
    (SERENDIPIA / f"optimizacion_{particion}.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print("INSTRUCCIONES FINALES:\n" + salida["instrucciones_finales"])
