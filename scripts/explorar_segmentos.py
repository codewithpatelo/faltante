"""Prueba rápida, sin LLM, de cómo agrupar a la gente (dev). Dos preguntas, en orden:

1. ¿Agrupar por PROBLEMA (situación + qué quiere lograr) junta gente de búsquedas distintas?
   Para varios cortes del árbol de Ward: cuántos grupos cruzan búsquedas (2 personas en cada una
   de 2) y cuántas búsquedas junta el grupo mediano.
2. ¿Dentro de un mismo problema, la gente comparte TRABAS (dolor + temor) más que por azar?
   Se agrupan las trabas por separado y se cuentan los pares (problema, traba) que cruzan
   búsquedas; se compara con el mismo conteo barajando las trabas entre las personas de la MISMA
   búsqueda (200 veces): eso conserva las quejas típicas de cada producto y solo rompe el vínculo
   entre la traba y el problema.
   Si no le gana al azar, "trabas comunes" no es una propiedad de los datos y no conviene usarla
   como segunda clave.

Imprime métricas y ejemplos en líneas "RESULTADO explorar_segmentos.json <json>".

    python scripts/explorar_segmentos.py
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

RAIZ = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(RAIZ))
from harness.voces import productos  # noqa: E402

MODELO = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
CORTES_PROBLEMA = (25, 50, 100, 200, 400, 800)
CORTES_TRABA = (25, 50, 100, 200)
PERMUTACIONES = 200
SEMILLA = 7


def vec(textos):
    from sentence_transformers import SentenceTransformer
    return np.asarray(SentenceTransformer(MODELO).encode(textos, batch_size=64, normalize_embeddings=True))


def cruza(busquedas) -> bool:
    c = Counter(busquedas)
    return sum(n >= 2 for n in c.values()) >= 2


def main():
    todos = productos()
    tarjetas = json.loads((RAIZ / "data/serendipia/personas_escala_dev_api.json").read_text(encoding="utf-8"))["tarjetas"]
    con = [t for t in tarjetas if t["quiere_lograr"]]
    busq = np.array([todos[t["producto"]]["busqueda"] for t in con])
    problema = [f"{t['situacion']}. quiere: {t['quiere_lograr']}" if t["situacion"] else f"quiere: {t['quiere_lograr']}" for t in con]
    P = vec(problema)
    arbol_p = linkage(P, method="ward")
    salida = {"personas_con_problema": len(con), "problema": []}
    etiquetas_p = {}
    for k in CORTES_PROBLEMA:
        e = fcluster(arbol_p, k, criterion="maxclust")
        etiquetas_p[k] = e
        grupos = defaultdict(list)
        for i, g in enumerate(e):
            grupos[g].append(i)
        n_busq = [len(set(busq[m])) for m in grupos.values()]
        salida["problema"].append({"corte": k, "grupos_que_cruzan": sum(cruza(busq[m]) for m in grupos.values()),
                                   "busquedas_del_grupo_mediano": float(np.median(n_busq)),
                                   "personas_del_grupo_mediano": float(np.median([len(m) for m in grupos.values()]))})
    # ejemplos: en el corte con más grupos que cruzan, los 8 grupos que más búsquedas juntan
    mejor = max(salida["problema"], key=lambda r: r["grupos_que_cruzan"])["corte"]
    e = etiquetas_p[mejor]
    grupos = defaultdict(list)
    for i, g in enumerate(e):
        grupos[g].append(i)
    ejemplos = []
    for g, m in sorted(grupos.items(), key=lambda x: -len(set(busq[x[1]])))[:8]:
        por_busq = {}
        for i in m:
            por_busq.setdefault(busq[i], problema[i])
        ejemplos.append({"personas": len(m), "busquedas": len(por_busq), "uno_por_busqueda": list(por_busq.items())[:8]})
    salida["corte_elegido"] = mejor
    salida["ejemplos_problema"] = ejemplos

    # 2 · trabas comunes dentro del problema
    idx = [i for i, t in enumerate(con) if t["dolor"] or t["teme"]]
    traba = [" ".join(x for x in (con[i]["dolor"], con[i]["teme"]) if x) for i in idx]
    T = vec(traba)
    arbol_t = linkage(T, method="ward")
    rng = random.Random(SEMILLA)
    salida["trabas"] = {"personas_con_problema_y_traba": len(idx), "por_corte": []}
    for kt in CORTES_TRABA:
        et = fcluster(arbol_t, kt, criterion="maxclust")

        def pares_que_cruzan(etiq_traba):
            pares = defaultdict(list)
            for j, i in enumerate(idx):
                pares[(e[i], etiq_traba[j])].append(busq[i])
            return sum(cruza(b) for b in pares.values())

        real = pares_que_cruzan(et)
        azar = []
        por_busqueda = defaultdict(list)
        for j, i in enumerate(idx):
            por_busqueda[busq[i]].append(j)
        for _ in range(PERMUTACIONES):
            mezcla = list(et)
            for js in por_busqueda.values():
                valores = [et[j] for j in js]
                rng.shuffle(valores)
                for j, v in zip(js, valores):
                    mezcla[j] = v
            azar.append(pares_que_cruzan(mezcla))
        p = (1 + sum(a >= real for a in azar)) / (1 + PERMUTACIONES)
        salida["trabas"]["por_corte"].append({"corte_traba": kt, "pares_que_cruzan": real,
                                              "azar_media": float(np.mean(azar)), "azar_p95": float(np.percentile(azar, 95)),
                                              "p": round(p, 4)})
        if kt == 50:
            pares = defaultdict(list)
            for j, i in enumerate(idx):
                pares[(e[i], et[j])].append((busq[i], problema[i], traba[j]))
            buenos = [v for v in pares.values() if cruza([b for b, _, _ in v])]
            buenos.sort(key=lambda v: -len({b for b, _, _ in v}))
            salida["ejemplos_problema_y_traba"] = [
                {"personas": len(v), "busquedas": len({b for b, _, _ in v}),
                 "uno_por_busqueda": list({b: (pr, tr) for b, pr, tr in v}.items())[:6]} for v in buenos[:8]]
    print("RESULTADO explorar_segmentos.json " + json.dumps(salida, ensure_ascii=False))


if __name__ == "__main__":
    main()
