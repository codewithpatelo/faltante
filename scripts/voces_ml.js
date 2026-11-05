// Junta el voto con las manos de cada producto ancla: opiniones de compradores y preguntas
// de indecisos. Corre en tu navegador, con tu sesión, porque la API de Mercado Libre está
// cerrada. Lee solo texto visible; no lee ni envía cookies, tokens ni datos de tu cuenta.
//
// Son dos pasadas, porque opiniones y preguntas viven en dominios distintos:
//
//   1. OPINIONES, desde https://www.mercadolibre.com.ar (cualquier página):
//        window.__vocesProductos = ["https://www.mercadolibre.com.ar/.../p/MLA123", ...];
//      pegá este archivo y Enter. Descarga opiniones_<fecha>.json (con el ID de cada publicación).
//
//   2. PREGUNTAS, desde https://articulo.mercadolibre.com.ar (cualquier página):
//        window.__vocesItems = [...los "item" de opiniones_<fecha>.json...];
//      pegá este archivo y Enter. Descarga preguntas_<fecha>.json.
//
// Guardá los dos en data/voces/ y corré: python scripts/unir_voces.py <fecha>
// Tarda ~30 s por producto en la pasada 1 y ~5 s en la 2. El avance queda en window.__voces.

(async () => {
  const espera = (ms) => new Promise((r) => setTimeout(r, ms));
  const fecha = new Date().toISOString().slice(0, 10);

  // Una página de Mercado Libre metida en la pantalla actual. Tiene que estar visible (aunque
  // casi transparente): las opiniones se cargan a medida que se ven.
  async function abrir(ruta) {
    const f = document.createElement("iframe");
    f.style.cssText = "position:fixed;left:0;top:0;width:1000px;height:800px;opacity:0.02;z-index:99999;pointer-events:none";
    f.src = ruta;
    document.body.appendChild(f);
    await espera(4000);
    return f;
  }

  // Saca de un texto lo que no hace falta guardar: enlaces y números largos (CUIT, teléfonos).
  const limpio = (t) => t.replace(/https?:\/\/\S+/g, "[enlace]").replace(/\d[\d-]{7,}\d/g, "[número]").trim();

  function descargar(nombre, datos) {
    window.__vocesResultado = datos;
    if (window.__vocesDescargar === false) return;   // para probar sin bajar archivos
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(datos, null, 1)], { type: "application/json" }));
    a.download = nombre;
    a.click();
  }

  // --- Pasada 1: opiniones -------------------------------------------------------------------
  async function opinionesDe(url) {
    const html = await fetch(new URL(url).pathname).then((r) => r.text());
    const item = (html.match(/noindex\/questions\/(MLA\d+)/) || [])[1] || null;
    // Las opiniones se piden con el ID de la publicación (el mismo de las preguntas); el ID de
    // catálogo de las páginas /p/ devuelve una lista vacía.
    const idOpiniones = item || (html.match(/catalog_product_id":"(MLA\d+)"/) || [])[1];
    const titulo = ((html.match(/<meta property="og:title" content="([^"]+)"/) || [])[1] || "").replace(/ - \$.*$/, "");
    const precio = Number((html.match(/"price":(\d+)/) || [])[1]) || null;
    const m = html.match(/\+(\d+)\s*(mil)?\s*vendidos/);
    const vendidos = m ? Number(m[1]) * (m[2] ? 1000 : 1) : 0;
    const calificacion = (html.match(/Calificación [\d.]+ de 5\. [\d.]+ opiniones/) || [])[0] || null;
    let opiniones = [];
    if (idOpiniones) {
      const f = await abrir(`/noindex/catalog/reviews/${idOpiniones}?noIndex=true&access=view_all&modal=true`);
      const leer = () => [...f.contentDocument.querySelectorAll("p.ui-review-capability-comments__comment__content")];
      let antes = -1, quietas = 0;
      while (quietas < 3) {                       // seguir bajando hasta que no aparezcan más
        f.contentWindow.scrollTo(0, f.contentDocument.body.scrollHeight);
        await espera(1000);
        const ahora = leer().length;
        quietas = ahora === antes ? quietas + 1 : 0;
        antes = ahora;
      }
      opiniones = leer().map((p) => limpio(p.textContent)).filter(Boolean);
      f.remove();
    }
    return { url, item, titulo, precio, vendidos, calificacion, opiniones };
  }

  // --- Pasada 2: preguntas -------------------------------------------------------------------
  async function preguntasDe(item) {
    const f = await abrir(`/noindex/questions/${item}`);
    const lineas = (f.contentDocument.querySelector("main")?.innerText || "").split("\n").map((l) => l.trim())
      .filter((l) => l && !/^Denunciar$|^Se abrirá en una nueva ventana$|^Preguntas en esta publicación$/.test(l));
    f.remove();
    // Cada pregunta termina en la fecha de la respuesta: [pregunta, respuesta, dd/mm/aaaa]
    const pares = [];
    let bloque = [];
    for (const l of lineas) {
      if (/^\d{2}\/\d{2}\/\d{4}$/.test(l)) {
        if (bloque.length) pares.push([limpio(bloque.slice(0, -1).join(" ") || bloque[0]), bloque.length > 1 ? limpio(bloque.at(-1)) : ""]);
        bloque = [];
      } else bloque.push(l);
    }
    return { item, preguntas: pares };
  }

  // --- Qué pasada corre ----------------------------------------------------------------------
  if (location.hostname === "www.mercadolibre.com.ar") {
    const urls = window.__vocesProductos || [];
    if (!urls.length) return console.error("[voces] Definí antes window.__vocesProductos = [\"https://www.mercadolibre.com.ar/...\"]");
    window.__voces = { pasada: "opiniones", hechas: 0, de: urls.length, productos: [] };
    for (const url of urls) {
      try { window.__voces.productos.push(await opinionesDe(url)); }
      catch (e) { window.__voces.productos.push({ url, error: String(e).slice(0, 120) }); }
      window.__voces.hechas++;
    }
    descargar(`opiniones_${fecha}.json`, { fecha, como: "scripts/voces_ml.js, pasada 1", productos: window.__voces.productos });
  } else if (location.hostname === "articulo.mercadolibre.com.ar") {
    const items = window.__vocesItems || [];
    if (!items.length) return console.error("[voces] Definí antes window.__vocesItems = [\"MLA...\"]");
    window.__voces = { pasada: "preguntas", hechas: 0, de: items.length, productos: [] };
    for (const item of items) {
      try { window.__voces.productos.push(await preguntasDe(item)); }
      catch (e) { window.__voces.productos.push({ item, error: String(e).slice(0, 120) }); }
      window.__voces.hechas++;
    }
    descargar(`preguntas_${fecha}.json`, { fecha, como: "scripts/voces_ml.js, pasada 2", productos: window.__voces.productos });
  } else {
    console.error("[voces] Abrí www.mercadolibre.com.ar (opiniones) o articulo.mercadolibre.com.ar (preguntas).");
  }
  window.__voces.estado = "listo";
})();
