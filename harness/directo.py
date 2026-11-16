"""Baseline B3, zero-shot: el mismo modelo lee UN producto y propone qué traer en una sola llamada,
sin personas ni grupos (skills/proponer_directo). Responde si la arquitectura (personas →
segmentos → propuestas) aporta algo frente a preguntarle directamente al LLM. Pasa por el mismo
embudo: el dolor se mide igual que para los demás baselines (en la gente de su producto).

    DEEPSEEK_API_KEY=... python -m harness.directo escala_dev   -> data/serendipia/directo_escala_dev_api.json
    MODELO_LLM=claude-opus-5-5 python -m harness.directo escala_dev   -> ..._api__claude-opus-5-5.json (no pisa el de DeepSeek)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness import dolor as D
from harness.modelo import MODELO, clientes, con_reintento, costos, en_paralelo, juez_para_rejuzgar, sufijo
from harness.voces import RAIZ, los_mas_informativos, productos, textos_con_id

SKILL = RAIZ / "skills/proponer_directo/SKILL.md"
OPINIONES_QUE_LEE = 60        # las más informativas, más todas las preguntas: lo mismo que leía el paso viejo por producto
MIN_CITAS = 2                 # como toda señal del embudo


def proponer(cliente, pid: str, producto: dict, traza: list) -> list[dict]:
    textos = los_mas_informativos(textos_con_id(producto), OPINIONES_QUE_LEE)
    lineas = "\n".join(f"[{i}] {t[:400]}" for i, t in textos.items())
    prompt = (f"{SKILL.read_text(encoding='utf-8')}\n\n---\n\nPRODUCTO: {producto['titulo']} (búsqueda: {producto['busqueda']})\n\n"
              f"TEXTOS\n{lineas}\n\nRespondé SOLO con el JSON de la salida.")

    def validar(d):
        return {str(k): ["cita textos que no existen o menos de 2", "faltan que_traer o busqueda_ml"]
                for k, o in enumerate(d.get("oportunidades", []))
                if len([c for c in o.get("citas", []) if c in textos]) < MIN_CITAS or not o.get("que_traer") or not o.get("busqueda_ml")}
    ops = con_reintento(cliente, prompt, validar, traza, f"B3 {pid}").get("oportunidades", [])
    return [{**o, "id": f"B3.{pid}.{k}", "producto": pid} for k, o in enumerate(ops)
            if len([c for c in o.get("citas", []) if c in textos]) >= MIN_CITAS and o.get("que_traer") and o.get("busqueda_ml")]


def correr(cliente, particion: str, juez=None) -> dict:
    """`cliente` lee y propone; `juez` mide el dolor (C1). Sin `juez`, el mismo."""
    juez = juez or cliente
    traza, todos = [], productos()
    traza_juez = traza if juez is cliente else []
    from harness.personas import personas_de_la_particion
    tarjetas = {t["id"]: t for t in personas_de_la_particion(cliente, particion, traza)["tarjetas"]}
    ps = productos(particion)
    ops = [o for lista in en_paralelo(lambda pid: proponer(cliente, pid, ps[pid], traza), list(ps)) for o in lista]
    dolor = D.medir_y_decidir(juez, [(D.enunciado(o), {o["producto"]}) for o in ops], tarjetas, todos, traza_juez)
    trazas = {cliente.modelo: traza, **({juez.modelo: traza_juez} if juez is not cliente else {})}
    return {"quien": cliente.modelo, "juez": juez.modelo, "costo": costos(trazas),
            "traza": traza + (traza_juez if juez is not cliente else []), "oportunidades": ops, "dolor": dolor}


def rejuzgar(guardado: dict, particion: str, juez) -> dict:
    """Mide de nuevo el dolor (C1) de las propuestas de B3 ya guardadas, con otro juez y sin volver a proponer."""
    from harness.personas import tarjetas_guardadas
    todos, traza = productos(), []
    dolor = D.medir_y_decidir(juez, [(D.enunciado(o), {o["producto"]}) for o in guardado["oportunidades"]],
                              tarjetas_guardadas(particion), todos, traza)
    return {**{k: v for k, v in guardado.items() if k != "traza"}, "juez": juez.modelo, "costo_de_proponer": guardado.get("costo"),
            "costo": costos({juez.modelo: traza}), "traza": traza, "dolor": dolor}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    particion = args[0] if args else "escala_dev"
    if "--rejuzgar" in sys.argv:       # python -m harness.directo escala_dev --rejuzgar [archivo]
        juez = juez_para_rejuzgar(particion)
        origen = Path(args[1]) if len(args) > 1 else RAIZ / f"data/serendipia/directo_{particion}_api.json"
        guardado = json.loads(origen.read_text(encoding="utf-8"))
        if juez.modelo == guardado.get("quien", MODELO):
            raise SystemExit(f"{juez.modelo} ya propuso esto: re-juzgar es con otro modelo")
        salida = rejuzgar(guardado, particion, juez)
        destino = RAIZ / f"data/serendipia/directo_{particion}_api{sufijo(guardado.get('quien', MODELO), juez.modelo)}.json"
        destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{destino.relative_to(RAIZ)}: {salida['costo']}")
        raise SystemExit(0)
    cliente, juez = clientes()
    salida = correr(cliente, particion, juez)
    destino = RAIZ / f"data/serendipia/directo_{particion}_api{sufijo(cliente.modelo, juez.modelo)}.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{destino.relative_to(RAIZ)}: {salida['costo']}, {len(salida['oportunidades'])} oportunidades")
