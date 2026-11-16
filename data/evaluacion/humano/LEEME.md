# Juicio humano a ciegas

Los dos jueces LLM del embudo (C1: ¿el texto muestra el dolor sin resolver?; C4 a C6: ¿esta
publicación reemplaza a lo propuesto?) se validaron con controles y con un etiquetado de Claude.
Falta compararlos con personas.

**Qué hacer (unos 30 minutos):** abrí `planilla_<tu nombre>.csv` (Excel o Google Sheets) y en la
columna `respuesta` poné `si` o `no` en las 80 filas. No mires `clave.json`: ahí está lo que dijo
el modelo. Guardá como CSV con el mismo nombre y commiteá el archivo.

Las 80 filas están mezcladas y son de **dos tipos con preguntas distintas** (la columna `tipo` dice
cuál es). No se responden igual: mirá `tipo` en cada fila antes de contestar.

- **dolor** (40): `a` es el problema; `b`, lo que escribió una persona. ¿El texto muestra que esa
  persona tiene ese problema y no lo resolvió? Si lo menciona pero ya lo resolvió, o no se puede
  saber, `no`.
- **equivalencia** (40): `a` es lo que se propone traer; `b`, el título de una publicación de
  Mercado Libre. Acá **no se busca ningún problema**: se compara un producto con otro. ¿Alguien
  que quiere `a` podría comprar `b` en su lugar? Lo que está entre paréntesis en `a` ("para: …")
  es solo el contexto de por qué se propuso; no hay que encontrarlo en `b`.
  - `si`: mismo tipo de producto o sustituto directo, aunque cambie la marca, el tamaño o el
    color. Ejemplo inventado: `a` = "taladro inalámbrico de 18 V con dos baterías", `b` =
    "Taladro atornillador a batería 18V Marca X".
  - `no`: un accesorio, un repuesto, o algo que solo comparte palabras con `a`. Ejemplo
    inventado: con ese mismo `a`, `b` = "Mechas para taladro x 20" o "Taladro de juguete para
    niños".

Cuando estén las planillas: `python data/evaluacion/humano/calibrar.py` calcula el acuerdo entre
nosotros (kappa de Fleiss) y del modelo contra la mayoría (acuerdo, kappa de Cohen, precisión,
exhaustividad). Armado con `armar_planillas.py` (semilla fija).

## Parte 2: calidad de las oportunidades (unos 15 minutos)

`oportunidades_<tu nombre>.csv` tiene las 37 oportunidades que el embudo no descartó en dev y en
test, del LLM y de los baselines, mezcladas y sin decir de dónde salió cada una. En cada fila,
`si` o `no` en tres columnas:

- `concreta`: ¿es un producto concreto que se le puede pedir a un proveedor?
- `obvia`: ¿se le ocurriría a cualquiera que vende en esa categoría?
- `la_cotizaria`: si fueras importador, ¿pedirías una cotización para probarla?

No mires `clave_oportunidades.json`. Después: `python data/evaluacion/humano/evaluar_oportunidades.py`
cuenta, por método, cuántas son concretas, no obvias y "la cotizaría" a la vez (mayoría humana).
