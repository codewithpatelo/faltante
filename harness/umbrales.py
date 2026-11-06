"""Todos los umbrales del embudo, en un solo lugar.

Cambiar un número de acá cambia qué oportunidades pasan. Cada uno dice qué mide y de
dónde sale; los que son decisión nuestra lo dicen.
"""

# Pruebas estadísticas (C1 y C5): convención; en C1 se corrige por la cantidad de propuestas (Benjamini-Hochberg)
NIVEL_DE_SIGNIFICANCIA = 0.05

# C1 · El dolor existe: prueba estadística, sin umbrales propios (harness/dolor.py)

# Lo que vende una publicación típica, medido en las capturas (31.314 publicaciones de 498 búsquedas,
# noviembre 2026): de las publicaciones locales que vendieron algo, la mediana muestra "+100" y el
# escalón siguiente que muestra Mercado Libre es "+500".
VENTAS_DE_LA_PUBLICACION_TIPICA = 100

# C3 · Hay demanda: el producto donde aparece la señal vende más que la publicación típica
MIN_VENDIDOS_DEL_ANCLA = 500          # el primer escalón de "+N vendidos" arriba de la mediana

# C4 · Nadie la atiende todavía
VENDIDOS_PARA_DECIR_QUE_YA_VENDE = VENTAS_DE_LA_PUBLICACION_TIPICA   # un equivalente "vende" si vende como la publicación típica
MAX_EQUIVALENTES_QUE_YA_VENDEN = 2    # con 3 a 5 competidores un mercado ya se comporta como competitivo y el siguiente
                                      # cambia poco (Bresnahan y Reiss, 1991): con 3 o más que venden, está atendida

# C5 · Si se ofrece, la gente lo elige (voto con los pies: lo que se deja pasar también cuenta)
# Las alternativas comparables (stock local, precio no atípico: debajo de la valla de Tukey, Q3 + 1,5 x rango
# intercuartil) se comparan con las publicaciones locales de la búsqueda de donde salió la necesidad: si venden
# significativamente menos (Mann-Whitney unilateral; "+N vendidos" es ordinal), la gente la tuvo enfrente y la dejó pasar.

# C6 · Deja plata al precio que la gente paga
MIN_MARGEN_NETO = 0.0519              # ganancia neta sobre ventas de referencia: Retail (Special Lines), Damodaran, enero 2026; publicidad,
                                      # devoluciones, comisión, impuestos y logística ya se descuentan (harness/costo_puesto.py)
UNIDADES_MAX_PRIMER_LOTE = 1000       # el lote llena 1 m3 o llega a este tope, lo que pase primero

# Confianza de una oportunidad que pasó (harness/confianza.py): decisiones nuestras
MIN_ANCLAS_CON_LA_NECESIDAD = 2       # la misma necesidad aparece en 2 o más productos distintos
MIN_DESATENDIDOS_PARA_CONFIANZA = 10  # 10 o más personas con el dolor sin resolver (PENDIENTE: fundamentar)
MIN_VENTAS_DE_EQUIVALENTES = 500      # la gente ya elige este tipo de producto (suma de "+N vendidos")
MIN_PUBLICACIONES_PARA_PRECIO = 3     # el precio de referencia sale de 3 o más publicaciones con ventas
FACTORES_PARA_CONFIANZA_ALTA = 4      # de 5
FACTORES_PARA_CONFIANZA_MEDIA = 3

# Envío de Mercado Libre a cargo del vendedor (algoritmodigital.com.ar, septiembre 2026)
PRECIO_DESDE_EL_QUE_EL_ENVIO_ES_GRATIS = 33000   # ARS
ENVIO_DEBAJO_DEL_PISO = 2500          # ARS por unidad (costo fijo: 1.330 a 4.550 según modalidad)
ENVIO_ARRIBA_DEL_PISO = 7000          # ARS por unidad, paquete chico (6.190 a 8.290)
