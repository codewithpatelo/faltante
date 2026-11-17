# Agrupar por trabajo en vez de por situación (dev, 17/11, escrito antes de correrlo)

**Qué cambia.** Los grupos de la divergencia los definía el LLM en una sola llamada a partir de
la "situación" de cada persona. El 70% de las tarjetas no tiene situación, y los grupos salieron
por categoría de producto ("Convivencia con gatos", "Bebés de 0 a 12 meses"): 27 a 33 grupos de
hasta 720 personas, cada uno con unas 4 propuestas. Ahora, como se hace en la literatura:

1. El LLM reescribe cada tarjeta como el **trabajo** que la persona intenta hacer, un nivel por
   encima del producto y sin nombrarlo, y lo que le sale mal (Ulwick, Jobs-to-be-Done; etapa de
   resumen orientado al uso de TnT-LLM, Wan et al. 2024).
2. Los trabajos se agrupan por significado con vectores de palabras y Ward (Timoshenko y Hauser,
   2019). El corte del árbol es el que deja más grupos con 2 personas en cada uno de 2 productos.
3. Se propone primero para los trabajos que a más gente le salen mal, con tantas llamadas al paso
   B como productos (el mismo esfuerzo que B3).

**Medida.** La misma de siempre: oportunidades distintas no descartadas por el embudo en dev.
**Regla.** La versión nueva reemplaza a la vieja si deja más que la vieja en dev (13 de 135).
Se informa también contra B3 en dev (31 de 230). Una sola corrida: el plazo de entrega no da
para tres, y se declara. Test no se vuelve a correr: ya se usó con la versión vieja, y su
resultado queda como está.
