"""PoliticaReAct: el agente. Un loop ReAct escrito a mano sobre la API de Anthropic.

Sin framework a propósito: son ~150 líneas y cada integrante tiene que poder explicarlas.

    while no terminó y quedan pasos:
        respuesta = modelo(historial)              # razona y elige herramientas
        para cada tool_use en la respuesta:
            observación = motor.<operación>(...)   # guardrails en código, no en el prompt
            historial += tool_result(observación)  # incluye rechazos como is_error
"""

from __future__ import annotations

import json
import os
import time

from .motor import Motor, Rechazo

# USD por millón de tokens. Verificar contra la página de precios antes de reportar.
PRECIOS = {
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0, "cache_read": 0.10, "cache_write": 1.25},
}

HERRAMIENTAS = [
    {"name": "leer_skill",
     "description": "Devuelve las instrucciones completas de una skill: cuándo usarla y cómo interpretar su resultado.",
     "input_schema": {"type": "object", "properties": {"nombre": {"type": "string"}}, "required": ["nombre"]}},
    {"name": "proponer_hipotesis",
     "description": "Fase divergente. Convierte una pista en una hipótesis tipada sobre un producto concreto. "
                    "Podés proponer más de una hipótesis por pista. 'producto' es el nombre con el que se va a buscar.",
     "input_schema": {"type": "object", "properties": {
         "pista_id": {"type": "string"},
         "producto": {"type": "string"},
         "tipo": {"type": "string", "enum": ["ausencia", "precio", "complemento"]},
         "razonamiento": {"type": "string"}},
         "required": ["pista_id", "producto", "tipo", "razonamiento"]}},
    {"name": "verificar",
     "description": "Fase convergente. Corre una skill de verificación sobre una hipótesis. Devuelve datos y un evidencia_id. "
                    "Si la fuente no encuentra el producto, podés reintentar con otro nombre en 'producto'.",
     "input_schema": {"type": "object", "properties": {
         "skill": {"type": "string"},
         "hipotesis_id": {"type": "string"},
         "producto": {"type": "string", "description": "opcional: nombre alternativo para buscar"}},
         "required": ["skill", "hipotesis_id"]}},
    {"name": "dar_veredicto",
     "description": "Cierra una hipótesis. confirmar/descartar exigen citar evidencias exitosas de esa hipótesis. "
                    "Si no se pudo verificar, usar 'insuficiente'.",
     "input_schema": {"type": "object", "properties": {
         "hipotesis_id": {"type": "string"},
         "decision": {"type": "string", "enum": ["confirmar", "descartar", "insuficiente"]},
         "evidencias": {"type": "array", "items": {"type": "string"}},
         "justificacion": {"type": "string"}},
         "required": ["hipotesis_id", "decision", "evidencias", "justificacion"]}},
    {"name": "terminar",
     "description": "Termina la corrida. Solo se acepta cuando todas las pistas tienen al menos un veredicto.",
     "input_schema": {"type": "object", "properties": {}}},
]


def _prompt_sistema(m: Motor) -> str:
    catalogo = "\n".join(f"- {n}: {s['description']}" for n, s in m.skills.items())
    pistas = json.dumps([{k: p[k] for k in ("id", "senal", "texto", "producto_mencionado")} for p in m.pistas],
                        ensure_ascii=False, indent=1)
    return f"""Sos un analista de oportunidades de importación para Argentina.

Recibís PISTAS: votos con los pies, comportamientos que sugieren demanda insatisfecha
(gente que compra afuera, que paga usado a precio de nuevo, que fabrica adaptadores).

Trabajás en dos fases, por pista:
1. DIVERGENTE: leé la pista e inferí qué producto concreto se demanda y de qué tipo es la oportunidad:
   - ausencia: el producto no se consigue en Argentina.
   - precio: existe, pero la gente paga mucho más que afuera y compra igual.
   - complemento: falta el repuesto o consumible de algo que la gente ya tiene.
   Ojo: el producto mencionado en la pista puede no ser el que hay que importar (un adaptador casero
   apunta al consumible que falta), y puede estar en otro idioma o con nombre informal.
2. CONVERGENTE: tratá de REFUTAR la hipótesis con las skills, de la más barata a la más cara.
   Cortá apenas quede refutada. No corras skills que no cambian la decisión.

Skills disponibles (leé una con leer_skill antes de usarla si no sabés interpretarla):
{catalogo}

Reglas que el sistema hace cumplir en código:
- No podés confirmar ni descartar sin evidencia exitosa de esa hipótesis.
- Cada hipótesis tiene un tope de {m.presupuesto.max_skills_por_hipotesis} skills.
- Toda pista necesita al menos un veredicto antes de terminar.

PISTAS:
{pistas}"""


class PoliticaReAct:
    nombre = "react_llm"

    def __init__(self, modelo: str = "claude-haiku-4-5", max_turnos: int = 40, cliente=None):
        if cliente is None:  # en tests se inyecta un cliente falso
            import anthropic  # import diferido: las otras políticas no necesitan la dependencia
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError("Falta ANTHROPIC_API_KEY para correr la política react_llm")
            cliente = anthropic.Anthropic()
        self.cliente = cliente
        self.modelo = modelo
        self.max_turnos = max_turnos
        self.uso = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}
        self.turnos = 0
        self.latencia_s = 0.0

    def costo_usd(self) -> float:
        p = PRECIOS.get(self.modelo)
        if not p:
            return float("nan")
        return sum(self.uso[k] * p[k] for k in self.uso) / 1e6

    def _despachar(self, m: Motor, nombre: str, args: dict) -> tuple[str, bool]:
        """Ejecuta una herramienta en el motor. Devuelve (contenido, es_error)."""
        try:
            if nombre == "leer_skill":
                return m.leer_skill(args["nombre"]), False
            if nombre == "proponer_hipotesis":
                hid = m.proponer_hipotesis(args["pista_id"], args["producto"], args["tipo"], args["razonamiento"])
                return json.dumps({"hipotesis_id": hid}), False
            if nombre == "verificar":
                ev = m.verificar(args["skill"], args["hipotesis_id"], args.get("producto"))
                return json.dumps({k: v for k, v in ev.items() if k != "cache"}, ensure_ascii=False), False
            if nombre == "dar_veredicto":
                m.dar_veredicto(args["hipotesis_id"], args["decision"], args.get("evidencias", []), args["justificacion"])
                return "ok", False
            if nombre == "terminar":
                faltan = m.pistas_sin_veredicto()
                if faltan:
                    raise Rechazo(f"no se puede terminar: pistas sin veredicto {faltan}")
                return "terminado", False
            raise Rechazo(f"herramienta desconocida '{nombre}'")
        except Rechazo as e:
            return f"RECHAZADO: {e}", True
        except KeyError as e:
            return f"RECHAZADO: falta el argumento {e}", True

    def correr(self, m: Motor):
        sistema = [{"type": "text", "text": _prompt_sistema(m), "cache_control": {"type": "ephemeral"}}]
        historial = [{"role": "user", "content": "Analizá todas las pistas y terminá."}]
        terminado = False
        while not terminado and self.turnos < self.max_turnos:
            self.turnos += 1
            t0 = time.time()
            resp = self.cliente.messages.create(model=self.modelo, max_tokens=2048, system=sistema,
                                                tools=HERRAMIENTAS, messages=historial)
            self.latencia_s += time.time() - t0
            u = resp.usage
            self.uso["in"] += u.input_tokens
            self.uso["out"] += u.output_tokens
            self.uso["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
            self.uso["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0

            historial.append({"role": "assistant", "content": resp.content})
            texto = " ".join(b.text for b in resp.content if b.type == "text").strip()
            if texto:
                m._log("razonamiento", texto=texto)

            resultados = []
            for b in resp.content:
                if b.type != "tool_use":
                    continue
                contenido, es_error = self._despachar(m, b.name, b.input)
                if b.name == "terminar" and not es_error:
                    terminado = True
                resultados.append({"type": "tool_result", "tool_use_id": b.id,
                                   "content": contenido, "is_error": es_error})
            if not resultados:  # el modelo contestó sin herramientas: lo empujamos a seguir
                faltan = m.pistas_sin_veredicto()
                if not faltan:
                    break
                historial.append({"role": "user", "content": f"Faltan veredictos para {faltan}. Seguí."})
            else:
                historial.append({"role": "user", "content": resultados})
        m._log("fin_agente", turnos=self.turnos, terminado=terminado, uso=self.uso, costo_usd=self.costo_usd())
