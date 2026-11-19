"""Prueba rápida (dev): ¿un LLM encuentra segmentos que el parecido semántico no encuentra?

Salida buscada, por segmento: "[quiénes] que quieren resolver [X], hacen [Y], pero sufren [Z]",
con el hacen y el sufren lo bastante generales para cruzar productos distintos y lo bastante
concretos para que un producto lo resuelva.

Misma entrada para los dos brazos: las tarjetas de dev con un dolor o un temor (gente que no está
pudiendo resolver algo).

  LLM (TnT-LLM, Wan et al. 2024): el modelo propone la lista de segmentos leyendo 4 tandas de 200
      personas, refinándola en cada tanda, y después clasifica a cada persona en un segmento o en
      "ninguno".
  Parecido (BERTopic, Grootendorst 2022): Ward sobre los vectores de las tarjetas, con tantos grupos
      como segmentos dio el LLM; el mismo modelo nombra cada grupo con el mismo formato leyendo sus
      40 personas más típicas, o dice que no comparten un problema.

Métricas (código): segmentos que cruzan búsquedas (2 personas en cada una de 2), búsquedas del
segmento mediano y personas que quedan en segmentos que cruzan. La calidad la juzga una persona a
ciegas con los ejemplos que se imprimen.

    DEEPSEEK_API_KEY=... python scripts/explorar_taxonomia.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from harness.modelo import cliente_llm, con_reintento, costo, en_paralelo  # noqa: E402
from harness.voces import productos  # noqa: E402

SEMILLA = 7
TANDAS_DE_GENERACION = 4
PERSONAS_POR_TANDA_DE_GENERACION = 200
MAX_SEGMENTOS = 30
PERSONAS_POR_LLAMADA_AL_CLASIFICAR = 100
PERSONAS_PARA_NOMBRAR = 40
MODELO_DE_ORACIONES = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

FORMATO = """Cada segmento es un grupo identificable de personas que viven el MISMO problema, lo intentan
resolver comprando cosas distintas y no pueden por trabas parecidas:

  "[quiénes] que quieren resolver [X], hacen [Y], pero sufren [Z]"

- quiénes: lo que las voces muestran (qué hacen, para quién compran, dónde lo usan). No inventes
  edad, género ni lugar.
- X, Y y Z sin nombrar un producto ni una categoría de producto. Generalizá lo justo: tiene que
  valer para gente que compró cosas distintas (no "mujer que se lava el pelo con tal shampoo"), y
  seguir siendo un problema concreto que un producto podría resolver (no "personas que quieren
  que las cosas funcionen", no "que cumpla su función").
- Z es una traba concreta (algo que les impide resolver X), no una queja genérica de calidad,
  envío o precio."""

LINEA = lambda t, todos: (f"[{t['id']}] {todos[t['producto']]['busqueda']} | situación: {t['situacion']} | quiere: "
                          f"{t['quiere_lograr']} | dolor: {t['dolor']} | teme: {t['teme']}")


def generar(cliente, gente, todos, traza):
    lista = []
    rng = random.Random(SEMILLA)
    muestra = rng.sample(gente, TANDAS_DE_GENERACION * PERSONAS_POR_TANDA_DE_GENERACION)
    for n in range(TANDAS_DE_GENERACION):
        tanda = muestra[n * PERSONAS_POR_TANDA_DE_GENERACION:(n + 1) * PERSONAS_POR_TANDA_DE_GENERACION]
        prompt = (f"Estás armando, de a tandas, la lista de segmentos de compradores de Mercado Libre.\n\n{FORMATO}\n\n"
                  f"LISTA ACTUAL ({len(lista)}):\n{json.dumps(lista, ensure_ascii=False)}\n\n"
                  f"TANDA {n + 1} DE PERSONAS (id, búsqueda donde compró o preguntó, lo que se sabe de ella):\n"
                  + "\n".join(LINEA(t, todos) for t in tanda)
                  + f"\n\nDevolvé la lista refinada: agregá segmentos que esta tanda muestre (con gente de al menos 2 "
                  f"búsquedas distintas), uní los que son el mismo problema, partí los que mezclan problemas, sacá "
                  f"los que quedaron genéricos. Como máximo {MAX_SEGMENTOS}.\n"
                  'JSON: {"segmentos": [{"id": "S1", "quienes": "...", "quieren_resolver": "...", "hacen": "...", '
                  '"sufren": "...", "ejemplos": ["id", "id"]}]}')
        d = con_reintento(cliente, prompt, lambda d: {} if d.get("segmentos") else {"segmentos": ["vacío"]}, traza, f"G{n + 1}")
        lista = d.get("segmentos", lista)[:MAX_SEGMENTOS]
    for i, s in enumerate(lista, start=1):
        s["id"] = f"L{i:02d}"
    return lista


def clasificar(cliente, gente, segmentos, todos, traza):
    resumen = "\n".join(f"{s['id']}: {s['quienes']} que quieren resolver {s['quieren_resolver']}, hacen {s['hacen']}, "
                        f"pero sufren {s['sufren']}" for s in segmentos)
    ids_validos = {s["id"] for s in segmentos} | {"ninguno"}
    tandas = [gente[i:i + PERSONAS_POR_LLAMADA_AL_CLASIFICAR] for i in range(0, len(gente), PERSONAS_POR_LLAMADA_AL_CLASIFICAR)]

    def una(tanda):
        de_la_tanda = {t["id"] for t in tanda}
        prompt = (f"SEGMENTOS:\n{resumen}\n\nPara cada persona, decí a qué segmento pertenece: tiene que vivir ESE problema "
                  "y sufrir ESA traba (aunque haya comprado otra cosa). Si no encaja claramente en ninguno, \"ninguno\".\n\n"
                  "PERSONAS:\n" + "\n".join(LINEA(t, todos) for t in tanda)
                  + '\n\nJSON: {"asignaciones": [{"id": "...", "segmento": "L01"}]}')
        validar = lambda d: {str(a.get("id")): ["id o segmento inválido"] for a in d.get("asignaciones", [])
                             if a.get("id") not in de_la_tanda or a.get("segmento") not in ids_validos}
        d = con_reintento(cliente, prompt, validar, traza, "C", pensar=False)
        return {a["id"]: a["segmento"] for a in d.get("asignaciones", []) if a.get("id") in de_la_tanda and a.get("segmento") in ids_validos}

    asign = {}
    for parte in en_paralelo(una, tandas):
        asign |= parte
    return asign


def por_parecido(cliente, gente, k, todos, traza):
    from scipy.cluster.hierarchy import fcluster, linkage
    from sentence_transformers import SentenceTransformer
    textos = [". ".join(f"{n}: {t[c]}" for c, n in (("situacion", "quién es"), ("quiere_lograr", "qué quiere lograr"),
                                                    ("dolor", "qué le duele"), ("teme", "qué teme")) if t[c]) for t in gente]
    V = np.asarray(SentenceTransformer(MODELO_DE_ORACIONES).encode(textos, batch_size=64, normalize_embeddings=True))
    etiquetas = fcluster(linkage(V, method="ward"), k, criterion="maxclust")
    grupos = defaultdict(list)
    for i, e in enumerate(etiquetas):
        grupos[int(e)].append(i)

    def nombrar(item):
        e, miembros = item
        centro = V[miembros].mean(axis=0)
        tipicos = sorted(miembros, key=lambda i: -float(V[i] @ centro))[:PERSONAS_PARA_NOMBRAR]
        prompt = (f"{FORMATO}\n\nEstas personas quedaron juntas por parecido. Si comparten un problema y una traba, "
                  "describí el segmento; si no, poné \"comparten\": false.\n\n"
                  + "\n".join(LINEA(gente[i], todos) for i in tipicos)
                  + '\n\nJSON: {"comparten": true, "quienes": "...", "quieren_resolver": "...", "hacen": "...", "sufren": "..."}')
        d = con_reintento(cliente, prompt, lambda d: {}, traza, f"N{e}")
        return {"id": f"P{e:02d}", **d}

    segmentos = en_paralelo(nombrar, sorted(grupos.items()))
    asign = {gente[i]["id"]: f"P{e:02d}" for e, ms in grupos.items() for i in ms}
    for s in segmentos:
        if not s.get("comparten", True):
            asign = {p: ("ninguno" if g == s["id"] else g) for p, g in asign.items()}
    return [s for s in segmentos if s.get("comparten", True)], asign


def medir(segmentos, asign, por_id, todos):
    miembros = defaultdict(list)
    for p, g in asign.items():
        if g != "ninguno":
            miembros[g].append(p)
    cruzan, filas = [], []
    for s in segmentos:
        ms = miembros.get(s["id"], [])
        busq = Counter(todos[por_id[p]["producto"]]["busqueda"] for p in ms)
        cruza = sum(n >= 2 for n in busq.values()) >= 2
        uno_por_busqueda = {}
        for p in ms:
            t = por_id[p]
            uno_por_busqueda.setdefault(todos[t["producto"]]["busqueda"], {"id": p, "quiere": t["quiere_lograr"], "dolor": t["dolor"], "teme": t["teme"]})
        filas.append({**{k: s.get(k) for k in ("id", "quienes", "quieren_resolver", "hacen", "sufren")},
                      "personas": len(ms), "busquedas": len(busq), "cruza": cruza,
                      "ejemplos": list(uno_por_busqueda.items())[:5]})
        cruzan.append(cruza)
    en_cruzan = sum(f["personas"] for f in filas if f["cruza"])
    return {"segmentos": len(segmentos), "cruzan": sum(cruzan),
            "busquedas_del_mediano": float(np.median([f["busquedas"] for f in filas])) if filas else 0,
            "personas_en_segmentos_que_cruzan": en_cruzan, "ninguno": sum(g == "ninguno" for g in asign.values()),
            "detalle": filas}


def main():
    todos = productos()
    tarjetas = json.loads((RAIZ / "data/serendipia/personas_escala_dev_api.json").read_text(encoding="utf-8"))["tarjetas"]
    gente = [t for t in tarjetas if t["dolor"] or t["teme"]]
    por_id = {t["id"]: t for t in gente}
    cliente = cliente_llm()
    traza_l, traza_p = [], []
    segs_l = generar(cliente, gente, todos, traza_l)
    asign_l = clasificar(cliente, gente, segs_l, todos, traza_l)
    segs_p, asign_p = por_parecido(cliente, gente, len(segs_l), todos, traza_p)
    salida = {"personas": len(gente), "llm": medir(segs_l, asign_l, por_id, todos), "parecido": medir(segs_p, asign_p, por_id, todos),
              "costo": {"llm": costo(traza_l), "parecido": costo(traza_p)}}
    print("RESULTADO explorar_taxonomia.json " + json.dumps(salida, ensure_ascii=False))


if __name__ == "__main__":
    main()
