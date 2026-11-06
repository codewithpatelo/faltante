# Prerregistro: equivalencias juzgadas por quien no propuso (C4 a C6)

Escrito antes de correr el juez (6/11/2026).

**Problema.** El criterio de equivalencia lo escribía el mismo LLM que proponía. Auditando las
propuestas que sobreviven C5 en la mejor versión (personas libres + C1 dolor), el criterio deja
afuera competidores obvios: para "saca pelos de mascotas tapizados" no cuenta "Quita Pelo Mascota
Ropa Tapizados" (+10.000) ni "Cepillo Quita Pelusa Mascotas" (+10.000); para "pistola
masajeadora", `excluir: ["masajeador"]` saca todas las pistolas masajeadoras. Es un conflicto de
interés: el autor de la idea define qué es su competencia.

**Qué cambia.** Otro modelo (`skills/juzgar_equivalencia`), que solo ve qué se propone, para qué,
y los títulos de la búsqueda, dice cuáles la reemplazan. Mismas propuestas guardadas (las 3
corridas de personas libres), mismas capturas.

**Cómo se decide (es un instrumento, no una pieza del programa: se juzga por si mide bien).**
1. Se toman al azar 40 publicaciones donde el criterio viejo y el juez no coinciden (semilla 7).
2. Se etiquetan a ciegas (sin saber qué método dijo qué): ¿un comprador de lo propuesto podría
   comprar esta publicación en su lugar?
3. El juez entra si acierta en más de la mitad de los desacuerdos (prueba binomial unilateral al 5%).
4. Se informa cómo cambian los sobrevivientes de C4 y C5 por corrida.
