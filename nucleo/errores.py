# nucleo/errores.py
"""Excepción única para errores de entrada del usuario."""

from __future__ import annotations


class ErrorEntrada(Exception):
    """
    Error de validación de una entrada del usuario.

    `campo` indica qué campo del formulario originó el error, para que la
    interfaz pueda resaltarlo. `mensaje` debe explicar cómo corregirlo.
    """

    def __init__(self, mensaje: str, campo: str | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo

    def a_dict(self) -> dict:
        return {"error": self.mensaje, "campo": self.campo}
