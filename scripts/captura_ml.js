// Captura de la primera página de búsqueda de Mercado Libre, desde tu propio navegador.
// La usa C4: para cada oportunidad, ¿ya hay equivalentes que se venden?
//
// Por qué así: la API de búsqueda de Mercado Libre devuelve 403 sin token (probado desde la
// nube y desde una conexión hogareña, 2026-11-05) y la web no se puede leer con un script
// común. Desde el navegador con sesión iniciada sí se lee el listado.
//
// Cómo se usa:
//   1. Con tu sesión iniciada, abrí una búsqueda cualquiera: https://listado.mercadolibre.com.ar/termo
//      (tiene que ser listado.mercadolibre.com.ar; desde www. el navegador no deja leer el listado).
//   2. Abrí la consola (F12 → Consola) y definí las búsquedas (las que el embudo marca como
//      "falta capturar la búsqueda"): window.__capturaBusquedas = ["tabla de picar doble faz"];
//   3. Pegá este archivo entero y Enter. Tarda ~20 s por búsqueda; al terminar descarga
//      captura_ml_<fecha>.json.
//   4. Guardala como data/capturas/captura_ml_serendipia_<fecha>.json: `make serendipia` la toma sola.
//
// No lee ni envía cookies, tokens ni datos de tu cuenta: solo el texto visible del listado
// (título, precio, "+N vendidos", "Compra Internacional").

(async () => {
  const BUSQUEDAS = window.__capturaBusquedas;
  if (!BUSQUEDAS || !BUSQUEDAS.length) {
    console.error("[captura] Definí antes window.__capturaBusquedas = [\"...\"] (ver arriba).");
    return;
  }
  if (location.hostname !== "listado.mercadolibre.com.ar") {
    console.error("[captura] Abrí primero https://listado.mercadolibre.com.ar/termo y pegá el script ahí.");
    return;
  }
  const DESCARGAR = window.__capturaDescargar !== false;
  const espera = (ms) => new Promise((r) => setTimeout(r, ms));

  function leer(doc) {
    return [...doc.querySelectorAll("li.ui-search-layout__item")].map((li) => {
      const txt = li.textContent;
      const m = txt.match(/\+(\d+)\s*(mil)?\s*vendidos/i);
      const precioEl =
        li.querySelector(".poly-price__current .andes-money-amount__fraction") ||
        li.querySelector(".andes-money-amount__fraction");
      return {
        titulo: (li.querySelector(".poly-component__title")?.textContent || "").trim(),
        internacional: /internacional/i.test(txt) ? 1 : 0,
        vendidos: m ? parseInt(m[1], 10) * (m[2] ? 1000 : 1) : 0,
        precio: precioEl ? parseInt(precioEl.textContent.replace(/\./g, ""), 10) : null,
      };
    });
  }

  async function capturar(busqueda) {
    const slug = busqueda.trim().split(/\s+/).map(encodeURIComponent).join("-");
    const f = document.createElement("iframe");
    f.style.cssText = "position:fixed;left:-9999px;width:1200px;height:900px";
    f.src = `https://listado.mercadolibre.com.ar/${slug}`;
    document.body.appendChild(f);
    try {
      for (let i = 0; i < 40; i++) {
        await espera(500);
        const doc = f.contentDocument;
        if (doc && doc.querySelectorAll("li.ui-search-layout__item").length) {
          await espera(800); // que terminen de pintarse precios y etiquetas
          return {
            total: doc.querySelector(".ui-search-search-result__quantity-results")?.textContent.trim() || null,
            publicaciones: leer(doc),
          };
        }
      }
      return { total: null, publicaciones: [], error: "sin resultados o la página no cargó" };
    } finally {
      f.remove();
    }
  }

  const fecha = new Date().toISOString().slice(0, 10);
  const salida = {
    fecha,
    fuente: "primera página de listado.mercadolibre.com.ar, navegador con sesión iniciada (scripts/captura_ml.js)",
    busquedas: {},
  };
  window.__captura = { estado: "corriendo", hechas: 0, de: BUSQUEDAS.length, salida };
  for (const b of BUSQUEDAS) {
    salida.busquedas[b] = await capturar(b);
    window.__captura.hechas++;
    console.log(`[captura] ${b}: ${salida.busquedas[b].publicaciones.length} publicaciones`);
  }
  window.__captura.estado = "listo";

  if (DESCARGAR) {
    const blob = new Blob([JSON.stringify(salida, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `captura_ml_${fecha}.json`;
    a.click();
  }
  console.log("[captura] listo");
})();
