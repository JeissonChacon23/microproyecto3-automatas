# nucleo/__init__.py
"""
Núcleo algorítmico del software educativo de autómatas finitos.

Todos los algoritmos (análisis de la expresión regular, construcción de
Thompson, construcción de subconjuntos, eliminación de inaccesibles,
minimización por refinamiento de particiones y simulación) están
implementados a mano en este paquete, sin bibliotecas de autómatas.
"""

from .errores import ErrorEntrada
from .automata import Automata, EPS

__all__ = ["ErrorEntrada", "Automata", "EPS"]
