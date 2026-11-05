"""Todos los umbrales del embudo, en un solo lugar.

Cambiar un número de acá cambia qué oportunidades sobreviven. Cada uno dice qué mide y de
dónde sale; los que son decisión nuestra lo dicen.
"""

# C1 · La señal no es anecdótica
MIN_TEXTOS_CON_LA_SEÑAL = 3          # decisión: con 1 o 2 textos puede ser un caso aislado

# C2 · La necesidad importa y está mal resuelta (puntaje de oportunidad de Ulwick, escala 0-10)
PROPORCION_PARA_IMPORTANCIA_10 = 0.10  # decisión: si el 10% de los textos la menciona, importancia = 10
MIN_IMPORTANCIA = 3.0                 # = la menciona al menos el 3% de los textos
MAX_SATISFACCION = 5.0                # = al menos la mitad de las menciones son queja, duda o pedido

# C3 · Hay demanda: el producto donde aparece la señal se vende
MIN_VENDIDOS_DEL_ANCLA = 500

# C4 · Nadie la atiende todavía
VENDIDOS_PARA_DECIR_QUE_YA_VENDE = 100
MAX_EQUIVALENTES_QUE_YA_VENDEN = 2    # decisión: con 3 o más vendedores que venden, la necesidad está atendida

# C5 · Deja plata al precio que la gente paga
MIN_MARGEN_SOBRE_COSTO = 0.30         # decisión: colchón para devoluciones, publicidad y error de cotización
UNIDADES_MAX_PRIMER_LOTE = 1000       # el lote llena 1 m3 o llega a este tope, lo que pase primero

# Envío de Mercado Libre a cargo del vendedor (algoritmodigital.com.ar, septiembre 2026)
PRECIO_DESDE_EL_QUE_EL_ENVIO_ES_GRATIS = 33000   # ARS
ENVIO_DEBAJO_DEL_PISO = 2500          # ARS por unidad (costo fijo: 1.330 a 4.550 según modalidad)
ENVIO_ARRIBA_DEL_PISO = 7000          # ARS por unidad, paquete chico (6.190 a 8.290)
