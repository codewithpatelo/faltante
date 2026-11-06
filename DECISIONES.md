# Decisiones

Qué elegimos, contra qué, por qué. Para que cualquiera del grupo pueda defenderlas.

**El programa automatiza la función empresarial: descubrir desfasajes de mercado.**
Huerta de Soto (siguiendo a Kirzner) define al empresario como quien se da cuenta de un
desajuste: alguien necesita algo que no tiene, otro lo tiene y no lo valora, y el empresario
los conecta. Acá: un grupo de gente con una necesidad que el mercado local no atiende, y un
proveedor afuera que ya fabrica lo que la resuelve. El conocimiento para verlo está disperso en
miles de elecciones y voces; el programa lo junta (divergencia) y después trata de demostrar
que el desajuste no existe (convergencia). Las grandes cadenas (Walmart, Amazon) deciden qué
tener con sus propios datos de ventas; un importador chico no los tiene, pero sí tiene lo que
el mercado muestra en público: qué se elige, qué se deja pasar, qué se dice y qué se pregunta.

**El LLM propone, el código decide.**
El LLM abre (lee personas, las agrupa, abduce qué traer); seis supuestos críticos probados con
datos cierran (guardrail, C1 y C3 a C6). La divergencia trae hipótesis no obvias; la convergencia
mata el humo. Un LLM que también se juzga a sí mismo confirma lo que propuso.

**La unidad es la persona, no el producto.**
Leyendo un producto por vez, el LLM propuso lo obvio: el repuesto, el accesorio, la versión
mejorada. Cruzando señales de productos distintos mejoró poco: las señales ya venían pegadas a
su producto. Lo que cruza productos es la gente: alguien que vive en un departamento chico con
mascotas compra un bebedero y una aspiradora de auto, y su necesidad no es ninguno de los dos.
Por eso cada voz (opinión o pregunta) se convierte en un **mapa de empatía** chico (situación,
qué quiere lograr, dolor, ganancia, qué teme, con qué compara) y la gente se agrupa en
**segmentos** por situación. Además da escala: 41 productos son miles de personas.

**El mapa de empatía se llena con los dos votos.**
Qué ve (lo que ofrece su búsqueda), qué hace (qué eligió y qué dejó pasar), qué dice
(opiniones), qué teme (las preguntas de los indecisos son, sobre todo, miedos), dolores y
ganancias. Se eligió el mapa de empatía para describir a la persona porque cada uno de sus
cuadrantes tiene un dato que lo llena; la propuesta se escribe como la mitad izquierda del
canvas de propuesta de valor (qué dolor alivia, qué ganancia crea, por qué le gana a lo que ya
ve).

**Cada pieza entra solo si la evidencia dice que mejora.**
Las versiones se comparan en escala_dev, 3 corridas cada una, con la misma medida: propuestas
distintas que pasan C4 (nadie lo trae) y C5 (la eligen si se ofrece), y su proporción sobre las
que pasan C1 a C3 (`data/evaluacion/versiones_escala_dev/`). Con las reglas de C3 a C5 de abajo: señales
por producto más cruce, 1,0 por corrida (16%); personas con segmentos libres, 11,7 (22%), 35 ideas
distintas en 3 corridas; personas con segmentos obligados a cruzar búsquedas, 3,3 (14%). La idea de obligar a cruzar
búsquedas sonaba bien (en la primera corrida muchos segmentos eran "los compradores de X"), pero
empeoró la medida, así que se sacó. Un paso de dolor antes de proponer (el LLM formula
dolores, un clasificador independiente mide quién los tiene en los textos originales y una prueba
exacta de Fisher con corrección de Benjamini-Hochberg contra gente de afuera decide cuáles siguen;
un dolor placebo nunca salió significativo): 9,0 por corrida contra 11,7, con la misma proporción
(22%). Filtra pero no elige mejor: la fuerza del dolor apenas separa las ideas que sobreviven de
las que mueren (p = 0,07). No entró. El problema es la implementación, no la idea: como filtro
antes de proponer recorta el volumen, y C4 y C5 miden el mercado, no si el dolor existe. Usada
como chequeo de la propuesta, en lugar del conteo de palabras clave de C1 y C2, sí entró
(prerregistrado en `data/evaluacion/dolor_de_la_propuesta/`): sobre las mismas propuestas, 16,7
sobrevivientes por corrida contra 11,7, y 42% de las que llegan a C4 pasan C5 contra 40%. La
ganancia viene de sacar el conteo, que mataba ideas que la gente sí elige; el dolor medido no
predice qué elige el mercado (deja pasar el 84%; las que mata sobreviven C5 tanto como las otras),
pero agrega lo que C4 y C5 no ven: que la necesidad existe en la gente, medida por alguien que no
propuso. Eso es lo que evita el primer error del emprendedor, saltar a la solución. Después apareció un
problema de medición en C4: el criterio de qué publicaciones son "lo mismo" lo escribía el mismo
LLM que proponía, y dejaba afuera competidores obvios (para un quitapelos de mascotas no contaba
uno que vende +10.000). Ahora lo juzga otro modelo que solo ve qué se propone y los títulos
(`harness/equivalencias.py`). Prerregistrado en `data/evaluacion/equivalencias/`: en 40
desacuerdos etiquetados a ciegas, el juez acierta 32 y el criterio viejo 8 (binomial, p < 0,001);
cuando se equivoca, tiende a contar de más (más estricto con la idea). Con el juez, las mismas
propuestas dejan 8,7 sobrevivientes de C5 por corrida: los 16,7 de antes estaban inflados por
el criterio del autor. Esa es la medida de referencia de acá en adelante. Lo que todavía no mide ninguna corrida: si las ideas que
sobreviven son obvias (juicio humano a ciegas, pendiente) y si dejan margen (falta precio de
proveedor).

**El prompt se probó, no se adivinó.**
Antes de pasar a personas se compararon 25 variantes del prompt que cruzaba señales (espacio
balanceado de decisiones tomadas de la literatura: inspiraciones lejanas como en MOOSE-Chem,
explicación rival, razonamiento de detective, re-preguntar, evitar lo obvio, rol), cada una
medida 3 veces, y la mejor se optimizó al estilo GEPA. Dos hallazgos: (1) el mismo prompt varía
tanto entre corridas que la variante ganadora casi nunca gana al repetirla; (2) dos decisiones
rinden en los dos conjuntos de datos: **pedir una segunda tanda distinta** (2,6 contra 1,2
propuestas no obvias en promedio) y **prohibir lo obvio** (2,4 contra 1,4). Las dos quedaron en
el paso B. El código de esa comparación se borró al pasar a personas (está en el historial de
git); sus resultados están en `data/serendipia/espacio_*.json` y `optimizacion_escala_dev.json`.

**El LLM no juzga lo que se recomienda.**
Los LLM son malos jueces de ideas (Si, Yang y Hashimoto, 2024: el ranking automático coincide
poco con humanos; Cristofaro et al., 2025: la IA limita la novedad al reconocer oportunidades).
Qué se recomienda lo deciden los supuestos críticos en código, contra lo que la gente hizo.

**Guardrails en código, no en el prompt.**
"Citá textos reales" en el prompt es una sugerencia. En el código es una regla: cada persona
anotada cita un fragmento literal de su texto; cada propuesta cita personas del segmento; cada
señal del embudo cita 2 textos distintos. Si algo no pasa, el error vuelve al modelo una vez y
lo que sigue mal se descarta.

**Quien propone no es quien mide (C1).**
El dolor de cada propuesta lo lee otro modelo, que solo ve el dolor y los textos originales de la
gente de los productos que cita y de un grupo de control al azar; no sabe qué se propone ni quién
lo propuso. Cuenta quiénes lo tienen sin resolver (los desatendidos: los conformes no refutan el
dolor, dicen para quién funciona la solución de hoy) y decide una prueba exacta de Fisher con
corrección de Benjamini-Hochberg. Así una necesidad no pasa por estar bien redactada. Antes lo
hacía un conteo de las palabras clave que elegía el mismo LLM, con umbrales a ojo y el puntaje de
Ulwick; se sacó porque mataba ideas buenas. A los baselines se les mide el dolor igual.

**Lo que se deja pasar también es un voto (C5).**
"Nadie lo vende con volumen" no prueba que haya un hueco: si la alternativa se ofrece con stock
local y a precio comparable, y la gente igual elige el producto de origen, la necesidad no
alcanza para que la compren. Es humo. Lo importado (con espera) y lo caro no cuentan como
alternativa, porque explican por sí solos que no se elija.

**Una oportunidad tiene que dejar plata al precio que la gente paga (C6).**
El precio de mercado es la mediana de los equivalentes que vendieron algo: una publicación sin
ventas puede pedir cualquier cosa, y si ningún equivalente vendió, nadie lo compró a ningún
precio. El piso no es un número elegido: es la ganancia neta sobre ventas del comercio minorista
(Damodaran, enero 2026, 5,19%), después de descontar todo lo que antes cubría un "colchón" de 30%
puesto a ojo: comisión, impuestos, envío, publicidad (ACOS de Hogar en Mercado Libre) y
devoluciones (contadas como unidad perdida). Cada costo incierto va en tres escenarios con la
fuente de cada extremo (`harness/costo_puesto.py`). Con esos costos a la vista, la publicidad y
las devoluciones se comen cerca de un cuarto del precio: el pastillero de dev, que con el 30%
"casi pasaba", necesita un FOB de USD 1,99, debajo del catálogo. Si el margen no llega, se
calcula el FOB máximo: la oportunidad queda condicional y el experimento siguiente es pedir
cotización. Pendiente de fuente oficial: la alícuota de Ingresos Brutos y el volumen extra del
embalaje.

**Confianza calculada, no opinada.**
Sobrevivir dice que nada refutó la oportunidad; no dice cuán sólida es la evidencia. La
confianza (alta, media, baja) sale de cinco factores de sí o no que calcula el programa.

**Baselines sin LLM por el mismo embudo.**
B1 (queja más frecuente) es lo que haría un análisis de palabras, y es lo que hacen las
herramientas comerciales (Jungle Scout, Product Opportunity Explorer): mejorar el producto por
su queja. B2 (pedidos de repuesto) es una regla fuerte escrita después de leer dev. Si el LLM no
les gana en test, el LLM sobra.

**Partición por búsqueda, decidida antes de leer.**
Dev para iterar skills, criterios y umbrales; test una sola vez, con todo congelado. Las
búsquedas (no los productos) se reparten por hash, así los dos anclas de una búsqueda quedan
del mismo lado.

**Captura desde el navegador.**
La API de búsqueda de Mercado Libre devuelve 403 aun con token válido. Leer la página con la
sesión del usuario es lo único que funciona; se guarda solo el texto visible.

**Código escrito a mano, sin frameworks de agentes.**
El embudo es una lista de seis supuestos críticos con nombre (`harness/embudo.py`). La defensa
es individual y cada uno tiene que poder explicarlo por dentro; un framework deja una caja negra.

**DeepSeek Flash.**
Lo que falta es escala: leer 3.389 personas, armar segmentos y proponer costó USD 1,39 en la
primera corrida de escala_dev, y rehacer segmentos y propuestas, unos USD 0,95. Leer y asignar
personas va sin razonamiento (es clasificar); definir segmentos y proponer, con razonamiento.
