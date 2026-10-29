"""Adaptador en vivo contra la API de Mercado Libre (solo contar_oferta por ahora).

Estado verificado el 29/10/2026 desde el entorno de desarrollo:
- GET /sites/MLA/search sin credenciales devuelve 403.
- El listado web (listado.mercadolibre.com.ar) muestra un muro de login a tráfico
  no autenticado.
Conclusión: hace falta una app registrada en developers.mercadolibre.com.ar y un
access token (variable ML_ACCESS_TOKEN). Sin eso este adaptador falla de forma
explícita, y el harness registra el error en la traza en lugar de inventar un número.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .base import Adaptador, ErrorFuente

API = "https://api.mercadolibre.com"


class AdaptadorMercadoLibre(Adaptador):
    nombre = "mercadolibre_api"

    def __init__(self, token: str | None = None, sitio: str = "MLA", timeout: int = 15):
        self.token = token or os.environ.get("ML_ACCESS_TOKEN")
        self.sitio = sitio
        self.timeout = timeout

    def _get(self, ruta: str, params: dict) -> dict:
        if not self.token:
            raise ErrorFuente("sin_credenciales", "falta ML_ACCESS_TOKEN (la búsqueda pública devuelve 403)")
        url = f"{API}{ruta}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise ErrorFuente(f"http_{e.code}", e.reason) from e
        except urllib.error.URLError as e:
            raise ErrorFuente("red", str(e.reason)) from e

    def contar_oferta(self, producto: str) -> dict:
        datos = self._get(f"/sites/{self.sitio}/search", {"q": producto, "limit": 50})
        resultados = datos.get("results", [])
        vendedores = {r.get("seller", {}).get("id") for r in resultados if r.get("seller")}
        return {
            "publicaciones": datos.get("paging", {}).get("total", len(resultados)),
            "vendedores": len(vendedores),  # sobre los primeros 50: es una cota inferior
            "nota": "vendedores contados sobre los primeros 50 resultados",
            "fuente": self.nombre,
        }
