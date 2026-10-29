"""Arma out/reporte.html a partir de las corridas guardadas en out/.

Muestra la comparación entre políticas y el expediente de cada pista: qué hipótesis se
formó, qué verificaciones corrió, qué devolvió cada una y por qué se decidió lo que se decidió.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "out"
ORDEN = ["fija", "heuristica", "react_llm"]
NOMBRE = {"fija": "Fija (todas las skills)", "heuristica": "Heurística (corta al refutar)",
          "react_llm": "Agente ReAct (LLM)"}
e = html.escape


def cargar():
    corridas = {}
    for p in ORDEN:
        r, s = OUT / f"{p}.resumen.json", OUT / f"{p}.estado.json"
        if r.exists() and s.exists():
            corridas[p] = (json.loads(r.read_text(encoding="utf-8")), json.loads(s.read_text(encoding="utf-8")))
    return corridas


def fmt_datos(ev):
    if not ev["ok"]:
        return f'<span class="err">{e(ev["error"])}</span> <span class="dim">{e(ev["detalle"])}</span>'
    d = {k: v for k, v in ev["datos"].items() if k not in ("fuente", "producto_resuelto", "ejemplos")}
    partes = [f'<span class="k">{e(k)}</span> {e(json.dumps(v, ensure_ascii=False))}' for k, v in d.items()]
    ejemplos = ev["datos"].get("ejemplos") or []
    if ejemplos:
        partes.append(f'<q>{e(ejemplos[0]["texto"])}</q>')
    return " · ".join(partes)


def tabla_comparacion(corridas):
    filas = []
    for p, (r, _) in corridas.items():
        costo = "—" if p != "react_llm" else f'USD {r["costo_usd"]:.4f}'
        filas.append(
            f'<tr><th scope="row">{e(NOMBRE[p])}</th>'
            f'<td class="n">{r["accuracy"] * 100:.0f}%</td>'
            f'<td class="n">{r["skills_por_pista"]}</td>'
            f'<td class="n">{r["llamadas_a_fuente"]}</td>'
            f'<td class="n">{r["rechazos_guardrail"]}</td>'
            f'<td class="n">{costo}</td></tr>')
    if "react_llm" not in corridas:
        filas.append('<tr class="pend"><th scope="row">Agente ReAct (LLM)</th>'
                     '<td colspan="5">Pendiente: requiere <code>ANTHROPIC_API_KEY</code>. '
                     'Se corre con <code>make agente</code>.</td></tr>')
    return ("<div class='scroll'><table class='cmp'><thead><tr><th>Política</th><th>Aciertos</th>"
            "<th>Skills por pista</th><th>Llamadas a la fuente</th><th>Rechazos del guardrail</th>"
            "<th>Costo LLM</th></tr></thead><tbody>" + "".join(filas) + "</tbody></table></div>")


def expedientes(resumen, estado):
    pistas = {p["id"]: p for p in estado["pistas"]}
    por_pista = {f["pista"]: f for f in resumen["por_pista"]}
    bloques = []
    for pid, p in pistas.items():
        hs = [h for h in estado["hipotesis"].values() if h["pista_id"] == pid]
        f = por_pista[pid]
        cuerpo = []
        for h in hs:
            v = estado["veredictos"].get(h["id"], {})
            pasos = "".join(
                f'<li><span class="skill">{e(estado["evidencias"][eid]["skill"])}</span>'
                f'<span class="eid">{e(eid)}</span> {fmt_datos(estado["evidencias"][eid])}</li>'
                for eid in h["evidencias"])
            cuerpo.append(
                f'<div class="hip"><p class="hline"><span class="tipo">{e(h["tipo"])}</span> '
                f'buscado como <b>{e(h["producto"])}</b></p>'
                f'<ol class="pasos">{pasos}</ol>'
                f'<p class="just"><span class="sello s-{e(v.get("decision", "sin_veredicto"))}">'
                f'{e(v.get("decision", "sin veredicto"))}</span> {e(v.get("justificacion", ""))}</p></div>')
        acierto = "coincide" if f["acierto"] else "no coincide"
        bloques.append(
            f'<article class="exp"><header><span class="pid">{e(pid)}</span>'
            f'<span class="senal">{e(p["senal"].replace("_", " "))}</span>'
            f'<span class="vs {"ok" if f["acierto"] else "bad"}">verdad: {e(f["verdad"])} · {acierto}</span></header>'
            f'<p class="texto">{e(p["texto"])}</p>{"".join(cuerpo)}</article>')
    return "".join(bloques)


def main():
    corridas = cargar()
    if not corridas:
        sys.exit("No hay corridas en out/. Correr make demo primero.")
    sintetico = any(r["datos_sinteticos"] for r, _ in corridas.values())
    exp_pol = "heuristica" if "heuristica" in corridas else next(iter(corridas))
    if "react_llm" in corridas:
        exp_pol = "react_llm"
    r_exp, s_exp = corridas[exp_pol]

    plantilla = (RAIZ / "reporte_plantilla.html").read_text(encoding="utf-8")
    pagina = (plantilla
              .replace("{{AVISO}}", '<div class="aviso"><b>Datos sintéticos.</b> Esta corrida prueba el '
                       'mecanismo del harness. Ningún número sale de una fuente real y nada de esto es un hallazgo.</div>'
                       if sintetico else "")
              .replace("{{DIAGRAMA}}", (RAIZ / "docs/arquitectura.svg").read_text(encoding="utf-8"))
              .replace("{{TABLA}}", tabla_comparacion(corridas))
              .replace("{{EXP_POL}}", e(NOMBRE[exp_pol]))
              .replace("{{EXPEDIENTES}}", expedientes(r_exp, s_exp)))
    destino = OUT / "reporte.html"
    destino.write_text(pagina, encoding="utf-8")
    print(f"reporte: {destino}")


if __name__ == "__main__":
    main()
