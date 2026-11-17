"""Resultado de la hipótesis sobre el embudo de una partición (por defecto, test), según el prerregistro.

    python data/evaluacion/test/resultado.py [escala_test_api]  -> data/evaluacion/test/resultado_<particion>.json

Por método: propuestas, cuántas pasan cada chequeo, oportunidades distintas (por búsqueda
propuesta) no descartadas, su proporción, y dónde mueren las demás. Además, el subconjunto limpio:
propuestas que solo citan productos nuevos (prefijo F), que ninguna versión leyó antes.
"""
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
particion = sys.argv[1] if len(sys.argv) > 1 else "escala_test_api"
filas = json.loads((RAIZ / f"data/serendipia/embudo_{particion}.json").read_text(encoding="utf-8"))


def resumen(rs: list[dict]) -> dict:
    vivas = [r for r in rs if r["estado"] != "descartada"]
    return {"propuestas": len(rs),
            "no_descartadas_distintas": len({r["busqueda_ml"] for r in vivas}),
            "sobreviven": len({r["busqueda_ml"] for r in vivas if r["estado"] == "sobrevive"}),
            "proporcion": round(len(vivas) / max(1, len(rs)), 3),
            "mueren_en": dict(Counter(r["se_detiene_en"] for r in rs if r["estado"] == "descartada")),
            "no_descartadas": sorted({f"{r['estado']}: {r['que_traer'][:90]}" for r in vivas})}


salida = {}
for metodo in ("llm", "B1", "B2", "B3", "B4"):
    rs = [r for r in filas if r["metodo"] == metodo]
    limpias = [r for r in rs if all(p.startswith("F") for p in r["productos"])]
    salida[metodo] = {"todo": resumen(rs), "limpio_productos_nuevos": resumen(limpias)}
(Path(__file__).parent / f"resultado_{particion}.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
for m, v in salida.items():
    print(m, {k: v["todo"][k] for k in ("propuestas", "no_descartadas_distintas", "sobreviven", "proporcion")},
          "| limpio:", {k: v["limpio_productos_nuevos"][k] for k in ("propuestas", "no_descartadas_distintas")})
