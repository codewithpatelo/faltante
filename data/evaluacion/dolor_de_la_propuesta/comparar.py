"""Compara, sobre las mismas propuestas, el embudo con C1 y C2 (A) y con el dolor medido en su lugar (B).

    python data/evaluacion/dolor_de_la_propuesta/comparar.py <carpeta con dolor_eval-personas-libres_*.json>
"""
import json
import shutil
import statistics as st
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
from scipy.stats import fisher_exact  # noqa: E402

from harness import chequeos as c  # noqa: E402
from harness import correr as cr  # noqa: E402

carpeta = Path(sys.argv[1])
filas, faltan, tabla = [], set(), [[0, 0], [0, 0]]
for f in sorted(carpeta.glob("dolor_eval-personas-libres_*.json")):
    medida = {m["id"]: m["veredicto"] for m in json.loads(f.read_text(encoding="utf-8"))["medidas"]}
    corrida = f.stem.rsplit("_", 1)[1]
    tmp = cr.SERENDIPIA / f"divergente_eval{corrida}.json"
    shutil.copy(RAIZ / "data/evaluacion/versiones_escala_dev" / f.name.removeprefix("dolor_"), tmp)
    try:
        ps = [p for p in cr.propuestas(f"eval{corrida}") if p.metodo == "llm"]
    finally:
        tmp.unlink()
    a, b = {"c4": set(), "c5": set()}, {"c4": set(), "c5": set()}
    for p in ps:
        busq = p.oportunidad["busqueda_ml"]
        base = c.guardrail(p).pasa and c.c3_demanda(p).pasa
        if not base:
            continue
        c4 = c.c4_hueco(p)
        if c4.motivo.startswith("falta capturar"):
            if medida[p.oportunidad["id"]]["pasa"]:      # solo importa para B: A ya la mató en C1 o C2
                faltan.add(busq)
            continue
        c5 = c4.pasa and c.c5_la_eligen(p).pasa
        dolor = medida[p.oportunidad["id"]]["pasa"]
        tabla[int(dolor)][int(c5)] += 1
        for version, pasa_necesidad in ((a, c.c1_verificada(p).pasa and c.c2_subatendida(p).pasa), (b, dolor)):
            if pasa_necesidad and c4.pasa:
                version["c4"].add(busq)
                if c5:
                    version["c5"].add(busq)
    filas.append({"corrida": corrida, "A_c4": len(a["c4"]), "A_c5": len(a["c5"]), "B_c4": len(b["c4"]), "B_c5": len(b["c5"]),
                  "solo_A": sorted(a["c5"] - b["c5"]), "solo_B": sorted(b["c5"] - a["c5"])})
resumen = {v: {"c5_por_corrida": round(st.mean(x[f"{v}_c5"] for x in filas), 1),
               "proporcion_c5_sobre_c4": round(sum(x[f"{v}_c5"] for x in filas) / max(1, sum(x[f"{v}_c4"] for x in filas)), 3)}
           for v in ("A", "B")}
p_sep = fisher_exact(tabla, alternative="greater")[1] if all(sum(r) for r in tabla) else None
salida = {"filas": filas, "resumen": resumen,
          "dolor_vs_c5_entre_las_que_pasan_c3": {"tabla_[dolor][c5]": tabla, "p": p_sep}, "faltan": sorted(faltan)}
(carpeta / "comparacion.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in salida.items() if k != "filas"}, ensure_ascii=False, indent=1)[:3000])
