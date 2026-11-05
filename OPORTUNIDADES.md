# Oportunidades de importación (05/11/2026)

Qué sobrevivió, qué se descartó y por qué. Entrada: 21 productos, los más elegidos de sus
búsquedas en Mercado Libre, con 2.647 opiniones y 334 preguntas de indecisos. El LLM propuso
14 oportunidades distintas; el programa probó los supuestos críticos de cada una (guardrail y
C1 a C6, ver README). Salida de `make serendipia`; el recorrido completo de cada propuesta,
con su confianza, está en `data/serendipia/embudo_dev.json` y `embudo_test.json`.

**Resumen:** ninguna sobrevive del todo; una queda condicional, con confianza baja. Las
propuestas fueron triviales y la muestra es insignificante (ver "¿Sirve?" en el README).

## Condicional

### Disco de repuesto para afiladores rodantes, suelto (dev) · confianza baja

| | |
|---|---|
| **De dónde sale** | Los dos afiladores más elegidos de su búsqueda venden +1.000 cada uno (P01 y P02). En las preguntas piden **discos de repuesto** y el vendedor no los tiene ("Venden discos de respuesto para el afilador Refilo?", "se consigue repuestos cuando se gastan las piedras?"). |
| **C4 y C5** | Solo hay un disco suelto para afilador rodante con stock local (+100, $17.416): nadie más lo ofrece, así que la gente no tuvo la opción de dejarlo pasar. |
| **C6** | A $17.416 el margen base es 27%: **no llega al 30%** con el FOB de catálogo (USD 3,30). Pasa si el proveedor cotiza **≤ USD 3,21** (catálogo: USD 2,60-3,30). |
| **Confianza baja (2 de 5)** | A favor: aparece en 2 productos y la mencionan 11 textos. En contra: el disco que existe vendió poco (+100), el precio sale de una sola publicación y en el escenario pesimista pierde plata. |
| **Próximo paso** | Cotizar discos compatibles con los afiladores de imán más vendidos; solo si alguna cotización baja de USD 3,21, publicar 50 unidades. |

## Lo que se descartó y por qué

| Propuesta | Supuesto refutado | El dato |
|---|---|---|
| Tabla de picar doble faz (pedían higiene y que no desafile) | C5: si se ofrece, la eligen | 6 tablas doble faz con stock local a ~$32.000 suman +125 ventas; la de una cara, +1.000. La gente la tuvo enfrente y la dejó pasar. |
| Adhesivos de repuesto para estantes de ducha | C5: si se ofrece, la eligen | 8 packs con stock local a precio comparable suman +125 ventas; los estantes, +10.000. |
| Cepillos de repuesto para limpiadoras a vapor | C5: si se ofrece, la eligen | **Error del programa**: contó cepillos a vapor para mascotas como alternativas. Ningún cepillo de repuesto real vende; la propuesta merecía otra prueba. |
| Espumador de leche (lo piden los indecisos de una minipimer, 10 textos) | C4: nadie la atiende | 12 espumadores de mano ya venden +100, varios +1.000 a ~$10.000. |
| Repuestos de minipimer (vaso picador, pie) | C4: nadie la atiende | 7 repuestos ya venden +100 (Liliana, Philips, Black+Decker). |
| Organizador de ropa con estructura metálica | C4: nadie la atiende | 7 ya venden +100, dos con +5.000. |
| Set de recipientes de acero herméticos de buena calidad | C4: nadie la atiende | 5 equivalentes venden +100, de $13.600 a $84.900. |
| Set de recipientes de acero del mismo tamaño para viandas | C4: nadie la atiende | 6 equivalentes venden +100. |
| Filtros de repuesto para aspiradoras de mano | C4: nadie la atiende | 3 kits ya venden +100. |
| Vasos térmicos por caja para empresas (preguntan 22, 28, 36 unidades con logo) | C4: nadie la atiende | 16 vasos de 900 ml ya venden +100. |
| Aspiradora de mano con función sopladora | C2: importa y está mal resuelta | Solo 3 textos la mencionan: importancia baja. |
| Bowls con base antideslizante | C1: no es un caso aislado | Solo 2 textos lo mencionan. |
| Lonchera 12/24 V para camioneros | Guardrail | El LLM citó dos veces el mismo texto: una sola pregunta no es señal. |

## LLM contra baselines (mismas pruebas)

| | propuestas | sobreviven | condicionales | distintas que sobreviven o quedan condicionales |
|---|---|---|---|---|
| dev, LLM | 8 | 0 | 2 | 1 (discos) |
| dev, B1 queja más frecuente | 11 | 0 | 0 | 0 |
| dev, B2 regla "piden repuesto" | 4 | 0 | 2 | 1 (repuesto de afilador) |
| test, LLM | 10 | 0 | 0 | 0 |
| test, B1 queja más frecuente | 10 | 0 | 0 | 0 |
| test, B2 regla "piden repuesto" | 1 | 0 | 0 | 0 |

Con 21 productos la comparación no dice nada: hacen falta cientos o miles.
