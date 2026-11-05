"""LLM juez: puntúa la planilla con la misma rúbrica que los humanos.

Escribe data/evaluacion/juicios_juez_llm.csv, así `make juicios` lo trata como un juez más
y calcula su acuerdo (kappa) con cada persona. Solo se usa para escalar la evaluación si
el kappa contra los humanos es aceptable (>= 0,6); si no, se reporta y no se usa.

    ANTHROPIC_API_KEY=... python scripts/juez_llm.py
"""
import csv
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from harness.divergente import MODELO, texto_vista  # noqa: E402

D = RAIZ / "data/evaluacion"
RUBRICA = (D / "COMO_JUZGAR.md").read_text(encoding="utf-8")


def juzgar(cliente, item: dict, cap: dict) -> dict:
    vistas = "\n\n".join(texto_vista(b.strip(), cap[b.strip()]["publicaciones"]) for b in item["busqueda"].split("+"))
    pedido = (f"{RUBRICA}\n\n---\nDatos:\n{vistas}\n\n---\nÍtem a juzgar:\n{item['texto']}\n\n"
              'Respondé SOLO con JSON: {"sostenida_1a3": n, "no_obvia_1a3": n, "accionable_1a3": n, "comentario": "una línea"}')
    r = cliente.messages.create(model=MODELO, max_tokens=300, messages=[{"role": "user", "content": pedido}])
    return json.loads(re.search(r"\{.*\}", r.content[0].text, re.S).group(0))


def main(cliente=None):
    if cliente is None:
        import anthropic
        cliente = anthropic.Anthropic()
    cap = json.loads((RAIZ / "data/capturas/captura_ml_2026-11-05.json").read_text(encoding="utf-8"))["busquedas"]
    filas = list(csv.DictReader((D / "planilla_juicios.csv").open()))
    with (D / "juicios_juez_llm.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        for fila in filas:
            j = juzgar(cliente, fila, cap)
            w.writerow({**fila, **{k: j[k] for k in ("sostenida_1a3", "no_obvia_1a3", "accionable_1a3")},
                        "juez": f"llm:{MODELO}", "comentario": j.get("comentario", "")})
    print(f"{len(filas)} ítems juzgados -> {D / 'juicios_juez_llm.csv'}")


if __name__ == "__main__":
    main()
