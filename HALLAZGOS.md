# Hallazgos: fichas de decisión para un importador (05/11/2026)

Cada ficha responde "¿lo traigo?", con el motivo, la evidencia y lo que falta para estar
seguros. Las marcadas como **no obvias** son las que no se ven mirando solo precio y
ventas: salieron de cruzar los votos (qué se compra) con lo que dicen los compradores.

| Producto | ¿Traerlo? | Por qué | Confianza |
|---|---|---|---|
| Afilador de cuchillos rodante | **Sí, a validar costo** | +1.000 vendidos por Compra Internacional a $21.838; los locales equivalentes que venden cuestan $43k a $135k (2,3x de mediana). Demanda de cocina general, no de nicho | media |
| Set de recipientes herméticos de acero | Sí, con cautela | +5.000 por Compra Internacional a $14.063; sets locales que venden, ~3,4x. Ojo: hay uno local de 6 piezas a $11k con +100 | media-baja |
| Contenedor con colador para heladera | Abierto | +1.000 por Compra Internacional a $17.191; hay 3 locales al mismo precio y **ninguno vende**: ni precio ni espera lo explican | baja |
| Tostadora de ranura del top de Amazon (Bella) | No | Cuesta 2,3 a 8 veces lo que se vende; las de ranura locales a $34k-60k venden +10.000 | alta |
| Carlitero / tostador abierto de calor superior | **Abierto, no obvia** | Segundo mercado que el top de Amazon no tiene: +5.000 a $160k-280k, 2-3 fabricantes locales; se compra para panes que no entran en ranura ("no poder meter un pan francés… acá tenés la solución") y por negocios chicos (15 de 151 opiniones) | media |
| Olla de cocción lenta (Crock-Pot) | No, **no obvia** | La función se compra dentro de ollas multifunción o a presión (+1.000 c/u), no como aparato dedicado; además los modelos de EE.UU. son de 120 V | media |
| Lonchera eléctrica | No | La necesidad existe (≈4.500 ventas visibles) pero la atienden muchos vendedores locales a ~$48k | alta |
| Aspiradora-sopladora de mano | No | Premium local que vende (+5.000 a $157k); se compra para el auto (25 de 175 opiniones), no para el asado (1 de 175) | alta |

## Qué aprendimos del método

- **Partir del top de Amazon encuentra poco**: casi todo es más caro o ya se vende.
  Partir de lo que se compra por Compra Internacional encuentra demanda probada.
- **El LLM cambia el resultado donde importa**: decidiendo qué es equivalente, bajan de
  10 a 3 las oportunidades; las otras 7 eran falsas (tamaños y gamas distintos).
- **Las hipótesis situadas hay que refutarlas**: dos de las nuestras ("sopladora para el
  asado", "afilador para el asado") cayeron con las opiniones (1 de 175, 0 de 111), y una
  tercera ("el pan de acá no entra en ranura, por eso no vende la tostadora") cayó con los
  datos de ventas. Lo que quedó en pie es más chico pero sostenido.

## Lo que falta para pasar de "abierto" a "sí"

1. Costo puesto en Argentina (origen + flete + impuestos) de las 3 candidatas.
2. Etiquetas humanas de equivalencia (`data/evaluacion/planilla_equivalencia.csv`).
3. Mostrarle las fichas a uno o dos importadores y preguntarles si traerían algo.

Evidencia: `data/cross_border/`, `data/voces/`, `data/diagnostico/`, `data/divergente/`.
