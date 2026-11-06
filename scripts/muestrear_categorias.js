// Elige qué búsquedas recolectar sin elegirlas a mano: muestrea categorías hoja del árbol de
// Mercado Libre con probabilidad proporcional a la cantidad de publicaciones (cada paso baja a un
// hijo con probabilidad proporcional a sus publicaciones; muestreo PPS), 11 por cada categoría raíz
// de bienes de consumo importables, con semilla fija. El texto de búsqueda es el nombre de la hoja
// (más el del padre, o el de la raíz, si la hoja es una sola palabra).
//
// Raíces (decidido antes de muestrear): accesorios para vehículos, mascotas, bebés, belleza y
// cuidado personal, deportes y fitness, herramientas, hogar, juegos y juguetes, arte y librería.
// Quedan afuera alimentos, celulares, computación y electrónica (homologación), salud (ANMAT),
// inmuebles, autos, servicios y antigüedades.
//
// Se corre en la consola de cualquier página de mercadolibre.com.ar (la API de categorías responde
// desde el navegador). Deja el resultado en window.__muestra. Corrida del 6/11/2026: 99 hojas,
// búsquedas en data/capturas/captura_ml_escala_2026-11-06.json.

(async () => {
  const RAICES = ["MLA5725", "MLA1071", "MLA1384", "MLA1246", "MLA1276", "MLA407134", "MLA1574", "MLA1132", "MLA1368"];
  const POR_RAIZ = 11, SEMILLA = 7;
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const azar = mulberry32(SEMILLA), cache = {};
  const categoria = async (id) => cache[id] || (cache[id] = await fetch(`https://api.mercadolibre.com/categories/${id}`).then((r) => r.json()));
  async function hoja(raiz) {
    let c = await categoria(raiz); const ruta = [c.name];
    while ((c.children_categories || []).length) {
      const hijos = c.children_categories.filter((h) => !/^Otro/i.test(h.name));
      if (!hijos.length) break;
      const total = hijos.reduce((s, h) => s + (h.total_items_in_this_category || 0), 0);
      let x = azar() * total, elegido = hijos[hijos.length - 1];
      for (const h of hijos) { x -= h.total_items_in_this_category || 0; if (x <= 0) { elegido = h; break; } }
      c = await categoria(elegido.id); ruta.push(c.name);
    }
    return { id: c.id, nombre: c.name, ruta: ruta.join(" > "), items: c.total_items_in_this_category };
  }
  const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  window.__muestra = [];
  for (const raiz of RAICES) {
    const vistas = new Set(); let intentos = 0;
    while (vistas.size < POR_RAIZ && intentos < 60) {
      intentos++; const h = await hoja(raiz);
      if (!vistas.has(h.id)) { vistas.add(h.id); window.__muestra.push({ raiz, ...h }); }
    }
  }
  for (const h of window.__muestra) {
    const r = h.ruta.split(" > "), hojaNombre = r.at(-1), padre = r.at(-2), raizNombre = r[0];
    let b = hojaNombre;
    if (hojaNombre.trim().split(/\s+/).length === 1) b += " " + (padre && !norm(padre).includes(norm(hojaNombre)) ? padre : raizNombre);
    h.busqueda = norm(b).replace(/[^a-z0-9ñ ]/g, " ").replace(/\s+/g, " ").trim();
  }
  console.log(`[muestra] ${window.__muestra.length} búsquedas`);
})();
