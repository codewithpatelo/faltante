"""La divergencia: perfilar a la gente y buscar desfasajes de mercado.

    A · personas   (skills/leer_personas)          de cada voz, un mapa de empatía chico citando su texto
    S · segmentos  (skills/agrupar_personas)       personas en la misma situación, aunque hayan
                                                    comprado cosas distintas; de cada segmento, su
                                                    mapa de empatía (harness/personas.py)
    B · propuestas (skills/proponer_a_un_segmento) por segmento, qué traer que ese grupo necesita y
                                                    no ve en su góndola, como propuesta de valor; dos
                                                    tandas, la segunda distinta de la primera

    C1 · dolor     (harness/dolor.py)               otro modelo mide si el dolor que dice aliviar cada
                                                    propuesta existe en la gente que cita (y en los
                                                    baselines, igual); decide una prueba estadística

Lo no obvio sale de la persona, no del producto: mirar un producto solo da su repuesto o su
versión mejorada. En cada paso el guardrail (código) revisa lo que cita el LLM; lo que sigue
mal después de un reintento se descarta. Las propuestas salen en el formato del embudo: cada una
con señales por producto, armadas con las voces que cita.

    DEEPSEEK_API_KEY=... python -m harness.divergente escala_dev   -> data/serendipia/divergente_escala_dev_api.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from harness import dolor as D
from harness import personas as P
from harness.baselines import b1_queja_mas_frecuente, b2_pedidos_de_repuesto
from harness.modelo import cliente_llm, con_reintento, costo, en_paralelo, sufijo
from harness.voces import RAIZ, productos

SKILL_B = RAIZ / "skills/proponer_a_un_segmento/SKILL.md"
MIN_PERSONAS_POR_PRODUCTO = 2     # en cada producto, la necesidad la dicen al menos 2 personas (como toda señal del embudo)
MIN_PRODUCTOS_CITADOS = 2         # en al menos 2 productos distintos: la necesidad cruza productos
REPREGUNTAR = True                # pedir una segunda tanda distinta: lo que más rindió al comparar prompts (DECISIONES.md)


def prompt_b(mapa: dict) -> str:
    return (f"{SKILL_B.read_text(encoding='utf-8')}\n\n---\n\nMAPA DE EMPATÍA DEL SEGMENTO\n"
            f"{json.dumps(mapa, ensure_ascii=False, indent=1)}\n\nRespondé SOLO con el JSON de la salida.")


def errores_de_propuesta(o: dict, miembros: dict[str, dict]) -> list[str]:
    """Guardrail del paso B: las personas citadas son del segmento, alcanzan y cruzan productos."""
    citadas = o.get("personas") or []
    errores = [f"cita a alguien que no es del segmento: {i}" for i in citadas if i not in miembros]
    por_producto = Counter(miembros[i]["producto"] for i in dict.fromkeys(citadas) if i in miembros)
    if sum(n >= MIN_PERSONAS_POR_PRODUCTO for n in por_producto.values()) < MIN_PRODUCTOS_CITADOS:
        errores.append(f"tiene que citar al menos {MIN_PERSONAS_POR_PRODUCTO} personas de cada uno de al menos "
                       f"{MIN_PRODUCTOS_CITADOS} productos distintos")
    if not o.get("alivia") or not o.get("busqueda_ml"):
        errores.append("faltan alivia o busqueda_ml")
    return errores


def proponer(cliente, mapa: dict, miembros: dict[str, dict], traza: list) -> list[dict]:
    """Paso B para un segmento: una tanda de propuestas y, si REPREGUNTAR, otra distinta."""
    validar = lambda d: {o.get("id"): e for o in d.get("oportunidades", []) if (e := errores_de_propuesta(o, miembros))}
    prompt, etiqueta = prompt_b(mapa), f"B {mapa['segmento']}"
    ops = con_reintento(cliente, prompt, validar, traza, etiqueta).get("oportunidades", [])
    if REPREGUNTAR and ops:
        previas = "\n".join(f"- {o.get('que_traer', '')}" for o in ops)
        otra = f"{prompt}\n\nYa propusiste estas:\n{previas}\nProponé hasta 3 MÁS, distintas de todas estas."
        ops += [{**o, "id": f"{o.get('id', 'O')}b"} for o in con_reintento(cliente, otra, validar, traza, f"{etiqueta} otra").get("oportunidades", [])]
    return [{**o, "id": f"{mapa['segmento']}.{o.get('id', 'O')}", "segmento": mapa["segmento"]}
            for o in ops if not errores_de_propuesta(o, miembros)]


def al_formato_del_embudo(oportunidades: list[dict], tarjetas: dict[str, dict], particion: str) -> dict:
    """El embudo mide señales por producto (harness/embudo.py). Cada propuesta deja, en cada
    producto de las personas que cita, una señal: la necesidad, sus palabras clave y las citas."""
    señales = {pid: [] for pid in productos(particion)}
    salida = []
    for o in oportunidades:
        sid, ids = o["id"].replace(".", ""), []
        for pid in dict.fromkeys(tarjetas[i]["producto"] for i in o["personas"]):
            señales.setdefault(pid, []).append({"id": sid, "tipo": "segmento", "descripcion": o.get("alivia") or o.get("por_que", ""),
                                 "citas": [{"texto": tarjetas[i]["texto"], "fragmento": tarjetas[i]["fragmento"]}
                                           for i in o["personas"] if tarjetas[i]["producto"] == pid]})
            ids.append(f"{pid}.{sid}")
        salida.append({**o, "señales": ids})
    return {"señales": señales, "oportunidades": salida}


def dolores_de_los_baselines(particion: str, tarjetas: dict) -> dict[str, list]:
    """El dolor de cada baseline, dicho como el del LLM, medido en la gente de su producto."""
    con_gente = {t["producto"] for t in tarjetas.values()}
    salida = {"B1": [], "B2": []}
    for pid, producto in productos(particion).items():
        if pid not in con_gente:
            continue
        for metodo, baseline in (("B1", b1_queja_mas_frecuente), ("B2", b2_pedidos_de_repuesto)):
            hecho = baseline(producto)
            if hecho:
                señal, oportunidad, _ = hecho
                salida[metodo].append(({"id": f"{metodo}.{pid}", "trabajo": f"usar {producto['busqueda']}",
                                        "obstaculo": señal["descripcion"], "que_hace_mal": oportunidad["que_traer"]}, {pid}))
    return salida


def divergir(cliente, particion: str, capturas: dict) -> dict:
    todos, traza = productos(), []
    gente = P.personas_de_la_particion(cliente, particion, traza)
    tarjetas = {t["id"]: t for t in gente["tarjetas"]}
    mapas, miembros_de = [], {}
    for s in gente["segmentos"]:
        miembros_de[s["id"]] = {i: tarjetas[i] for i, g in gente["asignaciones"].items() if g == s["id"]}
        mapas.append(P.mapa_de_empatia(s, list(miembros_de[s["id"]].values()), todos, capturas))
    suficientes = [m for m in mapas if P.es_segmento_suficiente(m)]
    oportunidades = [o for ops in en_paralelo(lambda m: proponer(cliente, m, miembros_de[m["segmento"]], traza), suficientes)
                     for o in ops]
    dolor = {"llm": D.medir_y_decidir(cliente, [(D.enunciado(o), {tarjetas[i]["producto"] for i in o["personas"]})
                                                for o in oportunidades], tarjetas, todos, traza)}
    for metodo, dolores in dolores_de_los_baselines(particion, tarjetas).items():
        dolor[metodo] = D.medir_y_decidir(cliente, dolores, tarjetas, todos, traza)
    return {"quien": cliente.modelo, "costo": costo(traza, cliente.modelo), "traza": traza, "dolor": dolor,
            "personas": len(tarjetas), "asignadas": len(gente["asignaciones"]),
            "segmentos": [{**m, "pasa_al_paso_b": P.es_segmento_suficiente(m)} for m in mapas],
            **al_formato_del_embudo(oportunidades, tarjetas, particion)}


if __name__ == "__main__":
    from harness.correr import busquedas_capturadas
    particion = sys.argv[1] if len(sys.argv) > 1 else "escala_dev"
    cliente = cliente_llm()
    salida = divergir(cliente, particion, busquedas_capturadas())
    destino = RAIZ / f"data/serendipia/divergente_{particion}_api{sufijo(cliente.modelo)}.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{destino.relative_to(RAIZ)}: {salida['costo']}, {salida['personas']} personas, "
          f"{sum(m['pasa_al_paso_b'] for m in salida['segmentos'])} segmentos, {len(salida['oportunidades'])} oportunidades")
