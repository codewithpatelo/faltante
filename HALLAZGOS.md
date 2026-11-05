# Hallazgos: fichas de decisión para un importador (05/11/2026)

Cada ficha responde "¿lo traigo?", con el motivo, la evidencia y lo que falta para estar
seguros. Las marcadas como **no obvias** son las que no se ven mirando solo precio y
ventas: salieron de cruzar los votos (qué se compra) con lo que dicen los compradores.

| Producto | ¿Traerlo? | Por qué | Confianza |
|---|---|---|---|
| Set de recipientes herméticos de acero | **Sí: la más robusta** | +5.000 por Compra Internacional a $14.063; sets locales que venden, ~3,4x. Costo puesto ~$5.700; vendido a $25.000 con stock local deja **73% sobre costo** (27% en un lote chico de 200). Riesgo: trámite de envases en contacto con alimentos de origen importado (INAL/ANMAT) | media |
| Afilador de cuchillos rodante | **Sí, si FOB ≤ USD 6** | +1.000 por Compra Internacional a $21.838; locales que venden, $43k a $135k. Costo puesto ~$11.400; a $35.000 deja **44%** (15% en lote de 200), a $49.800 deja 129%. Con FOB USD 12 y arancel 35% pierde | media |
| Contenedor con colador para heladera | Abierto | +1.000 por Compra Internacional a $17.191; hay 3 locales al mismo precio y **ninguno vende**: ni precio ni espera lo explican | baja |
| Tostadora de ranura del top de Amazon (Bella) | No | Cuesta 2,3 a 8 veces lo que se vende; las de ranura locales a $34k-60k venden +10.000 | alta |
| Carlitero / tostador abierto de calor superior | **No importar, no obvia** | Parece un hueco: +5.000 a $160k-280k, 2-3 fabricantes locales, comprado para panes que no entran en ranura ("no poder meter un pan francés… acá tenés la solución") y por negocios chicos. Pero la salamandra eléctrica importada más barata (USD 167) queda puesta en ~$450.000: el fabricante local gana | alta |
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

## Costo puesto: cómo se calculó

`python -m harness.costo_puesto` (resultado en `data/cross_border/costo_puesto_2026-11-05.json`).
Para un importador Responsable Inscripto: FOB (Alibaba, rango por proveedor) + logística
consolidada puerta a puerta USD 450/m³ (mínimo 1 m³) + derecho de importación (7323.93: 35%;
8516.72: 20%; afilador: 18% de arancel común, probado hasta 35%) + tasa de estadística 3%. IVA
y percepciones son crédito fiscal (caja, no costo). Venta en Mercado Libre: precio con IVA,
comisión 14%, envío a cargo del vendedor, IIBB 3,5%. Dólar $1.570. Tres escenarios
(optimista, base, pesimista) y lote lleno contra lote de prueba de 200 unidades.

Capital para un lote lleno (1 m³): herméticos ~$2,3 millones (399 sets); afilador ~$9 millones (788 unidades).

## Lo que falta para pasar de "abierto" a "sí"

1. Cotización real de un proveedor y de un despachante (los números de arriba son de referencia pública).
2. Confirmar el trámite de envases en contacto con alimentos para los herméticos y el arancel exacto del afilador.
3. Etiquetas humanas de equivalencia (`data/evaluacion/planilla_equivalencia.csv`).
4. Mostrarle las fichas a uno o dos importadores y preguntarles si traerían algo.

Evidencia: `data/cross_border/`, `data/voces/`, `data/diagnostico/`, `data/divergente/`.
