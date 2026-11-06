# Faltante

**Qué hace:** encuentra productos que conviene importar para vender en Mercado Libre y que
nadie está trayendo. No parte de una lista de productos: parte de las **elecciones** de la
gente, que se ven de dos maneras.

- **Voto con los pies, lo que la gente hace:** frente a las opciones de una búsqueda, qué
  elige y qué deja pasar. Que algo se venda, solo, no dice nada; dice algo que se venda *en
  lugar de* otra cosa.
- **Voto con las manos, lo que la gente dice:** por qué eligió y qué le faltó. Opiniones de
  quienes compraron y preguntas de quienes todavía dudan.

Funciona como la selección natural. **La divergencia trae hipótesis no obvias:** un LLM cruza
las dos cosas y propone qué traer. **La convergencia mata el humo:** el programa lista los
supuestos críticos de cada propuesta (¿la necesidad es real?, ¿nadie la atiende?, ¿si se
ofrece, la gente la elige?, ¿deja plata?) y busca el dato que la tira abajo. Solo se
recomienda lo que sobrevive.

TP de IA Agéntica, Maestría en Explotación de Datos (UBA), 2026.

## ¿Sirve? Estado al 05/11/2026

**Todavía no. La convergencia funciona; la divergencia trae ideas triviales; y la muestra es
insignificante.**

| Pregunta | Respuesta hoy |
|---|---|
| ¿Mata el humo, con un motivo verificable? | **Sí.** De 14 propuestas descartó 13: 7 porque ya las vende alguien, 3 porque la gente tuvo la alternativa enfrente y la dejó pasar, 2 porque la señal era débil y 1 por citas mal hechas. |
| ¿Encuentra una oportunidad que sobreviva? | **No del todo.** Ninguna pasa todo. El disco de repuesto para afilador pasa solo si el proveedor cotiza ≤ USD 3,21 (catálogo: 2,60 a 3,30), con confianza baja. Detalle en [`OPORTUNIDADES.md`](OPORTUNIDADES.md). |
| ¿Las hipótesis son no obvias? | **No.** Repuestos, accesorios y versiones mejoradas del mismo producto: a cualquiera que mire el mercado se le ocurren. El LLM leyó cada producto por separado; lo no obvio sale de cruzar información de muchos productos y categorías, y de ver qué se deja pasar, y eso todavía no lo hace. |
| ¿Es mejor que no usar un LLM? | **No se puede saber.** Con 21 productos, ni el LLM ni los baselines dejan nada en test. Hacen falta cientos de productos, o miles. |
| ¿Quién propuso? | En esta corrida las propuestas las escribió Claude en el chat siguiendo el skill, no el programa con la API (no había clave). |

**Cómo se comparó:** los 21 productos se dividieron antes de leerlos en dev (11, para
ajustar) y test (10). Las propuestas del LLM y las de dos baselines sin LLM pasan por las
mismas pruebas. **B1** propone mejorar el producto por su queja más frecuente; **B2** propone
el repuesto cuando 2 o más preguntas lo piden (se escribió después de ver dev). Oportunidades
que pasan o quedan condicionales: en dev, LLM 1, B1 0, B2 1; en test, 0 en los tres. Test se
corrió dos veces: la segunda, después de agregar C5 (ver `BITACORA.md`).

**Para poder decir que sí sirve falta:**
1. **Escala:** cientos o miles de productos de muchas categorías. El cuello de botella es la
   recolección en el navegador; el paso del LLM cuesta ~USD 0,01 por producto.
2. **Divergencia de verdad:** que el LLM vea el conjunto (qué se elige y qué se deja pasar en
   cada búsqueda, y la misma necesidad en productos de otras categorías), no un producto aislado.
3. Que proponga el programa con la API (workflow `llm`), no el chat.
4. Un baseline humano: que alguien del grupo proponga con los mismos datos, y juzgar a ciegas
   las propuestas mezcladas (¿no obvia? ¿accionable?).

## Un ejemplo: cómo se mata el humo

En la búsqueda "tabla de cortar acero inoxidable", las dos tablas más elegidas venden **más de
1.000 unidades cada una**. Sus compradores dicen que las eligieron por higiene, pero 21 textos
se quejan de que **rayan y desafilan los cuchillos**. El LLM propone traer una tabla **doble
faz** (acero de un lado, polipropileno o bambú del otro). El programa prueba sus supuestos:

- ¿La necesidad es real? 21 textos, la mayoría como queja. **Pasa.**
- ¿Nadie la atiende? De 18 publicaciones parecidas, solo una vendió más de 100. **Pasa.**
- ¿Si se ofrece, la gente la elige? Hay 6 tablas doble faz con stock local y a precio
  comparable (~$32.000). Entre todas vendieron +125; la de una cara, +1.000. **La gente tuvo la
  alternativa enfrente y la dejó pasar: es humo. Se descarta.**

Sin la última prueba, el programa la habría recomendado con 79% de margen.

## Cómo funciona

```
voto con los pies ─────┐
(qué se elige y qué    │
 se deja pasar)        ├─► LLM propone ──► el programa prueba los supuestos ──► OPORTUNIDADES.md
voto con las manos ────┘   (divergente)     críticos y mata el humo (convergente)
(opiniones, preguntas)
```

| Etapa | Supuesto crítico que pone a prueba | El dato que lo tira abajo | Quién |
|---|---|---|---|
| Datos | — | Los 1 o 2 productos más elegidos de cada búsqueda, con opiniones y preguntas de indecisos | Captura desde el navegador |
| Filtro | — | Todas las preguntas + las opiniones más informativas (como Timoshenko y Hauser, 2019) | Código |
| Divergente A | — | Por producto: lee qué se eligió y qué se dejó pasar en su búsqueda, y las voces; devuelve señales (quejas, faltantes, deseos, usos raros) citando textos | **LLM** (`skills/leer_voces`) |
| Divergente B | — | Entre todos los productos: propone qué traer conectando señales de al menos 2 productos distintos (lo no obvio sale de cruzar) | **LLM** (`skills/cruzar_senales`) |
| Guardrail | Lo que dice el LLM está en los textos | Cita un texto que no existe, un fragmento que no está, o un solo texto (se le devuelve el error una vez) | Código |
| C1 dolor | El dolor que dice aliviar existe y está mal resuelto | Otro modelo, que no sabe qué se propone, no encuentra a quienes lo tienen sin resolver más seguido que en gente al azar (Fisher con Benjamini-Hochberg), o los encuentra en un solo producto | **LLM que mide** (`skills/medir_dolor`) + código que decide |
| C3 demanda | Hay gente eligiendo el producto de origen | Vende menos de +500 | Código |
| C4 hueco | Nadie la atiende todavía | 3 o más equivalentes ya venden +100 | Código + captura |
| C5 la eligen | Si se ofrece, la gente la elige | Las alternativas con stock local y precio no atípico venden significativamente menos (Mann-Whitney, 5%) que lo que la misma gente compra en su búsqueda de origen | Código + captura |
| C6 margen | Deja plata al precio que la gente paga | Ganancia neta (después de comisión, impuestos, envío, publicidad y devoluciones) menor que la del comercio minorista (5,19%, Damodaran); si alcanza solo con un FOB más bajo, queda condicional | Código |
| Confianza | — | A lo que sobrevive le muestra cada evidencia con su incertidumbre (dolor con intervalo de Wilson, ventas de equivalentes, margen de pesimista a optimista) y los riesgos definidos (`harness/confianza.py`) | Código |

**Cómo se eligió el prompt del paso B:** no a ojo. Se arman 25 variantes que combinan
decisiones de diseño sacadas de la literatura sobre generación de hipótesis (antecedente más
inspiraciones lejanas, explicación rival, razonamiento de detective, re-preguntar "otra
distinta", evitar lo obvio, rol). Se prueban todas sobre los mismos productos de desarrollo
(`harness/explorar_prompts.py`): cuántas propuestas pasan el guardrail y C1 a C3, cuántas son
distintas y cuántas no son obvias según un juez auxiliar. La mejor se optimiza al estilo GEPA
(`harness/optimizar_prompt.py`): el modelo lee por qué falló cada propuesta, reescribe las
instrucciones, y la versión nueva se queda solo si mejora.

**Por qué un LLM:** lo valioso está en texto desordenado ("¿venden los discos de repuesto?",
"se raya pero la prefiero a la de madera"). Contar palabras da "filo", "precio", "hola".
Proponer *qué traer* requiere leer.

**Por qué no se lo cree:** el LLM no puede citar un texto que no existe, el dolor lo mide otro
modelo que no sabe qué se propuso, y cada supuesto se contrasta con lo que la gente hizo. Cada propuesta
descartada queda registrada con el motivo.

## Correrlo

```bash
git clone https://github.com/codewithpatelo/faltante && cd faltante
python3 -m venv .venv && source .venv/bin/activate
make setup     # instala dependencias
make todo      # tests + el embudo en dev y test sobre los datos guardados (sin internet ni claves)
```

| Comando | Qué hace |
|---|---|
| `make serendipia` | Prueba las propuestas del LLM y de los dos baselines, en dev y en test |
| `make serendipia-api` | Lo mismo con el paso del LLM hecho por la API (necesita `DEEPSEEK_API_KEY`) |

**Costo:** ~USD 0,003 por producto con DeepSeek Flash (estimado; `CONSIGNA.md`): 1.000
productos, ~USD 3. La recolección en el navegador lleva ~1 minuto por producto.

Sin compartir claves: `DEEPSEEK_API_KEY` está cargada como secreto del repo (Actions). Se
corre el workflow **llm** desde la pestaña Actions eligiendo la tarea (serendipia, explorar u
optimizar) y la partición; los resultados quedan como archivo de la corrida
(`gh run download <id>`).

## Datos

| Qué | Volumen | Dónde |
|---|---|---|
| Productos ancla (los 1 o 2 que más venden en cada búsqueda) | 21, en 12 búsquedas de Cocina, Hogar y Bazar | `data/voces/productos_2026-11-05.json` |
| Opiniones de compradores | 2.647 | Panel "Mostrar todas las opiniones" de cada publicación |
| Preguntas de indecisos con su respuesta | 334 | Página de preguntas de cada publicación |
| Búsquedas para C4 | 30 | `data/capturas/captura_ml_serendipia_*.json` (`scripts/captura_ml.js`) |
| Precios de origen | 9 productos | Catálogo de Alibaba, con el ID de cada publicación: `data/serendipia/fob_2026-11-05.json` |
| Aranceles, flete, comisiones y envío | — | Con fuente en `harness/costo_puesto.py` y `harness/umbrales.py` |

Opiniones y preguntas juntas: `data/voces/corpus_2026-11-05.json`. Se leen desde un
navegador con sesión iniciada porque la API de búsqueda de Mercado Libre está cerrada aun
con token válido.

## Mapa

Un archivo por etapa, en el orden en que corren:

| Archivo | Qué hace |
|---|---|
| `harness/voces.py` | Carga los productos y sus textos, les pone ID (`o12`, `p3`) y elige los que lee el LLM |
| `harness/divergente.py` | Los dos pasos del LLM (DeepSeek): A, señales por producto (`skills/leer_voces`); B, oportunidades que cruzan productos (`skills/cruzar_senales`); reintenta si el guardrail rechaza algo |
| `harness/espacio_de_prompts.py` | Las 25 variantes del prompt del paso B, como combinación de decisiones de diseño |
| `harness/explorar_prompts.py` · `harness/optimizar_prompt.py` | Comparan las 25 variantes y optimizan la mejor (juez auxiliar: `skills/juzgar_obviedad`) |
| `harness/baselines.py` | B1 y B2: proponer sin LLM, para comparar |
| `harness/embudo.py` | **La lista de supuestos críticos**, en orden, cada uno con el dato que lo refuta; y cómo se recorre |
| `harness/chequeos.py` | Cómo se prueba cada supuesto (guardrail, C1 y C3 a C6) |
| `harness/confianza.py` | La evidencia y los riesgos de lo que sobrevive |
| `harness/umbrales.py` | Todos los umbrales, con qué mide cada uno |
| `harness/costo_puesto.py` | Costo puesto en Argentina e ingreso neto vendiendo en Mercado Libre |
| `harness/correr.py` | Junta las propuestas, las pasa por el embudo y escribe el resultado |
| `scripts/captura_ml.js` | Captura de búsquedas desde el navegador (para C4) |
| `scripts/voces_ml.js` | Junta opiniones y preguntas desde el navegador, en dos pasadas |
| `scripts/elegir_anclas.py` · `scripts/unir_escala.py` | Eligen los productos ancla de cada búsqueda y arman `data/escala/corpus_<fecha>.json` |
| `scripts/unir_voces.py` | Armó el primer corpus (`data/voces/corpus_2026-11-05.json`, 21 productos) |
| `tests/test_embudo.py` | Lo que tiene que cumplir cada etapa |
| `data/serendipia/` | Propuestas del LLM, precios de proveedor y el recorrido de cada propuesta |
| `OPORTUNIDADES.md` | El resultado, para leer: qué pasó las pruebas, qué se descartó y por qué |
| `CONSIGNA.md` · `DECISIONES.md` | Requisitos del TP y dónde se cumplen · qué elegimos y por qué |
| `BITACORA.md` | Cómo llegamos acá, incluidos los enfoques descartados (su código está en el historial de git; sus datos, en el resto de `data/`) |

## Glosario

- **Voto con los pies:** lo que la gente hace: entre las opciones que tiene, qué elige y qué deja pasar.
- **Voto con las manos:** lo que la gente dice: por qué eligió y qué le faltó (opiniones y preguntas).
- **Divergente / convergente:** primero abrir hipótesis (LLM), después intentar refutarlas (programa).
- **Abducción:** proponer lo que haría que lo observado tenga sentido.
- **Equivalente:** una publicación que es el mismo producto o un reemplazo directo.
- **Costo puesto:** precio en origen + flete + aranceles, con el producto en Argentina.
- **FOB:** precio del proveedor en el puerto de origen.
- **Guardrail:** regla en código que el LLM no puede saltear.

## Limitaciones

- El LLM ve el producto elegido y lo que dicen sus compradores e indecisos, pero no las
  alternativas que la gente dejó pasar en esa búsqueda: esas entran recién en C4 y C5.
- El paso del LLM en dev y test lo hizo Claude en el chat siguiendo el skill, porque no
  había clave de API en el entorno; `make serendipia-api` lo repite con el modelo.
- Algunas preguntas de test se vieron durante la recolección. Después de correr test no se
  cambió nada.
- C4 y C5 deciden equivalencias por palabras del título y se equivocan: en test contaron
  cepillos a vapor *para mascotas* como repuestos de limpiadora.
- Los costos usan precios de catálogo y tarifas publicadas, no cotizaciones reales.
- "+N vendidos" es un piso del contador de Mercado Libre, no las ventas exactas.
- El código que recolectó opiniones y preguntas se corrió en la consola del navegador y
  todavía no está guardado en `scripts/`.
