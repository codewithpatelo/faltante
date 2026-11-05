"""Etapa divergente con LLM: lee los votos de una búsqueda y devuelve hipótesis validadas.

Patrón evaluador-optimizador de la clase 9: el LLM propone, `validar_hipotesis` (código,
no LLM) revisa las citas, y si hay errores se los devuelve al modelo una vez para que
corrija. Lo que sigue fallando se descarta y queda en la traza: nunca entra una hipótesis
con citas inventadas.

    ANTHROPIC_API_KEY=... python -m harness.divergente data/capturas/captura_ml_2026-11-05.json --dev
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from .votos import contraste_terminos, validar_hipotesis, vista

RAIZ = Path(__file__).resolve().parent.parent
MODELO = "claude-haiku-4-5"
PRECIO_MTOK = {"entrada": 1.0, "salida": 5.0}  # USD por millón de tokens (Haiku 4.5)
MAX_REINTENTOS = 1


def texto_vista(busqueda: str, pubs: list[dict]) -> str:
    v = vista(pubs)
    lineas = [f"### {busqueda} — ventas visibles {v['ventas_visibles']}", "GANAN:"]
    lineas += [f"[{p['i']}] +{p['vendidos']} ${(p['precio'] or 0)//1000}k {'INTL ' if p['internacional'] else ''}{p['titulo']}" for p in v["ganan"]]
    lineas.append("PIERDEN:")
    lineas += [f"[{p['i']}] ${(p['precio'] or 0)//1000}k {'INTL ' if p['internacional'] else ''}{p['titulo']}" for p in v["pierden"]]
    return "\n".join(lineas)


def prompt(busqueda: str, pubs: list[dict]) -> str:
    skill = (RAIZ / "skills/leer_votos/SKILL.md").read_text(encoding="utf-8")
    return (f"{skill}\n\n---\n\n{texto_vista(busqueda, pubs)}\n\n"
            f"Respondé SOLO con un JSON: {{\"hipotesis\": [...]}}. En cada cita usá \"busqueda\": \"{busqueda}\".")


def _json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto, re.S)
    return json.loads(m.group(0)) if m else {"hipotesis": []}


def leer_busqueda(cliente, busqueda: str, pubs: list[dict], traza: list) -> list[dict]:
    """Una búsqueda: propone, valida en código, reintenta una vez con los errores."""
    mensajes = [{"role": "user", "content": prompt(busqueda, pubs)}]
    fuente = {busqueda: pubs}
    for intento in range(MAX_REINTENTOS + 1):
        t0 = time.time()
        r = cliente.messages.create(model=MODELO, max_tokens=2000, messages=mensajes)
        texto = r.content[0].text
        uso = {"entrada": r.usage.input_tokens, "salida": r.usage.output_tokens}
        hs = _json(texto).get("hipotesis", [])
        errores = {h.get("id", f"#{k}"): validar_hipotesis(h, fuente) for k, h in enumerate(hs)}
        traza.append({"busqueda": busqueda, "intento": intento, "segundos": round(time.time() - t0, 2),
                      "tokens": uso, "hipotesis": len(hs), "errores": {k: v for k, v in errores.items() if v}})
        if not any(errores.values()):
            return hs
        if intento < MAX_REINTENTOS:
            mensajes += [{"role": "assistant", "content": texto},
                         {"role": "user", "content": "El validador rechazó estas citas:\n"
                          + json.dumps({k: v for k, v in errores.items() if v}, ensure_ascii=False)
                          + "\nCorregí o sacá esas hipótesis. Respondé SOLO con el JSON."}]
    return [h for k, h in enumerate(hs) if not errores.get(h.get("id", f"#{k}"))]


def costo(traza: list) -> dict:
    ent = sum(t["tokens"]["entrada"] for t in traza)
    sal = sum(t["tokens"]["salida"] for t in traza)
    usd = ent / 1e6 * PRECIO_MTOK["entrada"] + sal / 1e6 * PRECIO_MTOK["salida"]
    return {"tokens_entrada": ent, "tokens_salida": sal, "usd": round(usd, 4),
            "segundos": round(sum(t["segundos"] for t in traza), 1)}


def main(captura: Path, busquedas: list[str], cliente=None) -> dict:
    if cliente is None:
        import anthropic
        cliente = anthropic.Anthropic()
    cap = json.loads(captura.read_text(encoding="utf-8"))["busquedas"]
    traza, salida = [], {"modelo": MODELO, "captura": str(captura.relative_to(RAIZ)) if captura.is_relative_to(RAIZ) else str(captura),
                         "hipotesis": [], "baseline": {}}
    for b in busquedas:
        salida["hipotesis"] += leer_busqueda(cliente, b, cap[b]["publicaciones"], traza)
        salida["baseline"][b] = contraste_terminos(cap[b]["publicaciones"])
    salida["costo"] = costo(traza)
    salida["traza"] = traza
    return salida


if __name__ == "__main__":
    cap = Path(sys.argv[1])
    pedidas = sys.argv[2:]
    if pedidas in (["--dev"], ["--test"]):
        pedidas = json.loads((RAIZ / "data/divergente/particion.json").read_text(encoding="utf-8"))[pedidas[0][2:]]
    out = main(cap, pedidas)
    destino = RAIZ / "out/divergente_llm.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out['hipotesis'])} hipótesis validadas; costo {out['costo']} -> {destino}")
