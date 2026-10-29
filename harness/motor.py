"""El motor del harness: estado, skills, caché, guardrails y traza.

Las políticas (fija, heurística, LLM) no tocan datos ni estado directamente: solo
llaman a cuatro operaciones del motor. Eso hace que las tres se comparen en igualdad
de condiciones y que todos los controles vivan en un solo lugar.

    proponer(pista_id, producto, tipo, razonamiento) -> hipotesis_id
    ejecutar(skill, hipotesis_id, producto)          -> observación (con evidencia_id)
    veredicto(hipotesis_id, decision, evidencias, justificacion)
    leer_skill(nombre)                               -> texto del SKILL.md
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from adapters import Adaptador, ErrorFuente

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
TIPOS = {"ausencia", "precio", "complemento"}
DECISIONES = {"confirmar", "descartar", "insuficiente"}


class Rechazo(Exception):
    """Un guardrail rechazó la operación. Vuelve a la política como observación."""


def cargar_skills(directorio: Path = SKILLS_DIR) -> dict[str, dict]:
    skills = {}
    for md in sorted(directorio.glob("*/SKILL.md")):
        texto = md.read_text(encoding="utf-8")
        _, front, cuerpo = texto.split("---", 2)
        meta = {}
        for linea in front.strip().splitlines():
            k, v = linea.split(":", 1)
            meta[k.strip()] = v.strip()
        meta["toca_datos"] = meta.get("toca_datos", "false") == "true"
        meta["cuerpo"] = cuerpo.strip()
        skills[meta["name"]] = meta
    return skills


@dataclass
class Presupuesto:
    max_skills_por_hipotesis: int = 6
    max_pasos: int = 80


@dataclass
class Motor:
    adaptador: Adaptador
    pistas: list[dict]
    presupuesto: Presupuesto = field(default_factory=Presupuesto)
    ruta_cache: Path | None = None

    def __post_init__(self):
        self.skills = cargar_skills()
        self.hipotesis: dict[str, dict] = {}
        self.evidencias: dict[str, dict] = {}
        self.veredictos: dict[str, dict] = {}
        self.traza: list[dict] = []
        self.pasos = 0
        self.cache_hits = 0
        self.llamadas_fuente = 0
        self.cache: dict[str, dict] = {}
        if self.ruta_cache and self.ruta_cache.exists():
            self.cache = json.loads(self.ruta_cache.read_text(encoding="utf-8"))
        self._pista_ids = {p["id"] for p in self.pistas}

    # ---------- utilidades ----------

    def _log(self, evento: str, **datos):
        self.traza.append({"t": round(time.time(), 3), "paso": self.pasos, "evento": evento, **datos})

    def _paso(self):
        self.pasos += 1
        if self.pasos > self.presupuesto.max_pasos:
            raise Rechazo(f"presupuesto agotado: más de {self.presupuesto.max_pasos} pasos")

    def guardar_cache(self):
        if self.ruta_cache:
            self.ruta_cache.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---------- operaciones ----------

    def leer_skill(self, nombre: str) -> str:
        if nombre not in self.skills:
            raise Rechazo(f"skill desconocida '{nombre}'. Disponibles: {sorted(self.skills)}")
        self._log("leer_skill", skill=nombre)
        return self.skills[nombre]["cuerpo"]

    def proponer(self, pista_id: str, producto: str, tipo: str, razonamiento: str) -> str:
        self._paso()
        if pista_id not in self._pista_ids:
            raise Rechazo(f"pista inexistente '{pista_id}'")
        if tipo not in TIPOS:
            raise Rechazo(f"tipo inválido '{tipo}'. Usar uno de {sorted(TIPOS)}")
        if not producto.strip():
            raise Rechazo("producto vacío")
        hid = f"H{len(self.hipotesis) + 1}"
        self.hipotesis[hid] = {"id": hid, "pista_id": pista_id, "producto": producto.strip(),
                               "tipo": tipo, "razonamiento": razonamiento, "evidencias": []}
        self._log("proponer", hipotesis=hid, pista_id=pista_id, producto=producto, tipo=tipo,
                  razonamiento=razonamiento)
        return hid

    def ejecutar(self, skill: str, hipotesis_id: str, producto: str | None = None) -> dict:
        self._paso()
        if skill not in self.skills:
            raise Rechazo(f"skill desconocida '{skill}'. Disponibles: {sorted(self.skills)}")
        h = self.hipotesis.get(hipotesis_id)
        if h is None:
            raise Rechazo(f"hipótesis inexistente '{hipotesis_id}'")
        if hipotesis_id in self.veredictos:
            raise Rechazo(f"{hipotesis_id} ya tiene veredicto; no se puede seguir probando")
        if len(h["evidencias"]) >= self.presupuesto.max_skills_por_hipotesis:
            raise Rechazo(f"{hipotesis_id} agotó su presupuesto de {self.presupuesto.max_skills_por_hipotesis} skills")

        producto = (producto or h["producto"]).strip()
        clave = hashlib.sha1(f"{self.adaptador.nombre}|{skill}|{producto.lower()}".encode()).hexdigest()[:16]
        desde_cache = clave in self.cache
        if desde_cache:
            res = self.cache[clave]
            self.cache_hits += 1
        else:
            self.llamadas_fuente += 1
            try:
                res = {"ok": True, "datos": getattr(self.adaptador, skill)(producto)}
            except ErrorFuente as e:
                res = {"ok": False, "error": e.codigo, "detalle": e.detalle}
            self.cache[clave] = res

        eid = f"E{len(self.evidencias) + 1}"
        ev = {"id": eid, "hipotesis_id": hipotesis_id, "skill": skill, "producto": producto,
              "cache": desde_cache, **res}
        self.evidencias[eid] = ev
        h["evidencias"].append(eid)
        self._log("ejecutar", evidencia=eid, hipotesis=hipotesis_id, skill=skill, producto=producto,
                  cache=desde_cache, resultado=res)
        return ev

    def veredicto(self, hipotesis_id: str, decision: str, evidencias: list[str], justificacion: str):
        self._paso()
        h = self.hipotesis.get(hipotesis_id)
        if h is None:
            raise Rechazo(f"hipótesis inexistente '{hipotesis_id}'")
        if decision not in DECISIONES:
            raise Rechazo(f"decisión inválida '{decision}'. Usar {sorted(DECISIONES)}")
        if hipotesis_id in self.veredictos:
            raise Rechazo(f"{hipotesis_id} ya tiene veredicto")

        # GUARDRAIL CENTRAL: confirmar o descartar exige evidencia propia, exitosa y que
        # haya tocado datos. El modelo no puede decidir sobre una hipótesis sin haberla
        # sometido al mundo. "insuficiente" es la salida honesta cuando no se pudo.
        validas = [e for e in evidencias
                   if e in self.evidencias
                   and self.evidencias[e]["hipotesis_id"] == hipotesis_id
                   and self.evidencias[e]["ok"]
                   and self.skills[self.evidencias[e]["skill"]]["toca_datos"]]
        if decision in {"confirmar", "descartar"} and not validas:
            self._log("rechazo", hipotesis=hipotesis_id, motivo="veredicto sin evidencia válida",
                      decision=decision, evidencias_citadas=evidencias)
            raise Rechazo(f"'{decision}' necesita al menos una evidencia exitosa de {hipotesis_id} "
                          f"que haya tocado datos. Citadas: {evidencias}. Si no se pudo verificar, "
                          f"usar 'insuficiente'.")
        invalidas = sorted(set(evidencias) - set(validas))
        self.veredictos[hipotesis_id] = {"hipotesis_id": hipotesis_id, "pista_id": h["pista_id"],
                                         "decision": decision, "evidencias": validas,
                                         "evidencias_descartadas": invalidas,
                                         "justificacion": justificacion}
        self._log("veredicto", hipotesis=hipotesis_id, decision=decision, evidencias=validas,
                  justificacion=justificacion)

    # ---------- cierre ----------

    def pistas_sin_veredicto(self) -> list[str]:
        cubiertas = {v["pista_id"] for v in self.veredictos.values()}
        return sorted(self._pista_ids - cubiertas)

    def decision_por_pista(self) -> dict[str, dict]:
        """Una pista puede tener varias hipótesis. Gana confirmar > descartar > insuficiente."""
        orden = {"confirmar": 2, "descartar": 1, "insuficiente": 0}
        out: dict[str, dict] = {}
        for v in self.veredictos.values():
            actual = out.get(v["pista_id"])
            if actual is None or orden[v["decision"]] > orden[actual["decision"]]:
                out[v["pista_id"]] = v
        for pid in self.pistas_sin_veredicto():
            out[pid] = {"pista_id": pid, "decision": "sin_veredicto", "evidencias": [],
                        "justificacion": "la política terminó sin decidir"}
        return out
