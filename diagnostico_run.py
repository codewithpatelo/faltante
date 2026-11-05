"""Corre la política de diagnóstico sobre una foto capturada de Mercado Libre.

    python diagnostico_run.py [ruta_foto]

Sin argumento usa la foto más reciente de data/diagnostico/. Escribe
data/diagnostico/resultado_<fecha>.json y out/diagnostico.traza.jsonl.
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from adapters import AdaptadorSnapshotML  # noqa: E402
from harness.motor import Motor, Presupuesto  # noqa: E402
from harness.politicas import PoliticaDiagnostico  # noqa: E402
from harness.diagnostico import diagnosticar  # noqa: E402

foto = Path(sys.argv[1]) if len(sys.argv) > 1 else max((RAIZ / "data/diagnostico").glob("foto_ml_*.json"))
print(f"foto: {foto.name}\n")
ad = AdaptadorSnapshotML(foto)
pistas = [{"id": f"D{i+1}", "busqueda": b} for i, b in enumerate(ad.fotos)]
m = Motor(adaptador=ad, pistas=pistas, presupuesto=Presupuesto(max_pasos=400))
PoliticaDiagnostico().correr(m)

salida = []
for p in pistas:
    h = next(h for h in m.hipotesis.values() if h["pista_id"] == p["id"])
    v = m.veredictos[h["id"]]
    d = diagnosticar(ad.fotos[p["busqueda"]])
    salida.append({"busqueda": p["busqueda"], "veredicto": v["decision"], "motivo": v["justificacion"],
                   "chequeos_corridos": len(h["evidencias"]), "conclusion": d["conclusion"],
                   "resumen": d["resumen"], "chequeos": d["chequeos"]})
out = RAIZ / "data/diagnostico" / foto.name.replace("foto_ml_", "resultado_")
out.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
(RAIZ / "out").mkdir(exist_ok=True)
(RAIZ / "out/diagnostico.traza.jsonl").write_text("\n".join(json.dumps(t, ensure_ascii=False) for t in m.traza), encoding="utf-8")

for s in salida:
    r = s["resumen"]
    print(f"{s['veredicto']:<12} {s['conclusion']:<36} {s['busqueda']:<30} prod L{r['producto_local']}/{r['producto_local_vende']}v I{r['producto_intl']}/{r['producto_intl_vende']}v  "
          f"$prod {r['precio_producto_intl'] or r['precio_producto_local']}  $sust {r['precio_sustitutos_que_venden']}  ventas {r['ventas_visibles_total']}  [{s['chequeos_corridos']} chequeos]")
print("rechazos del guardrail:", sum(1 for t in m.traza if t["evento"] == "rechazo"))
