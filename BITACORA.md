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
