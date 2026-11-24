# nucleo/entrada_automata.py
"""
Registro y validación manual de un autómata (Modalidad B, RF-04).

Formato documentado
-------------------
  Estados:          q0, q1, q2          (separados por comas o espacios)
  Alfabeto:         a, b                (un carácter por símbolo)
  Estado inicial:   q0
  Estados finales:  q2                  (puede quedar vacío)
  Transiciones:     una por línea
                        q0, a -> q1
                        q0, a -> q1, q2     (varios destinos = no determinismo)
                        q1, ε -> q2         (transición vacía; también vale "eps")
                    Se acepta → en lugar de ->, y las líneas que empiezan
                    con # se ignoran (comentarios).
"""

from __future__ import annotations

import re

from .automata import EPS, Automata
from .errores import ErrorEntrada
from .expresion import validar_alfabeto

_NOMBRE = re.compile(r"^[\w']+$")


def _lista(texto: str) -> list[str]:
    return [p for p in (texto or "").replace(",", " ").split() if p]


def validar_estados(texto: str) -> list[str]:
    estados = _lista(texto)
    if not estados:
        raise ErrorEntrada("Escribe al menos un estado, por ejemplo: q0, q1, q2", "estados")
    vistos = []
    for e in estados:
        if not _NOMBRE.match(e) or e.lower() == "eps":
            raise ErrorEntrada(f"«{e}» no es un nombre de estado válido. Usa letras, números o _ (por ejemplo q0, A, s_1).", "estados")
        if e in vistos:
            raise ErrorEntrada(f"El estado «{e}» está repetido.", "estados")
        vistos.append(e)
    return estados


def leer_automata(datos: dict) -> Automata:
    estados = validar_estados(datos.get("estados", ""))
    alfabeto = validar_alfabeto(datos.get("alfabeto", ""))
    conflicto = set(estados) & set(alfabeto)
    if conflicto:
        raise ErrorEntrada(f"«{conflicto.pop()}» se usa como estado y como símbolo; usa nombres distintos.", "estados")

    inicial = (datos.get("inicial") or "").strip()
    if not inicial:
        raise ErrorEntrada("Indica el estado inicial.", "inicial")
    if inicial not in estados:
        raise ErrorEntrada(f"El estado inicial «{inicial}» no está en la lista de estados.", "inicial")

    finales = _lista(datos.get("finales", ""))
    for f in finales:
        if f not in estados:
            raise ErrorEntrada(f"El estado final «{f}» no está en la lista de estados.", "finales")

    automata = Automata(estados, alfabeto, inicial, set(finales))
    lineas = (datos.get("transiciones") or "").splitlines()
    total = 0
    for n, linea in enumerate(lineas, 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        origen, simbolo, destinos = _leer_linea(linea, n)
        if origen not in estados:
            raise ErrorEntrada(f"Línea {n}: el estado de origen «{origen}» no existe.", "transiciones")
        if simbolo.lower() == "eps":
            simbolo = EPS
        if simbolo != EPS and simbolo not in alfabeto:
            raise ErrorEntrada(f"Línea {n}: el símbolo «{simbolo}» no pertenece al alfabeto {{{', '.join(alfabeto)}}}.", "transiciones")
        for d in destinos:
            if d not in estados:
                raise ErrorEntrada(f"Línea {n}: el estado destino «{d}» no existe.", "transiciones")
            automata.agregar_transicion(origen, simbolo, d)
            total += 1
    if total == 0:
        raise ErrorEntrada("No se registró ninguna transición. Escribe una por línea, por ejemplo: q0, a -> q1", "transiciones")
    return automata


def _leer_linea(linea: str, n: int) -> tuple[str, str, list[str]]:
    linea = linea.replace("→", "->")
    if "->" in linea:
        izquierda, derecha = linea.split("->", 1)
        partes_izq = _lista(izquierda)
        destinos = _lista(derecha)
        if len(partes_izq) != 2 or not destinos:
            raise ErrorEntrada(f"Línea {n}: «{linea}» no tiene el formato «origen, símbolo -> destino».", "transiciones")
        return partes_izq[0], partes_izq[1], destinos
    partes = _lista(linea)
    if len(partes) < 3:
        raise ErrorEntrada(f"Línea {n}: «{linea}» no tiene el formato «origen, símbolo -> destino».", "transiciones")
    return partes[0], partes[1], partes[2:]
