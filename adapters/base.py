"""Contrato común de las fuentes de datos.

Cada skill que toca datos se resuelve en un adaptador. El harness no sabe de dónde
salen los números: solo habla con esta interfaz. Por eso se puede correr el mismo
agente sobre datos sintéticos, sobre una caché grabada o contra las APIs en vivo.
"""

from __future__ import annotations


class ErrorFuente(Exception):
    """La fuente no pudo responder (sin credenciales, 403, producto no encontrado...)."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(f"{codigo}: {detalle}")
        self.codigo = codigo
        self.detalle = detalle


class Adaptador:
    nombre = "base"

    def contar_oferta(self, producto: str) -> dict:
        raise ErrorFuente("no_implementado", "contar_oferta no disponible en esta fuente")

    def ratio_precio(self, producto: str) -> dict:
        raise ErrorFuente("no_implementado", "ratio_precio no disponible en esta fuente")

    def persistencia(self, producto: str) -> dict:
        raise ErrorFuente("no_implementado", "persistencia no disponible en esta fuente")

    def voto_manos(self, producto: str) -> dict:
        raise ErrorFuente("no_implementado", "voto_manos no disponible en esta fuente")

    def viabilidad(self, producto: str) -> dict:
        raise ErrorFuente("no_implementado", "viabilidad no disponible en esta fuente")
