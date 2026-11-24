# nucleo/automata.py
"""
Estructura de datos para representar autómatas finitos (AFD, AFN y AFN-ε).

Representación elegida
----------------------
- estados:       lista ordenada de nombres (str). El orden se conserva para
                 que las tablas salgan siempre igual.
- alfabeto:      lista ordenada de símbolos (str de un carácter).
- inicial:       nombre del estado inicial.
- finales:       conjunto (set) de estados de aceptación.
- transiciones:  diccionario {(estado, símbolo): set(destinos)}.
                 El símbolo EPS ('ε') representa una transición vacía.
                 Usar conjuntos como destino permite representar AFN; un AFD
                 es el caso particular en que cada conjunto tiene 1 elemento.
- correspondencia: diccionario opcional {estado_nuevo: [estados_originales]}
                 que conserva la relación entre los estados creados por un
                 algoritmo (subconjuntos o minimización) y los de la etapa
                 anterior.
"""

from __future__ import annotations

import re
from collections import deque

EPS = "ε"


def clave_natural(nombre: str):
    """Orden 'natural': q2 va antes que q10."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", nombre)]


def ordenar(estados) -> list[str]:
    return sorted(estados, key=clave_natural)


def texto_conjunto(estados) -> str:
    """{q0, q1, q2} o ∅ si está vacío."""
    estados = ordenar(estados)
    return "{" + ", ".join(estados) + "}" if estados else "∅"


class Automata:
    def __init__(
        self,
        estados: list[str],
        alfabeto: list[str],
        inicial: str,
        finales: set[str],
        transiciones: dict[tuple[str, str], set[str]] | None = None,
        correspondencia: dict[str, list[str]] | None = None,
    ):
        self.estados = list(estados)
        self.alfabeto = list(alfabeto)
        self.inicial = inicial
        self.finales = set(finales)
        self.transiciones: dict[tuple[str, str], set[str]] = {}
        for (origen, simbolo), destinos in (transiciones or {}).items():
            if destinos:
                self.transiciones[(origen, simbolo)] = set(destinos)
        self.correspondencia = correspondencia

    # ------------------------------------------------------------------ #
    # Operaciones básicas
    # ------------------------------------------------------------------ #
    def agregar_transicion(self, origen: str, simbolo: str, destino: str) -> None:
        self.transiciones.setdefault((origen, simbolo), set()).add(destino)

    def destinos(self, estado: str, simbolo: str) -> set[str]:
        return self.transiciones.get((estado, simbolo), set())

    def tiene_epsilon(self) -> bool:
        return any(s == EPS for (_, s) in self.transiciones)

    def transiciones_epsilon(self) -> list[tuple[str, str]]:
        return [
            (o, d)
            for (o, s), ds in self.transiciones.items()
            if s == EPS
            for d in ordenar(ds)
        ]

    def pares_no_deterministas(self) -> list[tuple[str, str, set[str]]]:
        """(estado, símbolo, destinos) con más de un destino."""
        return [
            (o, s, ds)
            for (o, s), ds in self.transiciones.items()
            if s != EPS and len(ds) > 1
        ]

    def pares_faltantes(self) -> list[tuple[str, str]]:
        """(estado, símbolo) sin ninguna transición definida."""
        return [
            (e, a)
            for e in self.estados
            for a in self.alfabeto
            if not self.destinos(e, a)
        ]

    def es_determinista(self) -> bool:
        return not self.tiene_epsilon() and not self.pares_no_deterministas()

    def es_completo(self) -> bool:
        return not self.pares_faltantes()

    def tipo(self) -> str:
        if self.tiene_epsilon():
            return "AFN-ε"
        if self.pares_no_deterministas():
            return "AFN"
        return "AFD" if self.es_completo() else "AFD (incompleto)"

    def alcanzables(self) -> list[str]:
        """Estados alcanzables desde el inicial (recorrido en anchura)."""
        vistos = {self.inicial}
        cola = deque([self.inicial])
        orden = [self.inicial]
        simbolos = self.alfabeto + ([EPS] if self.tiene_epsilon() else [])
        while cola:
            actual = cola.popleft()
            for s in simbolos:
                for d in ordenar(self.destinos(actual, s)):
                    if d not in vistos:
                        vistos.add(d)
                        orden.append(d)
                        cola.append(d)
        return orden

    # ------------------------------------------------------------------ #
    # Representaciones para la interfaz
    # ------------------------------------------------------------------ #
    def tabla(self) -> dict:
        """Tabla de transición lista para dibujar en HTML."""
        simbolos = self.alfabeto + ([EPS] if self.tiene_epsilon() else [])
        determinista = self.es_determinista()
        encabezados = ["Estado"] + simbolos
        if self.correspondencia is not None:
            encabezados.append("Corresponde a")
        filas = []
        for e in self.estados:
            marca = ("→" if e == self.inicial else "") + ("*" if e in self.finales else "")
            celdas = []
            for s in simbolos:
                ds = self.destinos(e, s)
                if not ds:
                    celdas.append("—")
                elif determinista:
                    celdas.append(next(iter(ds)))
                else:
                    celdas.append(texto_conjunto(ds))
            fila = {"marca": marca, "estado": e, "celdas": celdas}
            if self.correspondencia is not None:
                fila["corresponde"] = texto_conjunto(self.correspondencia.get(e, []))
            filas.append(fila)
        return {"encabezados": encabezados, "filas": filas}

    def dot(self, resaltar: set[str] | None = None, color_resaltado: str = "#f59e0b") -> str:
        """
        Código DOT (Graphviz) del diagrama de transición.
        Graphviz solo se usa para DIBUJAR; no participa en ningún algoritmo.
        """
        resaltar = resaltar or set()

        def q(nombre: str) -> str:
            return '"' + nombre.replace('"', '\\"') + '"'

        lineas = [
            "digraph AF {",
            '  rankdir=LR; bgcolor="transparent";',
            '  node [shape=circle, fontname="Helvetica", fontsize=13, '
            'style=filled, fillcolor="#ffffff", color="#334155", penwidth=1.4];',
            '  edge [fontname="Helvetica", fontsize=12, color="#475569", arrowsize=0.8];',
            '  __inicio [shape=point, width=0.08, color="#0f172a"];',
        ]
        for e in self.estados:
            atributos = []
            if e in self.finales:
                atributos.append("shape=doublecircle")
            if e in resaltar:
                atributos.append(f'fillcolor="{color_resaltado}"')
            lineas.append(f"  {q(e)}" + (f" [{', '.join(atributos)}]" if atributos else "") + ";")
        lineas.append(f"  __inicio -> {q(self.inicial)};")

        # Se agrupan las aristas paralelas: q0 -a,b-> q1
        etiquetas: dict[tuple[str, str], list[str]] = {}
        simbolos = self.alfabeto + [EPS]
        for e in self.estados:
            for s in simbolos:
                for d in ordenar(self.destinos(e, s)):
                    etiquetas.setdefault((e, d), []).append(s)
        for (o, d), ss in etiquetas.items():
            etiqueta = ", ".join(ss).replace('"', '\\"')
            lineas.append(f'  {q(o)} -> {q(d)} [label="{etiqueta}"];')
        lineas.append("}")
        return "\n".join(lineas)

    def a_dict(self) -> dict:
        """Serialización completa (para la interfaz y para re-simular)."""
        return {
            "tipo": self.tipo(),
            "estados": self.estados,
            "alfabeto": self.alfabeto,
            "inicial": self.inicial,
            "finales": ordenar(self.finales),
            "transiciones": [
                {"origen": o, "simbolo": s, "destinos": ordenar(ds)}
                for (o, s), ds in self.transiciones.items()
            ],
            "correspondencia": self.correspondencia,
            "tabla": self.tabla(),
            "dot": self.dot(),
            "num_estados": len(self.estados),
            "num_transiciones": sum(len(ds) for ds in self.transiciones.values()),
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Automata":
        trans: dict[tuple[str, str], set[str]] = {}
        for t in datos["transiciones"]:
            trans[(t["origen"], t["simbolo"])] = set(t["destinos"])
        return cls(
            datos["estados"],
            datos["alfabeto"],
            datos["inicial"],
            set(datos["finales"]),
            trans,
            datos.get("correspondencia"),
        )
