"""El embudo convergente: la lista de chequeos que tiene que pasar una propuesta para que la
recomendemos. Se leen de arriba abajo; la primera que falla, mata la propuesta y queda el
motivo. El detalle de cada chequeo está en `harness/chequeos.py`; los umbrales, en
`harness/umbrales.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

from harness import chequeos as c
from harness.voces import textos_con_id


@dataclass(frozen=True)
class Chequeo:
    nombre: str
    pregunta: str
    funcion: object


EMBUDO = [
    Chequeo("guardrail", "¿Las citas del LLM existen, son literales y vienen de 2 o más textos?", c.guardrail),
    Chequeo("C1 verificada", "¿La señal aparece en 3 o más textos, contando todos y no solo los que leyó el LLM?", c.c1_verificada),
    Chequeo("C2 sub-atendida", "¿Importa y está mal resuelta (puntaje de oportunidad de Ulwick)?", c.c2_subatendida),
    Chequeo("C3 demanda", "¿El producto donde aparece la señal vende +500?", c.c3_demanda),
    Chequeo("C4 hueco", "¿Hay 2 o menos equivalentes en Mercado Libre que ya vendan +100?", c.c4_hueco),
    Chequeo("C5 margen", "¿Deja 30% o más sobre el costo puesto, al precio que la gente paga?", c.c5_margen),
]


@dataclass
class Propuesta:
    """Qué traer, quién lo propuso, a partir de qué producto y con qué señales."""
    metodo: str                    # "llm", "B1" o "B2"
    producto: dict                 # el producto ancla, con sus opiniones y preguntas
    oportunidad: dict              # que_traer, busqueda_ml, criterio_equivalencia, señales
    señales_citadas: list[dict]    # las señales que la sostienen, como las escribió quien propone
    verifica_citas: bool = True    # los baselines no citan textos
    fob: dict | None = None        # precio de proveedor (data/serendipia/fob_*.json), si lo hay
    captura: dict | None = None    # la búsqueda de Mercado Libre de lo propuesto, para C4 y C5
    titulos_ancla: set = field(default_factory=set)

    @cached_property
    def señales(self) -> list[dict]:
        """Cada señal con los errores de sus citas y su medición sobre todos los textos."""
        textos = textos_con_id(self.producto)
        return [{"id": s["id"], "descripcion": s["descripcion"],
                 "errores": c.errores_de_citas(s, textos) if self.verifica_citas else [],
                 "medida": c.medir(s, textos)} for s in self.señales_citadas]

    @property
    def señales_validas(self) -> list[dict]:
        return [s for s in self.señales if not s["errores"]]


def recorrer(p: Propuesta) -> dict:
    """Pasa la propuesta por el embudo y devuelve su recorrido: estado final
    (sobrevive / condicional / muere), dónde murió, por qué, y cada chequeo con sus datos."""
    recorrido = []
    for chequeo in EMBUDO:
        r = chequeo.funcion(p)
        recorrido.append({"chequeo": chequeo.nombre, "pasa": r.pasa, "motivo": r.motivo, **({"datos": r.datos} if r.datos else {})})
        if not r.pasa:
            estado = "condicional" if r.condicional else "muere"
            return _resultado(p, estado, chequeo.nombre, r.motivo, recorrido)
    return _resultado(p, "sobrevive", None, recorrido[-1]["motivo"], recorrido)


def _resultado(p: Propuesta, estado: str, donde: str | None, motivo: str, recorrido: list) -> dict:
    return {"metodo": p.metodo, "producto": p.producto["id"], "ancla": p.producto["titulo"][:60],
            "id": p.oportunidad["id"], "que_traer": p.oportunidad["que_traer"], "busqueda_ml": p.oportunidad["busqueda_ml"],
            "estado": estado, "se_detiene_en": donde, "motivo": motivo, "señales": p.señales, "recorrido": recorrido}
