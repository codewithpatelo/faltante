# Bitácora

Una entrada por sesión: qué probamos, qué esperábamos, qué pasó, qué decidimos.

---

## 2026-09 — Descarte de la v2 (reseñas de comercios de barrio)

**Qué probamos:** razonar qué señal contiene "fui y no lo tenían" en reseñas de Google Maps.
**Qué esperábamos:** detectar productos ausentes del mercado argentino.
**Qué pasó:** quien va a un local de barrio espera que el producto exista. La señal es
casi siempre falta de stock, no ausencia de mercado.
**Qué decidimos:** pasar a señales donde la persona ya tiene el producto (complementos) y,
después, a votos con los pies.

## 2026-10-29 — Prueba de acceso a fuentes de datos

**Qué probamos:** pedir datos sin credenciales desde el entorno de desarrollo en la nube.

| Fuente | Resultado |
|---|---|
| API de Mercado Libre `/sites/MLA/search` | **403** sin token |
| Listado web de Mercado Libre | muro de login para tráfico no autenticado |
| Tiendamia, Google Trends, Reddit (desde el shell) | bloqueados por la política de red del entorno |
| Rankings courier publicados en prensa | accesibles vía búsqueda web |

**Qué esperábamos:** que la API pública de Mercado Libre alcanzara para `contar_oferta`.
**Qué pasó:** no alcanza. Necesitamos una app registrada y un access token.
**Qué decidimos:** separar las fuentes en adaptadores con un contrato común, y construir y
testear el harness sobre datos sintéticos rotulados mientras se resuelve el acceso real.
El adaptador de Mercado Libre falla de forma explícita (`sin_credenciales`) y el sistema
devuelve `insuficiente` en lugar de inventar números: verificado corriendo la política
heurística contra la fuente en vivo.

## 2026-10-29 — Primer harness corriendo

**Qué probamos:** tres políticas sobre 8 pistas sintéticas con verdad etiquetada.
**Qué pasó:** fija y heurística aciertan 6 de 8; la heurística usa la mitad de llamadas a la
fuente (20 contra 40). Las dos fallan en las mismas pistas: P1 (nombre en inglés,
"nut milk maker") y P6 (un adaptador casero que apunta al consumible que falta). Son
exactamente los casos que requieren interpretación semántica.
**Qué decidimos:** esas dos pistas son la hipótesis concreta para el agente con LLM.
Si no las resuelve, el LLM no aporta sobre la heurística.

## 2026-10-29 — Prueba mínima de datos (la que faltaba)

**Qué probamos:** obtener de verdad, sin credenciales y desde código, los datos que el
sistema necesita. Criterios fijados antes de mirar: `data/prueba_datos/CRITERIOS.md`.
**Qué esperábamos:** habíamos diseñado el harness asumiendo que los datos se conseguían.
**Qué pasó:** el precio exterior se consigue (Tiendamia, Amazon). La oferta local en
Mercado Libre, que es la verificación central, no: 403 en todos los intentos. Los "más
vendidos" de Mercado Libre responden la mitad de las veces. El ranking de Tiendamia
necesita navegador. Además, Mercado Libre ya vende por Compra Internacional los
repuestos que suponíamos faltantes. Detalle en `data/prueba_datos/RESULTADOS.md`.
**Qué decidimos:** no-go para el diseño actual hasta repetir la prueba con un token de
Mercado Libre. Error de proceso que reconocemos: construimos el harness antes de probar
los datos.

## 2026-10-29 — Scraping desde el navegador: los datos se consiguen, la hipótesis no

**Qué probamos:** los 10 productos de la prueba en el listado de Mercado Libre, desde el
navegador real con sesión iniciada.
**Qué pasó:** 10 de 10 respondieron. Y los 10 tienen oferta local, incluidos los que
usábamos como ejemplos de ausencia (máquina de leche vegetal: 434 publicaciones).
**Qué decidimos:** el acceso a datos tiene salida (navegador, escala chica, declarado).
La hipótesis de "productos que faltan" pierde sustento con los ejemplos obvios: hay que
definir de dónde salen candidatos donde la ausencia sea plausible antes de seguir.

## 2026-10-29 — La señal no es "falta", es "solo llega por cross-border"

**Qué probamos:** 6 búsquedas en Mercado Libre de productos del ranking de más vendidos
de Amazon (Home & Kitchen). Datos en `data/prueba_datos/amazon_vs_ml_2026-10-29.json`.
**Qué pasó:** ninguno falta, pero en los que la búsqueda encuentra el producto correcto,
la oferta es casi toda Compra Internacional: Owala FreeSip 43 de 48 publicaciones, cortina
Barossa 40 de 52. Llegan hoy o mañana solo 4. Y en 3 de 6 búsquedas Mercado Libre devuelve
otra cosa ("zevo" trae cámaras Instax Evo; "upsimples", billeteras).
**Qué decidimos:** proponer al grupo reformular: medir qué parte de la demanda se atiende
solo por cross-border (con sus límites de 5 envíos al año y 3 unidades), y usar el LLM para
saber si dos publicaciones son el mismo producto, que es donde la búsqueda falla.

## 2026-10-29 — El voto con los pies desmiente la lectura anterior

**Qué probamos:** separar las ventas ("+N vendidos" visibles en el listado) entre
publicaciones de Compra Internacional y publicaciones locales, en 6 productos. Datos en
`data/prueba_datos/votos_pies_ml_2026-10-29.json`. Tiendamia ya no publica ranking.
**Qué pasó:** la oferta es mayormente internacional (27 a 43 publicaciones por página),
pero casi no vende: 0 a 4 publicaciones internacionales con ventas, contra 2 a 11 locales.
En los 6 productos, las ventas visibles se concentran en un puñado de publicaciones locales.
**Qué decidimos:** la lectura de la entrada anterior ("solo llega por cross-border") miraba
la oferta, no los votos. Los compradores eligen stock local y no esperan. La señal candidata
pasa a ser: demanda probada (ventas) concentrada en pocos vendedores locales.

## 2026-10-29 — Primera corrida del MVP sobre datos reales

**Qué probamos:** top 30 de Amazon en Cocina → 23 con marca → búsqueda en Mercado Libre →
emparejamiento → clasificación. El paso LLM lo hizo Claude en el chat (sin API key).
Datos en `data/mvp/`.
**Qué pasó:** 17 de 23 no se venden en Mercado Libre con stock local, y la demanda de la
búsqueda la toman sustitutos locales; 4 ya se venden; 1 dudoso; 1 sin demanda visible. El
baseline "menciona la marca" acertó 4 de 15 publicaciones con ventas (6 si se cuentan
probable y dudoso) y habría dado por atendidos 4 productos que no lo están.
**Qué decidimos:** el método produce una salida con sentido y el LLM tiene un trabajo medible
(emparejar). Falta: una medida de competencia mejor que el volumen (las balanzas dominan el
ranking por ser masivas), un segundo anotador, y validar con alguien del rubro si la marca
pesa en la decisión de compra.

## 2026-10-29 — Cuatro chequeos para "¿por qué no se vende?" y corrección del MVP

**Qué probamos:** el MVP anterior suponía que "no se vende acá pero venden parecidos"
significaba demanda insatisfecha. Lo desafiamos con cuatro explicaciones que compiten:
precio, espera, preferencia por otras opciones y falta de demanda. Las sumamos al harness
como skills (`chequear_*`) con una política de diagnóstico, y las corrimos sobre una foto
nueva de las 23 búsquedas (1.372 publicaciones, todos los precios). Datos y resultados en
`data/diagnostico/`.
**Qué pasó:** 16 de 23 no compiten en precio (cuestan 2,3 a 8 veces lo que se vende);
4 ya se venden acá; 1 sin demanda; 2 candidatos a probar. De 387 publicaciones
internacionales de estos productos, ninguna tiene ventas visibles (verificamos que el
contador sí aparece en otras internacionales). En los 4 productos que están en los dos
canales, la gente compra el local aunque el internacional cueste igual o menos: la espera
pesa. Primera versión de la política tenía un error de orden: daba como "oportunidad" a
productos que ya se venden; lo corregimos.
**Qué decidimos:** la conclusión del MVP anterior era incorrecta y la reemplazamos. El
único candidato sólido es el mixer Turelar (más barato que los Oster que se venden, y no
vende): separar espera de marca requiere otro dato. Pendientes: elegir mejor los
sustitutos (hoy entra ruido como la cinta Gorilla Tape) y comparar contra gama parecida.

## 2026-11-05 — API de Mercado Libre y segunda foto

**Qué probamos:** (1) la API de Mercado Libre sin token desde una conexión hogareña, no desde
la nube; (2) repetir la captura de las 23 búsquedas una semana después, ahora con un script
reutilizable (`scripts/captura_ml.js`) que guarda los títulos, y emparejar con reglas
(`scripts/emparejar.py`).
**Qué esperábamos:** que el 403 de la búsqueda fuera por la IP de la nube; que la foto nueva
pudiera cambiar las conclusiones.
**Qué pasó:** desde la conexión hogareña la API responde igual: búsqueda 403 `forbidden`,
más vendidos 401, `/products/search` y `/trends` 403; solo responden categorías. La foto
nueva (1.336 publicaciones) da las **mismas 23 conclusiones** que la del 29/10, y 0
publicaciones internacionales del producto con ventas. Encontramos un error del criterio:
para Gorilla Grip y KitchenAid exige "abrelata" en el título y se pierde "Abridor de latas",
así que subcuenta el producto (Gorilla Grip: 6 marcados, unos 20 reales). No lo corregimos
para que las dos fotos sean comparables; no cambia la conclusión (Gorilla Grip sigue costando 4 veces lo que
se vende; KitchenAid sigue "ya se vende acá"). En la foto nueva el rango de precio de los
16 que no compiten es 1,9 a 6,3 veces (antes 2,3 a 8,1).
**Qué decidimos:** la fuente de datos es la captura desde el navegador, declarada como
limitación. La API queda para quien tenga una app con token (`make prueba-api`). Siguiente
paso: emparejamiento con LLM contra estas reglas, empezando por los errores conocidos.

## 2026-11-05 — API de Mercado Libre con token: cerrada igual

**Qué probamos:** sacar un token válido con la app tp-iaa (authorization_code) y repetir las
llamadas. El usuario cargó el código y la Secret Key en su navegador; guardamos solo códigos
de respuesta en `data/prueba_datos/api_con_token_2026-11-05.json`.
**Qué esperábamos:** que con token la búsqueda respondiera.
**Qué pasó:** el token es válido (`/users/me` responde 200), pero búsqueda por texto, por
categoría, más vendidos, catálogo y tendencias dan 403 "At least one policy returned
UNAUTHORIZED". Están cerradas por política para una app no certificada, con o sin token.
**Qué decidimos:** la API de búsqueda queda descartada como fuente. La fuente es la captura
desde el navegador (`scripts/captura_ml.js`), declarada como limitación.
