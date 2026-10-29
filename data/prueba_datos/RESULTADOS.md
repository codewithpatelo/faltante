# Prueba mínima de datos — resultados (29/10/2026)

Criterios en `CRITERIOS.md`, fijados antes de probar. Todo se pidió sin credenciales,
desde código, usando la API de Exa como lector web (un crawler de terceros).

## Qué respondió cada fuente

| Fuente | URL probada | Resultado |
|---|---|---|
| Búsqueda de Mercado Libre (web) | `listado.mercadolibre.com.ar/<producto>` | **403** en 3 de 3 intentos |
| Búsqueda de Mercado Libre (API) | `api.mercadolibre.com/sites/MLA/search` | **403** sin token |
| Más vendidos de Mercado Libre (web) | `mercadolibre.com.ar/mas-vendidos/<categoría>` | **2 de 4 categorías** respondieron; las otras 2, muro de login |
| Más vendidos de Mercado Libre (API `/highlights`) | documentado, top 20 por categoría | Requiere token. No probado |
| Compra Internacional de Mercado Libre | `mercadolibre.com.ar/importados/compra-internacional` | Responde, con productos y precios. Es una vidriera, no un ranking |
| Más vendidos de Tiendamia | `tiendamia.com/ar/mas-vendidos` | Responde **vacío**: el contenido se arma con JavaScript |
| Búsqueda de Tiendamia | `tiendamia.com/ar/search?amzs=<producto>` | **Responde** con productos de Amazon y precio en pesos |
| Búsqueda de Amazon EE.UU. | `amazon.com/s?k=<producto>` | **Responde** con precio y "compras del último mes" |
| Reddit | búsqueda JSON | No disponible |
| Índice de búsqueda web (Exa) sobre Mercado Libre | búsqueda por producto | Devuelve publicaciones sueltas: sirve para saber **si existe** oferta, no **cuánta** |

## Contra los criterios

| # | Criterio | Resultado | Por qué |
|---|---|---|---|
| T1 | 20+ productos reales de voto con los pies | **Parcial** | Los más vendidos de ML dan 19 productos por categoría con rango de ventas, pero fallan la mitad de las veces y no son compra afuera. El ranking de compra afuera (Tiendamia) no se puede leer sin navegador |
| T2 | Oferta local por producto | **Falla** | La búsqueda de Mercado Libre bloquea todo acceso sin token |
| T3 | Precio exterior | **Pasa** | Tiendamia y Amazon responden con producto y precio |
| T4 | Calidad en 10 productos | **No evaluable** | Sin T2 no se puede medir. Además, cualitativamente: buscar "cepillo lateral robot" en Tiendamia devuelve 15 productos para 15 modelos distintos. Resolver *el mismo* producto entre fuentes no es trivial |
| T5 | Automatizable sin humano | **Condicional** | T3 sí. T1 y T2 dependen de un token de Mercado Libre o de un navegador |

## Veredicto

**No-go para el diseño actual.** Depende de contar la oferta en Mercado Libre, y hoy no
podemos hacerlo. La prueba que lo decide es una sola: registrar una app en Mercado Libre
y repetir T2 con token, contra `/sites/MLA/search` y `/highlights`.

## Hallazgo que cambia la hipótesis

Mercado Libre ya vende por **Compra Internacional** los repuestos que la v3 suponía
faltantes: buscando repuestos de robots aspiradores aparecen publicaciones marcadas
"Compra internacional · Envío desde USA". El hueco de complementos que imaginábamos se
está cerrando solo, por el canal cross-border.

Lo que ese canal **no** cierra son sus propios límites: 5 envíos internacionales por año
por persona, 3 unidades iguales por compra y clave fiscal nivel 2 (según el blog oficial
de Mercado Libre). Un producto que la gente compra repetidamente por cross-border, sin
vendedor local, es candidato a que un importador lo traiga en volumen. Esa es una
hipótesis nueva, y también hay que probar que sus datos se consiguen.

## Confirmación independiente (Devin, 29/10/2026, otra máquina)

| Endpoint | HTTP | Respuesta |
|---|---|---|
| `GET /sites/MLA/search` sin token | 403 | `{"message":"forbidden","error":"forbidden","status":403}` |
| `GET /highlights/MLA/category/MLA1574` sin token | 401 | `{"error":"unauthorized","message":"unspecified_token"}` |

La diferencia importa: el ranking pide un token (401); la búsqueda dice "prohibido"
(403), lo que es compatible con que esté cerrada aun con token. Pendiente: repetir con
la app registrada.
