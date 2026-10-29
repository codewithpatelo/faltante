"""Adaptador sobre datos sintéticos, para probar el harness sin red."""

from __future__ import annotations

import difflib
import json
import unicodedata
from pathlib import Path

from .base import Adaptador, ErrorFuente


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


class AdaptadorFixtures(Adaptador):
    nombre = "fixtures_sintetico"

    def __init__(self, ruta: str | Path):
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        self.productos = datos["productos"]
        # índice nombre/alias normalizado -> nombre canónico
        self.indice: dict[str, str] = {}
        for canon, d in self.productos.items():
            self.indice[_norm(canon)] = canon
            for a in d.get("alias", []):
                self.indice[_norm(a)] = canon

    def _resolver(self, producto: str) -> str:
        """Busca el producto. Coincidencia exacta o difusa alta; si no, error.

        Esto es deliberadamente estricto: resolver nombres informales ('nut milk maker')
        a un producto canónico es trabajo semántico, y es justo lo que se espera del LLM,
        no de una búsqueda por cadenas.
        """
        n = _norm(producto)
        if n in self.indice:
            return self.indice[n]
        cerca = difflib.get_close_matches(n, list(self.indice), n=1, cutoff=0.82)
        if cerca:
            return self.indice[cerca[0]]
        raise ErrorFuente("no_encontrado", f"sin resultados para '{producto}'")

    def _get(self, skill: str, producto: str) -> dict:
        canon = self._resolver(producto)
        out = dict(self.productos[canon][skill])
        out["producto_resuelto"] = canon
        out["fuente"] = self.nombre
        return out

    def contar_oferta(self, producto):
        return self._get("contar_oferta", producto)

    def ratio_precio(self, producto):
        return self._get("ratio_precio", producto)

    def persistencia(self, producto):
        return self._get("persistencia", producto)

    def voto_manos(self, producto):
        return self._get("voto_manos", producto)

    def viabilidad(self, producto):
        return self._get("viabilidad", producto)
