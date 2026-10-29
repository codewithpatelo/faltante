"""Políticas sin LLM: los baselines contra los que se mide el agente.

- PoliticaFija: corre TODAS las skills sobre TODAS las pistas y decide con reglas.
  Es "el mismo set de skills, sin loop". Si el agente no le gana a esto, el loop sobra.
- PoliticaHeuristica: mismas reglas, pero elige la próxima skill según lo observado y
  corta apenas una hipótesis queda refutada. Es un ReAct escrito a mano, sin modelo.

Las dos tipan y nombran el producto con lo que trae la pista, sin interpretar el texto.
Esa es su debilidad esperada: no resuelven nombres informales ni infieren el producto
real detrás de un workaround. Ahí es donde se mide el aporte del LLM.
"""

from __future__ import annotations

from .motor import Motor, Rechazo

TIPO_POR_SENAL = {
    "ranking_courier": "precio",
    "pico_courier": "precio",
    "usado_a_precio_de_nuevo": "complemento",
    "workaround": "complemento",
    "quejas_texto": "complemento",
}


def evaluar(r: dict[str, dict]) -> tuple[str | None, str]:
    """Reglas de decisión. Traducen la sección 'Cómo interpretarla' de cada SKILL.md.

    Devuelve (decision, motivo). decision=None significa 'todavía no se puede decidir'.
    """
    via = r.get("viabilidad")
    if via and via["bloqueante"]:
        return "descartar", f"barrera bloqueante: {', '.join(via['barreras'])}"
    per = r.get("persistencia")
    if per and per["meses_con_senal"] / per["de_meses"] < 0.5:
        return "descartar", f"pico, no tendencia ({per['meses_con_senal']}/{per['de_meses']} meses)"
    of = r.get("contar_oferta")
    rp = r.get("ratio_precio")
    if of and of["vendedores"] >= 15 and rp:
        if rp["ratio"] is None or rp["ratio"] < 1.8:
            return "descartar", f"hay oferta ({of['vendedores']} vendedores) y no hay arbitraje (ratio {rp['ratio']})"
    if of is None or per is None or via is None:
        return None, "faltan verificaciones"
    if of["vendedores"] >= 15:
        if rp is None:
            return None, "falta ratio de precio"
        return "confirmar", f"voto de precio: {of['vendedores']} vendedores y ratio {rp['ratio']}"
    return "confirmar", f"hueco: {of['vendedores']} vendedores, señal en {per['meses_con_senal']}/{per['de_meses']} meses"


def siguiente_skill(r: dict) -> str | None:
    if "contar_oferta" not in r:
        return "contar_oferta"
    if r["contar_oferta"]["vendedores"] >= 15 and "ratio_precio" not in r:
        return "ratio_precio"
    for s in ("persistencia", "viabilidad", "voto_manos"):
        if s not in r:
            return s
    return None


class _Base:
    nombre = "base"

    def _hipotesis(self, m: Motor, p: dict) -> str:
        tipo = TIPO_POR_SENAL.get(p["senal"], "ausencia")
        return m.proponer(p["id"], p["producto_mencionado"], tipo, f"tipado por señal '{p['senal']}'")

    def _cerrar(self, m: Motor, hid: str, r: dict, evs: list[str], fallo: str | None):
        if fallo:
            m.veredicto(hid, "insuficiente", [], fallo)
            return
        decision, motivo = evaluar(r)
        m.veredicto(hid, decision or "insuficiente", evs, motivo)


class PoliticaFija(_Base):
    nombre = "fija"

    def correr(self, m: Motor):
        for p in m.pistas:
            hid = self._hipotesis(m, p)
            r, evs, fallo = {}, [], None
            for s in ("contar_oferta", "ratio_precio", "persistencia", "voto_manos", "viabilidad"):
                ev = m.ejecutar(s, hid)
                if ev["ok"]:
                    r[s], _ = ev["datos"], evs.append(ev["id"])
                elif fallo is None:
                    fallo = f"{s} falló: {ev['error']} ({ev['detalle']})"
            self._cerrar(m, hid, r, evs, fallo)


class PoliticaHeuristica(_Base):
    nombre = "heuristica"

    def correr(self, m: Motor):
        for p in m.pistas:
            hid = self._hipotesis(m, p)
            r, evs, fallo = {}, [], None
            while (s := siguiente_skill(r)) is not None:
                try:
                    ev = m.ejecutar(s, hid)
                except Rechazo:
                    break
                if not ev["ok"]:
                    fallo = f"{s} falló: {ev['error']} ({ev['detalle']})"
                    break
                r[s] = ev["datos"]
                evs.append(ev["id"])
                decision, _ = evaluar(r)
                if decision == "descartar":
                    break
            self._cerrar(m, hid, r, evs, fallo)
