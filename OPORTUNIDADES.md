# Oportunidades de importación: lo que sobrevivió al embudo (05/11/2026)

Salida de `make serendipia`. Entrada: 21 productos que se venden mucho en Mercado Libre, con
sus opiniones (2.647) y las preguntas de los indecisos (~330). El LLM lee y propone; el
programa intenta matar cada propuesta con datos. Acá quedan las que no pudo matar.

## Sobrevive (test)

### Tabla de picar doble faz: una cara de acero, la otra de polipropileno o bambú

| | |
|---|---|
| **De dónde sale** | Dos tablas de acero que venden +1.000 cada una (P12 y P13). La gente las compra por higiene ("chau tablas de madera o plástico") pero se queja de que **se rayan y desafilan los cuchillos**: 11 y 10 textos lo mencionan, la mayoría como queja. |
| **La abducción** | Quieren higiene *y* cuidar el filo. Una tabla con dos caras resuelve las dos: acero para la carne cruda, la otra cara para cortar. |
| **C4: ¿alguien ya la vende?** | 18 publicaciones equivalentes en la búsqueda; **solo 1 llega a +100 vendidos** (importada, $14.184). Las tablas de una sola cara venden +1.000 cada una. El concepto existe pero nadie lo atiende con volumen. |
| **C5: ¿cuánto deja?** | Al precio de lo que se vendió ($32.800): costo puesto ~$10.700, **margen base 79%** sobre costo (pesimista 23%). Deja 30% mientras el proveedor cotice ≤ USD 6,14 (catálogo: USD 3,20 a EUR 6,05). |
| **Riesgo** | La demanda del producto *nuevo* es indirecta: las equivalentes vendieron poco (+25 a +100). Puede ser que nadie la atienda bien… o que no la quiera tanta gente. |
| **Experimento siguiente** | Pedir 3 cotizaciones (36x25 cm, acero 304 + PP); publicar 30 unidades a $32.800 contra una tabla de una cara al mismo precio y medir ventas en 30 días. |

## Condicional (dev)

### Disco de repuesto para afiladores rodantes, suelto

| | |
|---|---|
| **De dónde sale** | Dos afiladores que venden +1.000 cada uno (P01 y P02). En las preguntas piden **discos de repuesto** y el vendedor no los tiene ("Venden discos de respuesto para el afilador Refilo?", "se consigue repuestos cuando se gastan las piedras?"). |
| **C4** | En la búsqueda de discos, solo un disco suelto para afilador rodante vende (+100, $17.416). El resto son afiladores completos o discos de motosierra. |
| **C5** | A $17.416 el margen base es 27%: **no llega al 30%** con el FOB de catálogo (USD 3,30). Sobrevive si el proveedor cotiza **≤ USD 3,21** (catálogo: USD 2,60-3,30). |
| **Experimento siguiente** | Cotizar discos compatibles con los afiladores de imán más vendidos; si alguna cotización baja de USD 3,21, publicar 50 unidades. |

## Lo que murió y por qué (las más interesantes)

| Propuesta | Murió en | Motivo |
|---|---|---|
| Espumador de leche (lo piden los indecisos de una minipimer, 10 textos) | C4 | 12 espumadores de mano ya venden +100, varios +1.000 a ~$10.000. La necesidad es real y ya está atendida. |
| Repuestos de minipimer (vaso picador, pie) | C4 | 7 repuestos ya venden +100 (Liliana, Philips, Black+Decker). |
| Organizador de ropa con estructura metálica | C4 | 7 ya venden +100, dos con +5.000. |
| Set de recipientes de acero herméticos de buena calidad | C4 | 5 equivalentes venden +100, de $13.600 a $84.900. |
| Filtros de repuesto para aspiradoras de mano | C4 | 3 kits ya venden +100. |
| Vasos térmicos por caja para empresas (preguntan 22, 28, 36 unidades con logo) | C4 | 16 vasos de 900 ml ya venden +100. |
| Adhesivos de repuesto para estantes de ducha | C5 | Lo que se vende cuesta ~$6.000; con el costo fijo de envío de Mercado Libre (~$2.500) no deja nada. Haría falta FOB ≤ USD 0,18 por pack. |
| Cepillos de repuesto para limpiadoras a vapor | C5 | **Muerte falsa**: el criterio de equivalencia contó cepillos a vapor para mascotas ($4.999) como equivalentes. Ningún cepillo de repuesto real vende. Ver limitaciones. |
| Lonchera 12/24 V para camioneros | guardrail | El LLM citó dos veces el mismo texto: una sola pregunta no es señal. |
| Bowls con base antideslizante | C1 | Solo 2 textos lo mencionan. |

## LLM contra baselines (mismo embudo)

| | propuestas | sobreviven | condicionales | distintas |
|---|---|---|---|---|
| **dev, LLM** | 8 | 0 | 2 | 1 (discos) |
| dev, B1 queja más frecuente | 11 | 0 | 0 | 0 |
| dev, B2 regla "piden repuesto" | 4 | 0 | 2 | 1 (discos) |
| **test, LLM** | 10 | 2 | 0 | **1 (tabla doble faz)** |
| test, B1 queja más frecuente | 10 | 0 | 0 | 0 |
| test, B2 regla "piden repuesto" | 1 | 0 | 0 | 0 |

- **B1** cuenta la palabra más repetida en las quejas ("filo", "precio", "hola") y propone
  "una versión que lo resuelva". Casi siempre muere en C4: mejorar el producto ancla es
  competir en la misma búsqueda, que ya está llena.
- **B2** es fuerte cuando lo que falta es un repuesto (encontró los discos en dev), pero en
  test no encontró nada: la tabla doble faz no es un repuesto, es una **combinación** de dos
  cosas que la gente quiere a la vez. Eso es lo que el LLM agrega.
- Son 21 productos: alcanza para mostrar cómo funciona el embudo, no para afirmar una
  diferencia estadística.

Detalle por propuesta: `data/serendipia/embudo_dev.json` y `data/serendipia/embudo_test.json`.
