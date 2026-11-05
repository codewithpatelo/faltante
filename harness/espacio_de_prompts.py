"""El espacio de prompts del paso B (conectar señales de productos distintos en oportunidades).

Cada prompt es una combinación de decisiones de diseño sacadas de la literatura sobre
generación de hipótesis (ver DECISIONES.md). Se arman 25 combinaciones, se prueban todas sobre
los mismos productos de desarrollo y se optimiza la mejor (harness/optimizar_prompt.py).
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from harness.voces import RAIZ

BASE = (RAIZ / "skills/cruzar_senales/SKILL.md").read_text(encoding="utf-8")
CANTIDAD = 25
SEMILLA = 7

# Cada dimensión: nombre -> {opción: texto que agrega al prompt}
DIMENSIONES = {
    "estructura": {
        "todo_junto": "Mirá todas las señales juntas y proponé.",
        "inspiraciones_lejanas": (
            "Trabajá así: tomá cada señal como antecedente y buscá 1 a 3 señales de OTRAS búsquedas, lo más "
            "lejanas posible, que puedan inspirar un producto que resuelva el antecedente. Las señales parecidas "
            "solo traen ideas conocidas; las lejanas, ideas nuevas. Combiná antecedente e inspiración de dos o tres "
            "maneras distintas y quedate con la más fuerte."),
        "agrupar_primero": (
            "Trabajá así: primero agrupá las señales que expresan la misma necesidad de fondo aunque vengan de "
            "productos y búsquedas distintas. Después, para cada grupo de 2 o más productos, proponé qué traer."),
    },
    "abduccion": {
        "directa": "",
        "rival": ("Para cada oportunidad escribí también la explicación rival más fuerte (por qué las señales "
                  "podrían NO indicar que la gente compraría eso) en un campo \"explicacion_rival\"."),
        "sherlock": ("Razoná como un detective: primero listá las observaciones que no cierran (anomalías: lo que la "
                     "gente elige pese a un defecto, lo que deja pasar pese a una ventaja, usos que nadie previó). "
                     "Después proponé la explicación que da cuenta de varias anomalías a la vez, y lo que habría que "
                     "traer si esa explicación es cierta."),
    },
    "diversidad": {
        "una_pasada": "",
        "repreguntar": "",   # se implementa con una segunda llamada: "otras distintas de estas" (harness/explorar_prompts.py)
    },
    "rol": {
        "importador": "Sos un importador argentino que vive de encontrar lo que nadie trae.",
        "detective": "Sos un detective: las señales son pistas dispersas y tu trabajo es conectarlas.",
        "antropologo": "Sos un antropólogo del consumo: te importa qué revelan las elecciones sobre cómo vive la gente.",
    },
    "evitar_obvio": {
        "si": ("NO propongas: repuestos, consumibles o accesorios del mismo producto ancla, ni el mismo producto "
               "\"pero mejor\" (más grande, de otro material, con más piezas). Eso cualquiera lo ve."),
        "no": "",
    },
    "razonamiento": {
        "alto": "",
        "conciso": "Pensá lo necesario y de forma concisa antes de responder.",
    },
}


@dataclass(frozen=True)
class Variante:
    id: str
    opciones: dict

    @property
    def repreguntar(self) -> bool:
        return self.opciones["diversidad"] == "repreguntar"

    def prompt(self, señales: str) -> str:
        """El prompt completo: rol, skill base, las decisiones de esta variante y las señales."""
        o = self.opciones
        extra = [DIMENSIONES[d][o[d]] for d in ("estructura", "abduccion", "evitar_obvio", "razonamiento")]
        return "\n\n".join(x for x in (DIMENSIONES["rol"][o["rol"]], BASE, "## Cómo trabajar en esta corrida", *extra,
                                        "---", "SEÑALES VERIFICADAS", señales, "Respondé SOLO con el JSON de la salida.") if x)


def variantes(cantidad: int = CANTIDAD, semilla: int = SEMILLA) -> list[Variante]:
    """`cantidad` combinaciones distintas, al azar con semilla fija pero balanceadas: cada opción
    de cada dimensión aparece una cantidad parecida de veces, así se pueden comparar opciones."""
    nombres = list(DIMENSIONES)
    todas = [dict(zip(nombres, combo)) for combo in itertools.product(*(DIMENSIONES[d] for d in nombres))]
    random.Random(semilla).shuffle(todas)
    tope = {d: -(-cantidad // len(DIMENSIONES[d])) for d in nombres}          # techo de cantidad / opciones
    usos = {d: {o: 0 for o in DIMENSIONES[d]} for d in nombres}
    elegidas = []
    for combo in todas:
        if len(elegidas) == cantidad:
            break
        if all(usos[d][combo[d]] < tope[d] for d in nombres):
            elegidas.append(combo)
            for d in nombres:
                usos[d][combo[d]] += 1
    return [Variante(f"V{i + 1:02d}", o) for i, o in enumerate(elegidas)]
