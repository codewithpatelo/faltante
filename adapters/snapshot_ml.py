"""Adaptador sobre una foto de búsquedas de Mercado Libre capturada desde el navegador.

Cada publicación ya viene marcada como "es el producto" o no, según el emparejamiento.
Los cuatro chequeos de diagnóstico se exponen como skills.
"""

from __future__ import annotations

import json
from pathlib import Path

from harness.diagnostico import CHEQUEOS, Foto, Publicacion, _resumen

from .base import Adaptador, ErrorFuente


class AdaptadorSnapshotML(Adaptador):
    nombre = "snapshot_ml"

    def __init__(self, ruta: str | Path):
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        self.fotos = {
            b: Foto(b, [Publicacion(p["titulo"], bool(p["internacional"]), p["vendidos"], p["precio"], bool(p["es_producto"]))
                        for p in d["publicaciones"]])
            for b, d in datos["busquedas"].items()
        }

    def _chequeo(self, nombre: str, producto: str) -> dict:
        foto = self.fotos.get(producto)
        if foto is None:
            raise ErrorFuente("no_encontrado", f"no hay foto de la búsqueda '{producto}'")
        r = _resumen(foto)
        return {**CHEQUEOS[nombre](r), "resumen": r, "fuente": self.nombre}

    def chequear_demanda(self, producto):
        return self._chequeo("demanda", producto)

    def chequear_precio(self, producto):
        return self._chequeo("precio", producto)

    def chequear_espera(self, producto):
        return self._chequeo("espera", producto)

    def chequear_preferencia_local(self, producto):
        return self._chequeo("preferencia_local", producto)
