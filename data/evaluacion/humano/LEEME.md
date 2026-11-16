# Juicio humano a ciegas

Los dos jueces LLM del embudo (C1: ¿el texto muestra el dolor sin resolver?; C4 a C6: ¿esta
publicación reemplaza a lo propuesto?) se validaron con controles y con un etiquetado de Claude.
Falta compararlos con personas.

**Qué hacer (unos 30 minutos):** abrí `planilla_<tu nombre>.csv` (Excel o Google Sheets) y en la
columna `respuesta` poné `si` o `no` en las 80 filas. No mires `clave.json`: ahí está lo que dijo
el modelo. Guardá como CSV con el mismo nombre y commiteá el archivo.

- **dolor** (40): `a` es el problema; `b`, lo que escribió una persona. ¿El texto muestra que esa
  persona tiene ese problema y no lo resolvió? Si lo menciona pero ya lo resolvió, o no se puede
  saber, `no`.
- **equivalencia** (40): `a` es lo que se propone traer; `b`, una publicación de Mercado Libre.
  ¿Alguien que quiere lo propuesto podría comprar esa publicación en su lugar? Mismo tipo de
  producto o un sustituto directo, aunque cambie marca o tamaño: `si`. Un accesorio, un repuesto
  o algo que solo comparte palabras: `no`.

Cuando estén las planillas: `python data/evaluacion/humano/calibrar.py` calcula el acuerdo entre
nosotros (kappa de Fleiss) y del modelo contra la mayoría (acuerdo, kappa de Cohen, precisión,
exhaustividad). Armado con `armar_planillas.py` (semilla fija).
