"""Prueba las 25 variantes del paso B (harness/espacio_de_prompts.py) sobre los mismos productos
de desarrollo y las ordena. No usa el navegador: mide hasta C3; C4 y C5 se prueban después,
capturando las búsquedas de las mejores variantes.

    DEEPSEEK_API_KEY=... python -m harness.explorar_prompts dev   -> data/serendipia/espacio_dev.json

Medida de cada variante:
    validas    oportunidades que pasan el guardrail del cruce y C1 a C3
    distintas  de esas, las que no repiten a otra (comparando las palabras de "que_traer")
    no_obvias  de las distintas, las que el juez (skills/juzgar_obviedad) marca como no obvias
    puntaje    no_obvias; desempata distintas

El juez es un LLM y los LLM son malos jueces de ideas (ver DECISIONES.md): sirve para comparar
prompts entre sí, no para recomendar. La recomendación la sigue decidiendo el embudo.
"""

from __future__ import annotations

import json
import os
import re
import sys

from harness.chequeos import errores_de_citas
from harness.divergente import (DeepSeek, _con_reintento, costo, cruzar, eleccion_en_la_busqueda, lineas_de_señales,
                                señales_de, señales_verificadas)
from harness.embudo import EMBUDO, Propuesta
from harness.espacio_de_prompts import variantes
from harness.voces import RAIZ, productos, sin_acentos

SERENDIPIA = RAIZ / "data/serendipia"
JUEZ = (RAIZ / "skills/juzgar_obviedad/SKILL.md").read_text(encoding="utf-8")
PARECIDO_PARA_REPETIDA = 0.5      # proporción de palabras en común de "que_traer"
CHEQUEOS_SIN_NAVEGADOR = EMBUDO[:4]   # guardrail, C1, C2, C3


def señales_del_paso_a(cliente, particion: str, capturas: dict, traza: list) -> dict:
    """Las señales del paso A se calculan una vez y se guardan: todas las variantes del paso B
    parten de las mismas, así la comparación es justa."""
    archivo = SERENDIPIA / f"señales_{particion}_api.json"
    if archivo.exists():
        return json.loads(archivo.read_text(encoding="utf-8"))
    señales = {pid: señales_de(cliente, p, eleccion_en_la_busqueda(p, capturas.get(p["busqueda"])), traza)
               for pid, p in productos(particion).items()}
    archivo.write_text(json.dumps(señales, ensure_ascii=False, indent=1), encoding="utf-8")
    return señales


def proponer_con(cliente, variante, verificadas: list[dict], traza: list, instrucciones: str | None = None) -> list[dict]:
    texto = lineas_de_señales(verificadas)
    ops = cruzar(cliente, verificadas, traza, variante.prompt(texto, instrucciones), f"B {variante.id}")
    if variante.repreguntar and ops:
        previas = "\n".join(f"- {o.get('que_traer', '')}" for o in ops)
        otra = variante.prompt(texto, instrucciones) + f"\n\nYa propusiste estas:\n{previas}\nProponé hasta 5 MÁS, distintas de todas estas."
        nuevas = cruzar(cliente, verificadas, traza, otra, f"B {variante.id} otra")
        ops += [{**o, "id": f"{o.get('id', 'O')}b"} for o in nuevas]
    return ops


def validas(ops: list[dict], señales: dict, todos: dict) -> list[dict]:
    """Las que pasan guardrail y C1 a C3 (lo que se puede probar sin capturar búsquedas)."""
    por_id = {f"{pid}.{s['id']}": {**s, "producto": pid} for pid, lista in señales.items() for s in lista}
    salida = []
    for o in ops:
        citadas = [por_id[i] for i in o.get("señales", []) if i in por_id]
        if not citadas or "busqueda_ml" not in o:
            continue
        p = Propuesta("llm", [todos[pid] for pid in dict.fromkeys(s["producto"] for s in citadas)],
                      {"id": o.get("id"), "que_traer": o.get("que_traer", ""), "busqueda_ml": o["busqueda_ml"],
                       "criterio_equivalencia": o.get("criterio_equivalencia", {})}, citadas)
        if all(ch.funcion(p).pasa for ch in CHEQUEOS_SIN_NAVEGADOR):
            salida.append(o)
    return salida


def sin_repetidas(ops: list[dict]) -> list[dict]:
    palabras = lambda o: set(re.findall(r"[a-z]{4,}", sin_acentos(o.get("que_traer", ""))))
    salida = []
    for o in ops:
        if all(len(palabras(o) & palabras(x)) / max(1, len(palabras(o) | palabras(x))) < PARECIDO_PARA_REPETIDA for x in salida):
            salida.append(o)
    return salida


def juzgar(cliente, ops: list[dict], señales: dict, todos: dict, traza: list) -> dict:
    if not ops:
        return {}
    filas = []
    for o in ops:
        anclas = sorted({todos[i.split('.')[0]]["titulo"][:60] for i in o.get("señales", []) if i.split('.')[0] in todos})
        filas.append(f"[{o['id']}] {o.get('que_traer', '')} | por qué: {o.get('por_que', '')[:200]} | anclas: {'; '.join(anclas)}")
    prompt = f"{JUEZ}\n\n---\n\nOPORTUNIDADES\n" + "\n".join(filas) + "\n\nRespondé SOLO con el JSON de la salida."
    d = _con_reintento(cliente, prompt, lambda d: {}, traza, "juez")
    return {j.get("id"): j for j in d.get("juicios", [])}


def medir_variante(cliente, v, verificadas, señales, todos, traza, instrucciones: str | None = None) -> dict:
    """Propone con la variante y mide: válidas (guardrail y C1 a C3), distintas y no obvias.
    Devuelve también, por cada propuesta descartada, el motivo: es el feedback del optimizador."""
    inicio = len(traza)
    ops = proponer_con(cliente, v, verificadas, traza, instrucciones)
    validas_ = validas(ops, señales, todos)
    buenas = sin_repetidas(validas_)
    juicios = juzgar(cliente, buenas, señales, todos, traza)
    no_obvias = [o for o in buenas if juicios.get(o["id"], {}).get("obvia") is False]
    ids_validas, ids_buenas = {id(o) for o in validas_}, {id(o) for o in buenas}
    feedback = [{"que_traer": o.get("que_traer", ""),
                 "resultado": ("no pasó el guardrail o C1 a C3 (señales que no existen, de un solo producto, débiles o "
                               "de productos que venden poco)" if id(o) not in ids_validas else
                               "repite otra propuesta" if id(o) not in ids_buenas else
                               f"obvia: {juicios.get(o['id'], {}).get('motivo', '')}" if juicios.get(o["id"], {}).get("obvia")
                               else "válida, distinta y no obvia")} for o in ops]
    return {"variante": v.id, "opciones": v.opciones, "propuestas": len(ops), "validas_distintas": len(buenas),
            "no_obvias": len(no_obvias), "costo": costo(traza[inicio:]), "feedback": feedback,
            "oportunidades": [{**o, "juicio": juicios.get(o["id"])} for o in buenas]}


def explorar(cliente, particion: str, capturas: dict) -> dict:
    todos, traza = productos(), []
    señales = señales_del_paso_a(cliente, particion, capturas, traza)
    verificadas = señales_verificadas(señales, todos)
    resultados = []
    for v in variantes():
        r = medir_variante(cliente, v, verificadas, señales, todos, traza)
        resultados.append(r)
        print(f"{v.id} {r['propuestas']:>2} propuestas, {r['validas_distintas']:>2} válidas y distintas, "
              f"{r['no_obvias']:>2} no obvias  {v.opciones}", flush=True)
    resultados.sort(key=lambda r: (-r["no_obvias"], -r["validas_distintas"]))
    return {"particion": particion, "señales_verificadas": len(verificadas), "costo_total": costo(traza), "variantes": resultados}


if __name__ == "__main__":
    from harness.correr import busquedas_capturadas
    particion = sys.argv[1] if len(sys.argv) > 1 else "dev"
    salida = explorar(DeepSeek(os.environ["DEEPSEEK_API_KEY"]), particion, busquedas_capturadas())
    (SERENDIPIA / f"espacio_{particion}.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"costo total: {salida['costo_total']}")
