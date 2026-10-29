"""Corre una política sobre un conjunto de pistas y la evalúa contra la verdad etiquetada.

Uso:
    python run.py --politica fija
    python run.py --politica heuristica
    python run.py --politica react_llm        # requiere ANTHROPIC_API_KEY
    python run.py --politica fija --fuente ml  # requiere ML_ACCESS_TOKEN
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from adapters import AdaptadorFixtures, AdaptadorMercadoLibre  # noqa: E402
from harness.motor import Motor, Presupuesto  # noqa: E402
from harness.politicas import PoliticaFija, PoliticaHeuristica  # noqa: E402


def evaluar_corrida(m: Motor) -> dict:
    decisiones = m.decision_por_pista()
    filas, aciertos = [], 0
    for p in m.pistas:
        d = decisiones[p["id"]]["decision"]
        ok = d == p.get("verdad")
        aciertos += ok
        n_skills = sum(len(h["evidencias"]) for h in m.hipotesis.values() if h["pista_id"] == p["id"])
        filas.append({"pista": p["id"], "verdad": p.get("verdad"), "decision": d, "acierto": ok,
                      "skills_usadas": n_skills})
    n = len(m.pistas)
    conf_ok = sum(1 for f in filas if f["verdad"] == "confirmar" and f["decision"] == "confirmar")
    conf_pred = sum(1 for f in filas if f["decision"] == "confirmar")
    conf_real = sum(1 for f in filas if f["verdad"] == "confirmar")
    return {
        "accuracy": round(aciertos / n, 3),
        "precision_confirmar": round(conf_ok / conf_pred, 3) if conf_pred else None,
        "recall_confirmar": round(conf_ok / conf_real, 3) if conf_real else None,
        "skills_por_pista": round(sum(f["skills_usadas"] for f in filas) / n, 2),
        "llamadas_a_fuente": m.llamadas_fuente,
        "cache_hits": m.cache_hits,
        "rechazos_guardrail": sum(1 for t in m.traza if t["evento"] == "rechazo"),
        "por_pista": filas,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--politica", choices=["fija", "heuristica", "react_llm"], required=True)
    ap.add_argument("--fuente", choices=["fixtures", "ml"], default="fixtures")
    ap.add_argument("--pistas", default=str(RAIZ / "data/pistas_sintetico.json"))
    ap.add_argument("--modelo", default="claude-haiku-4-5")
    ap.add_argument("--sin-cache", action="store_true")
    ap.add_argument("--salida", default=str(RAIZ / "out"))
    args = ap.parse_args()

    pistas = json.loads(Path(args.pistas).read_text(encoding="utf-8"))["pistas"]
    adaptador = (AdaptadorFixtures(RAIZ / "data/fixtures_sintetico.json") if args.fuente == "fixtures"
                 else AdaptadorMercadoLibre())
    salida = Path(args.salida)
    salida.mkdir(exist_ok=True)
    cache = None if args.sin_cache else salida / f"cache_{adaptador.nombre}.json"
    # Cada política arranca con caché vacía en memoria salvo que se pida reusar:
    # así 'llamadas_a_fuente' compara a las políticas en igualdad de condiciones.
    if cache and cache.exists() and args.politica != "react_llm":
        cache = None
    m = Motor(adaptador=adaptador, pistas=pistas, presupuesto=Presupuesto(), ruta_cache=cache)

    if args.politica == "fija":
        pol = PoliticaFija()
    elif args.politica == "heuristica":
        pol = PoliticaHeuristica()
    else:
        from harness.agente import PoliticaReAct
        pol = PoliticaReAct(modelo=args.modelo)

    t0 = time.time()
    pol.correr(m)
    dur = time.time() - t0
    m.guardar_cache()

    resumen = {
        "politica": pol.nombre,
        "fuente": adaptador.nombre,
        "datos_sinteticos": args.fuente == "fixtures",
        "duracion_s": round(dur, 3),
        "costo_usd": round(pol.costo_usd(), 5) if hasattr(pol, "costo_usd") else 0.0,
        "tokens": getattr(pol, "uso", None),
        **evaluar_corrida(m),
    }
    base = salida / f"{pol.nombre}"
    (base.with_suffix(".traza.jsonl")).write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in m.traza), encoding="utf-8")
    (base.with_suffix(".resumen.json")).write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    (base.with_suffix(".estado.json")).write_text(json.dumps(
        {"hipotesis": m.hipotesis, "evidencias": m.evidencias, "veredictos": m.veredictos,
         "pistas": pistas}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[{pol.nombre}] accuracy={resumen['accuracy']}  skills/pista={resumen['skills_por_pista']}  "
          f"llamadas={resumen['llamadas_a_fuente']}  costo=USD {resumen['costo_usd']}  "
          f"rechazos={resumen['rechazos_guardrail']}")
    for f in resumen["por_pista"]:
        marca = "✓" if f["acierto"] else "✗"
        print(f"  {marca} {f['pista']}: {f['decision']:<13} (verdad: {f['verdad']}, skills: {f['skills_usadas']})")


if __name__ == "__main__":
    main()
