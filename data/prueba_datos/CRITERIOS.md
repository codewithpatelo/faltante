# Prueba mínima de datos — criterios fijados antes de mirar resultados

Pregunta: ¿podemos obtener los datos que el sistema necesita, con calidad suficiente?
Si la respuesta es no, el proyecto como está planteado no se sostiene.

| # | Qué tiene que pasar | Aprueba si |
|---|---|---|
| T1 | Pistas reales | Al menos 20 productos concretos de una fuente de voto con los pies, con fecha, obtenidos sin intervención manual |
| T2 | Oferta local | Para un producto dado, obtener cantidad de publicaciones o vendedores en Mercado Libre |
| T3 | Precio exterior | Para el mismo producto, obtener un precio fuera de Argentina |
| T4 | Calidad | En una muestra de 10 productos, T2 y T3 se resuelven en al menos 7, y el producto encontrado es el mismo (no uno parecido) |
| T5 | Repetible | Lo de T1 a T3 se puede automatizar desde código, sin un humano logueado |

Veredicto:
- **Go:** pasan T1 a T5.
- **Go condicional:** pasa T1 a T4 pero T5 depende de credenciales o de un navegador.
- **No-go:** falla T1, T2 o T4.
