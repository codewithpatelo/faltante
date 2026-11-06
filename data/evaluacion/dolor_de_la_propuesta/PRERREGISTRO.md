# Prerregistro: el dolor medido como chequeo de la propuesta (en lugar de C1 y C2)

Escrito antes de correr la medición (6/11/2026).

**Qué se mide.** Las propuestas ya guardadas de las 3 corridas de personas con segmentos libres
(la mejor versión, `data/evaluacion/versiones_escala_dev/eval-personas-libres_*.json`). A cada
una se le mide el dolor que dice aliviar con `harness/dolor_de_la_propuesta.py` (clasificador
independiente + Fisher + Benjamini-Hochberg contra un control al azar). No se generan propuestas
nuevas: cambia solo el chequeo.

**Comparación.** Mismas propuestas, mismo C3 a C5, dos versiones del embudo:
A = C1 y C2 actuales (conteo de palabras clave); B = el dolor medido en lugar de C1 y C2.

**Regla (para que entre B).** En promedio por corrida, B deja al menos tantas propuestas
distintas que pasan C5 como A, **y** una proporción de las que pasan C5 sobre las que llegan a C4
mayor o igual. Además se informa, con Fisher, si entre las propuestas que pasan C3 el dolor
medido separa las que pasan C5 de las que no (si no separa, el chequeo no agrega información
sobre el mercado, aunque pueda agregarla sobre la necesidad).

**Diagnóstico si no entra.** Mirar a mano 10 propuestas que A deja y B mata, y 10 al revés, para
distinguir si falla la idea (el dolor medido no tiene relación con lo que el mercado elige) o la
implementación (el enunciado del dolor sale de la propuesta y mezcla la solución, o el control
no es comparable).
