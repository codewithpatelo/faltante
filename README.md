# Faltante

TP de IA Agéntica (UBA, 2026). Tomamos productos que se venden mucho afuera (top de Amazon
en Cocina) y nos preguntamos **por qué no se venden en Mercado Libre**. Cuatro explicaciones
compiten: **precio** (cuesta mucho más que lo que la gente compra), **espera** (la gente no
quiere esperar el envío de afuera), **preferencia** (hay alternativas que gustan más) y
**falta de demanda**. El sistema corre las cuatro y se queda con la que sostienen los datos.

Usamos **votos con los pies**: lo que la gente compra ("+N vendidos" en cada publicación),
no lo que dice que compraría.

## Para el equipo: qué hacer ahora (05/11/2026)

1. `make setup && make todo`: tiene que dar 30 tests en verde y correr el diagnóstico y el piloto divergente.
2. **Etiquetar 94 equivalencias y juzgar 12 hipótesis a ciegas** (25 minutos): `data/evaluacion/COMO_JUZGAR.md`. Son los primeros
   juicios humanos: con ellos medimos LLM contra baseline y después calibramos un LLM juez.
3. Leer `BITACORA.md` de abajo hacia arriba: ahí está el relato del desarrollo que pide la exposición.
4. **Correr el LLM sin compartir claves:** cargar `ANTHROPIC_API_KEY` como secreto del repo y
   lanzar el workflow `llm` desde Actions (≈ USD 0,07). Detalle en `CONSIGNA.md`.
5. **`CONSIGNA.md`**: cada requisito de la consigna, dónde se verifica y qué falta, con el reparto
   de tareas propuesto.

## Resultado en una página: [`HALLAZGOS.md`](HALLAZGOS.md)

Fichas de decisión para un importador ("¿lo traigo?"), con motivo, evidencia y confianza.

## Hallazgo principal: demanda probada por Compra Internacional (05/11/2026)

El voto con los pies más fuerte a favor de importar es comprar por **Compra Internacional**:
la persona paga y además espera semanas. Tomamos los 74 productos internacionales con +100
vendidos o más en Cocina, Hogar, Bazar y Organización, y para 15 buscamos si hay un
equivalente con stock local (`make cross-border`). Quién decide qué es "equivalente" cambia
todo:

| Cómo se decide la equivalencia | Oportunidades de 15 |
|---|---|
| Baseline sin LLM (dos palabras del título) | 10 |
| Regla de palabras escrita por el LLM | 8 |
| **LLM juzgando publicación por publicación** (tamaño, gama) | **3** |

Las reglas confunden una tabla de 25x15 con una de 60x30, o un set básico de bowls con
ensaladeras premium. Las 3 que quedan, con demanda probada:
- **Afilador de cuchillos rodante**: +1.000 vendidos por Compra Internacional a $21.800; los
  locales equivalentes que venden cuestan ~2,3 veces más ($43k a $78k).
- **Set de recipientes herméticos de acero**: +5.000 a $14.000; los sets locales que venden,
  ~3,4 veces más (hay uno local barato con +100: atención).
- **Contenedor con colador para heladera**: +1.000 a $17.000; hay 3 locales al mismo precio y
  ninguno vende (no lo explica la espera: queda abierto).

Esto todavía es el juicio de un LLM. La hipótesis medible es que ese juicio acierta más que
las reglas: lo verifica el grupo etiquetando `data/evaluacion/planilla_equivalencia.csv`
(`make equivalencia` da precisión, recall y F1 de cada método). Hay 15 productos de **test**
fijados sin mirar (`data/cross_border/particion.json`).

## Qué encontramos antes (23 productos de Amazon, fotos del 29/10 y del 05/11/2026)

| Conclusión | Productos | Qué significa |
|---|---|---|
| No compite en precio | 16 | cuesta entre 2 y 8 veces lo que se vende en su búsqueda |
| Ya se vende acá | 4 | hay stock local con ventas (Owala FreeSip, Stanley Quencher, KitchenAid) |
| Candidato a probar | 2 | precio parecido y nadie lo vende con stock local (mixer Turelar, Owala SmoothSip) |
| Sin demanda | 1 | nadie compra nada en la búsqueda (YETI Rambler) |

Las dos fotos, tomadas con una semana de diferencia, dan **las mismas 23 conclusiones**.
De las publicaciones internacionales de estos productos, **ninguna muestra ventas**: en los
4 productos que están en los dos canales, la gente compra el de stock local aunque el
internacional cueste igual o menos.

## Etapa divergente (piloto, 05/11/2026)

El diagnóstico anterior parte de un producto de Amazon y pregunta por qué no se vende. Eso
es solo la mitad convergente. La etapa divergente **lee los votos**: en cada búsqueda, qué
eligió la gente y qué dejó pasar (formato, marca, precio, origen, palabras), y abduce
hipótesis de necesidad que después se intentan refutar.

- `skills/leer_votos/SKILL.md`: el procedimiento que sigue el LLM.
- `harness/votos.py`: la vista ganadoras/perdedoras, el **baseline** sin LLM (términos que
  distinguen lo que vende) y el **guardrail** de citas (cada hipótesis cita publicaciones
  con un fragmento literal y el voto tiene que coincidir con las ventas).
- `data/divergente/`: partición fija dev/test, 6 hipótesis piloto y la convergencia de dos.
- `make divergente` reproduce el piloto.

Resultado: 6 hipótesis sobre 6 búsquedas de desarrollo. De las tres que intentamos refutar:
lenguaje del título **cae**; voltaje 220 V **sigue abierta**; lonchera que calienta: **la necesidad
se confirma pero ya está atendida** por vendedores locales (no es oportunidad de importación).
`harness/divergente.py` es la versión con API (proponer → validar en código → reintentar una vez).

## Correrlo (sin red ni claves)

```bash
git clone https://github.com/codewithpatelo/faltante && cd faltante
python3 -m venv .venv && source .venv/bin/activate
make setup        # instala dependencias
make todo         # tests + demo del harness + diagnóstico sobre la foto más reciente
```

Por separado:

```bash
make test         # 30 tests: guardrails, chequeos, emparejamiento, citas, reintento
make diagnostico  # cuatro chequeos sobre la foto más reciente de data/diagnostico/
make demo         # políticas fija y heurística sobre datos sintéticos (prueban el mecanismo)
make agente       # agente ReAct con LLM (requiere ANTHROPIC_API_KEY)
```

Con Docker: `docker build -t faltante . && docker run --rm faltante`

## Refrescar los datos de Mercado Libre

La API de búsqueda de Mercado Libre está cerrada: devuelve **403 sin token** (desde la nube y
desde una conexión hogareña) y **403 con token válido** de una app no certificada
("At least one policy returned UNAUTHORIZED"; probado el 05/11/2026, ver
`data/prueba_datos/api_con_token_2026-11-05.json`). La web bloquea scripts comunes. Lo que sí
funciona es leer el listado desde tu navegador con sesión iniciada:

1. Abrí `https://listado.mercadolibre.com.ar/termo` con tu sesión de Mercado Libre.
2. Abrí la consola (F12 → Consola), pegá entero `scripts/captura_ml.js` y Enter.
   Tarda unos 8 minutos y descarga `captura_ml_<fecha>.json`. No toca cookies ni datos de tu cuenta.
3. Copiá el archivo a `data/capturas/` y corré:

```bash
make foto CAPTURA=data/capturas/captura_ml_<fecha>.json   # marca producto / sustituto / accesorio
make diagnostico                                           # usa la foto nueva
```

`make prueba-api` repite la prueba de la API con una app propia (pide Client ID y Secret Key
sin mostrarlos y no los guarda), por si Mercado Libre la abre o la app se certifica.

## Cómo está armado

![Arquitectura](docs/arquitectura.svg)

```
productos con demanda afuera
   │
   ▼
POLÍTICA ─── decide qué chequear ──►  MOTOR ─── guardrails, caché, traza
(fija | heurística | diagnóstico | LLM)  │
                                         ▼
                                  SKILLS ──► ADAPTADORES (foto de ML | API de ML | sintéticos)
```

- **`harness/motor.py`**: ejecuta lo que la política pide y hace cumplir las reglas; no decide.
  Operaciones: `proponer_hipotesis`, `verificar`, `dar_veredicto`, `leer_skill`.
- **`harness/diagnostico.py`**: los cuatro chequeos. Los umbrales están arriba del archivo,
  a la vista, porque son decisiones discutibles.
- **`harness/agente.py`**: loop ReAct sobre la API de Anthropic, sin framework.
- **`harness/politicas.py`**: fija, heurística y diagnóstico (los baselines contra los que
  se compara el agente).
- **`skills/*/SKILL.md`**: una por verificación: qué pregunta responde, cuándo usarla, cómo
  leer el resultado.
- **`adapters/`**: de dónde salen los datos. Cambiar de fuente no toca el harness.
- **`scripts/`**: captura desde el navegador, emparejamiento por reglas, prueba de la API.

### Guardrails (en código)

- No se puede confirmar ni descartar sin al menos una evidencia **propia, exitosa y que haya
  tocado datos**. Si no se pudo verificar, el veredicto es `insuficiente`.
- Tope de skills por hipótesis y de pasos totales.
- No se puede terminar con productos sin veredicto.
- Todo rechazo vuelve a la política como error y queda en la traza.

## Dónde está el LLM

En **emparejar**: decidir si cada publicación de Mercado Libre es el producto de Amazon, un
sustituto o un accesorio. La búsqueda de Mercado Libre mezcla todo, y una regla simple
("menciona la marca") acertó 4 de 15 en la prueba. Hoy el criterio por producto
(`data/diagnostico/criterios.json`) lo escribió el LLM en el chat y se aplica con reglas
(`scripts/emparejar.py`). Pendiente: hacer el emparejamiento con el LLM publicación por
publicación y compararlo contra estas reglas.

## Limitaciones que declaramos

- Primera página de cada búsqueda, 23 productos, una categoría.
- "+N vendidos" es un piso del contador, no ventas reales.
- El criterio de emparejamiento tiene errores conocidos (ver `BITACORA.md`).
- No sabemos si el precio internacional incluye impuestos de importación.

## Archivos para leer primero

- `BITACORA.md`: qué probamos, qué esperábamos, qué pasó, qué decidimos, en orden.
- `DECISIONES.md`: por qué el diseño es como es.
- `data/diagnostico/resultado_<fecha>.json`: cada producto con los números de cada chequeo.
