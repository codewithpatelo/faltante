// Opiniones de compradores de una publicación de Mercado Libre: para qué dicen que la usan.
//
// Cómo se usa: abrí la publicación (www.mercadolibre.com.ar/.../p/MLA...) con tu sesión, abrí la
// consola, pegá este archivo. Abre "Mostrar todas las opiniones", baja hasta cargar ~150, y
// deja en window.__voces: cantidad, conteo por categoría de uso y los n-gramas "para X".
// Editá CATEGORIAS con las hipótesis que quieras refutar. No lee datos de la cuenta.
(async () => {
  const CATEGORIAS = window.__vocesCategorias || {
    negocio: /negocio|local\b|kiosco|cantina|restaurante|clientes|emprend/i,
    regalo: /regal[eoa]|para mi (pap[aá]|mam[aá]|espos|novi)/i,
  };
  const esp = (ms) => new Promise((r) => setTimeout(r, ms));
  window.scrollTo(0, document.body.scrollHeight);
  await esp(2500);
  [...document.querySelectorAll("button")].find((b) => /Mostrar todas las opiniones/i.test(b.innerText))?.click();
  await esp(3500);
  const f = [...document.querySelectorAll("iframe")].find((f) => /review/.test(f.src));
  if (!f) return console.error("[voces] no se abrió el panel de opiniones");
  const d = f.contentDocument, w = f.contentWindow;
  for (let i = 0; i < 22; i++) {
    [...d.querySelectorAll("*")].filter((e) => e.scrollHeight > e.clientHeight + 50).forEach((e) => (e.scrollTop = e.scrollHeight));
    w.scrollTo(0, d.body.scrollHeight);
    await esp(700);
  }
  const textos = [...new Set([...d.querySelectorAll("p")].map((p) => p.innerText.trim()).filter((t) => t.length > 20 && !/^Calificaci/.test(t)))];
  const usos = {};
  for (const x of textos) {
    const n = x.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    for (const m of n.matchAll(/\bpara ([a-z]+)(?: ([a-z]+))?/g)) {
      const k = [m[1], m[2]].filter(Boolean).join(" ");
      usos[k] = (usos[k] || 0) + 1;
    }
  }
  window.__voces = {
    url: location.pathname, opiniones_leidas: textos.length,
    categorias: Object.fromEntries(Object.entries(CATEGORIAS).map(([k, re]) => [k, textos.filter((t) => re.test(t)).length])),
    para_x: Object.entries(usos).sort((a, b) => b[1] - a[1]).slice(0, 25), textos,
  };
  console.log("[voces]", window.__voces.opiniones_leidas, "opiniones", window.__voces.categorias);
})();
