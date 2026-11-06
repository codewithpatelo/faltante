"""El embudo convergente. La divergencia (LLM) trae hipótesis no obvias; la convergencia mata
el humo. Cada chequeo es un supuesto crítico de la oportunidad y el dato que lo refuta. Se
leen de arriba abajo; el primer supuesto refutado descarta la propuesta y deja el motivo. El detalle de cada chequeo está en `harness/chequeos.py`; los umbrales, en
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
    supuesto: str       # lo que tiene que ser cierto para que la oportunidad sea real
    refutacion: str     # el dato que lo tira abajo
    funcion: object


EMBUDO = [
    Chequeo("guardrail", "Lo que dice el LLM está en los textos",
            "cita un texto que no existe, un fragmento que no está, o un solo texto", c.guardrail),
    Chequeo("C1 verificada", "La necesidad no es un caso aislado",
            "las palabras de la señal aparecen en menos de 3 textos (contando todos)", c.c1_verificada),
    Chequeo("C2 sub-atendida", "La necesidad importa y está mal resuelta",
            "puntaje de Ulwick: pocos la mencionan o la mayoría está conforme", c.c2_subatendida),
    Chequeo("C3 demanda", "Hay gente eligiendo el producto de origen",
            "el producto donde aparece la señal vende menos de +500", c.c3_demanda),
    Chequeo("C4 hueco", "Nadie la atiende todavía",
            "3 o más equivalentes ya venden +100", c.c4_hueco),
    Chequeo("C5 la eligen", "Si se ofrece, la gente la elige",
            "las alternativas con stock local y precio no atípico venden significativamente menos que lo que "
            "la misma gente compra en su búsqueda de origen: las tuvo enfrente y las dejó pasar", c.c5_la_eligen),
    Chequeo("C6 margen", "Deja plata al precio que la gente paga",
            "ganancia neta (después de comisión, impuestos, envío, publicidad y devoluciones) menor que la del "
            "comercio minorista (Damodaran); si alcanza solo con un FOB más bajo, queda condicional", c.c6_margen),
]


@dataclass
class Propuesta:
    """Qué traer, quién lo propuso, y de qué productos y señales sale."""
    metodo: str                    # "llm", "B1" o "B2"
    anclas: list[dict]             # los productos donde aparecen sus señales, con opiniones y preguntas
    oportunidad: dict              # que_traer, busqueda_ml, criterio_equivalencia
    señales_citadas: list[dict]    # cada una con "producto" (el ID del ancla donde apareció)
    verifica_citas: bool = True    # los baselines no citan textos
    fob: dict | None = None        # precio de proveedor (data/serendipia/fob_*.json), si lo hay
    captura: dict | None = None    # la búsqueda de Mercado Libre de lo propuesto, para C4, C5 y C6
    titulos_ancla: set = field(default_factory=set)
    capturas_de_origen: list = field(default_factory=list)   # las búsquedas de donde salieron las anclas, para C5

    @property
    def vendidos_del_ancla(self) -> int:
        """El producto de origen más elegido entre los que sostienen la propuesta."""
        return max(a["vendidos"] for a in self.anclas)

    @cached_property
    def señales(self) -> list[dict]:
        """Cada señal con los errores de sus citas y su medición sobre todos los textos de su producto."""
        textos = {a["id"]: textos_con_id(a) for a in self.anclas}
        return [{"id": f"{s['producto']}.{s['id']}", "descripcion": s["descripcion"],
                 "errores": c.errores_de_citas(s, textos[s["producto"]]) if self.verifica_citas else [],
                 "medida": c.medir(s, textos[s["producto"]])} for s in self.señales_citadas]

    @property
    def señales_validas(self) -> list[dict]:
        return [s for s in self.señales if not s["errores"]]


def recorrer(p: Propuesta) -> dict:
    """Pasa la propuesta por el embudo y devuelve su recorrido: estado final
    (sobrevive / condicional / descartada), dónde se detuvo, por qué, y cada chequeo con sus datos."""
    recorrido = []
    for chequeo in EMBUDO:
        r = chequeo.funcion(p)
        recorrido.append({"chequeo": chequeo.nombre, "supuesto": chequeo.supuesto, "pasa": r.pasa, "motivo": r.motivo, **({"datos": r.datos} if r.datos else {})})
        if not r.pasa:
            estado = "condicional" if r.condicional else "descartada"
            return _resultado(p, estado, chequeo.nombre, r.motivo, recorrido)
    return _resultado(p, "sobrevive", None, recorrido[-1]["motivo"], recorrido)


def _resultado(p: Propuesta, estado: str, donde: str | None, motivo: str, recorrido: list) -> dict:
    return {"metodo": p.metodo, "productos": [a["id"] for a in p.anclas], "anclas": [a["titulo"][:60] for a in p.anclas],
            "id": p.oportunidad["id"], "que_traer": p.oportunidad["que_traer"], "busqueda_ml": p.oportunidad["busqueda_ml"],
            "estado": estado, "se_detiene_en": donde, "motivo": motivo, "señales": p.señales, "recorrido": recorrido}
