"""Desacuerdos entre el criterio viejo (lo escribía quien proponía) y el juez, para etiquetarlos a ciegas.

    python data/evaluacion/equivalencias/muestra.py <equivalencias_nuevas.json>
        -> data/evaluacion/equivalencias/a_ciegas.json (sin saber qué método dijo qué)
           data/evaluacion/equivalencias/clave.json    (qué dijo cada uno; se abre después de etiquetar)
"""
import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ))
from harness.correr import busquedas_capturadas  # noqa: E402
from harness.equivalencias import clave  # noqa: E402
from harness.voces import productos, sin_acentos  # noqa: E402


def criterio_viejo(titulo: str, criterio: dict) -> bool:
    """El que escribía el LLM que proponía (borrado de harness/chequeos.py; está en el historial)."""
    t = sin_acentos(titulo)
    if any(t.startswith(sin_acentos(e)) for e in criterio.get("no_empieza_con", [])):
        return False
    if criterio.get("empieza_con") and not any(t.startswith(sin_acentos(e)) for e in criterio["empieza_con"]):
        return False
    if any(sin_acentos(x) in t for x in criterio.get("excluir", [])):
        return False
    return all(any(sin_acentos(s) in t for s in grupo) for grupo in criterio.get("todos", []))


juicios = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
capturas, anclas = busquedas_capturadas(), {sin_acentos(p["titulo"]) for p in productos().values()}
desacuerdos = []
for f in sorted((RAIZ / "data/evaluacion/versiones_escala_dev").glob("eval-personas-libres_*.json")):
    for o in json.loads(f.read_text(encoding="utf-8"))["oportunidades"]:
        k = clave(o["que_traer"], o["busqueda_ml"])
        if k not in juicios or o["busqueda_ml"] not in capturas:
            continue
        juez = {sin_acentos(t) for t in juicios[k]}
        for x in capturas[o["busqueda_ml"]]["publicaciones"]:
            t = sin_acentos(x["titulo"])
            if not t or t in anclas:
                continue
            viejo, nuevo = criterio_viejo(x["titulo"], o.get("criterio_equivalencia", {})), t in juez
            if viejo != nuevo:
                desacuerdos.append({"propuesta": o["que_traer"], "para_que": o.get("alivia", ""), "publicacion": x["titulo"],
                                    "vendidos": x["vendidos"], "viejo": viejo, "juez": nuevo})
unicos = list({(d["propuesta"], d["publicacion"]): d for d in desacuerdos}.values())
muestra = random.Random(7).sample(unicos, min(40, len(unicos)))
(AQUI / "a_ciegas.json").write_text(json.dumps([{"n": i, "propuesta": d["propuesta"], "para_que": d["para_que"],
                                                  "publicacion": d["publicacion"], "es_equivalente": None}
                                                 for i, d in enumerate(muestra)], ensure_ascii=False, indent=1), encoding="utf-8")
(AQUI / "clave.json").write_text(json.dumps([{"n": i, "viejo": d["viejo"], "juez": d["juez"], "vendidos": d["vendidos"]}
                                             for i, d in enumerate(muestra)], ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(unicos)} desacuerdos; muestra de {len(muestra)}; "
      f"el juez suma {sum(d['juez'] for d in unicos)} y saca {sum(d['viejo'] for d in unicos)}")
