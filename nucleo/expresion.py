# nucleo/expresion.py
"""
Validación del alfabeto y análisis de la expresión regular (Modalidad A).

Sintaxis documentada de la expresión regular
--------------------------------------------
    a        un símbolo del alfabeto (un solo carácter)
    ε        la cadena vacía
    r|s      unión (alternativa)
    rs       concatenación (implícita, se escriben uno tras otro)
    r*       cerradura de Kleene (cero o más)
    r+       cerradura positiva (una o más)
    r?       opcional (cero o una)
    (r)      agrupación

Precedencia (de mayor a menor): * + ?  >  concatenación  >  |
Los espacios se ignoran.

Símbolos reservados: no pueden formar parte del alfabeto.
"""

from __future__ import annotations

from .automata import EPS
from .errores import ErrorEntrada

OPERADORES = {"|", "*", "+", "?", "(", ")"}
RESERVADOS = OPERADORES | {EPS, ",", "·", "∅"}
CONCAT = "·"  # se usa solo para mostrar la concatenación explícita


# ---------------------------------------------------------------------- #
# Alfabeto (RF-01)
# ---------------------------------------------------------------------- #
def validar_alfabeto(texto: str, campo: str = "alfabeto") -> list[str]:
    """
    El alfabeto se escribe separado por comas o espacios: "a, b" o "0 1".
    Cada símbolo debe ser un único carácter no reservado y sin repetir.
    """
    if texto is None or not texto.strip():
        raise ErrorEntrada("El alfabeto está vacío. Escribe los símbolos separados por comas, por ejemplo: a, b", campo)
    partes = [p for p in texto.replace(",", " ").split() if p]
    simbolos: list[str] = []
    for p in partes:
        if len(p) != 1:
            raise ErrorEntrada(
                f"«{p}» tiene {len(p)} caracteres. Cada símbolo del alfabeto debe ser un solo carácter "
                "(sepáralos con comas: a, b, c).",
                campo,
            )
        if p in RESERVADOS:
            raise ErrorEntrada(
                f"«{p}» es un símbolo reservado y no puede estar en el alfabeto. "
                f"Reservados: {' '.join(sorted(RESERVADOS))}",
                campo,
            )
        if p in simbolos:
            raise ErrorEntrada(f"El símbolo «{p}» está repetido en el alfabeto.", campo)
        simbolos.append(p)
    return simbolos


# ---------------------------------------------------------------------- #
# Análisis léxico (RF-02)
# ---------------------------------------------------------------------- #
def tokenizar(expresion: str, alfabeto: list[str]) -> list[str]:
    if expresion is None or not expresion.strip():
        raise ErrorEntrada("La expresión regular está vacía. Usa ε si quieres representar la cadena vacía.", "expresion")
    tokens = []
    for i, c in enumerate(expresion):
        if c.isspace():
            continue
        if c in OPERADORES or c == EPS or c in alfabeto:
            tokens.append(c)
        else:
            raise ErrorEntrada(
                f"El símbolo «{c}» (posición {i + 1}) no pertenece al alfabeto {{{', '.join(alfabeto)}}} "
                "ni es un operador válido.",
                "expresion",
            )
    return tokens


def _es_operando_final(t: str) -> bool:
    """Tokens tras los cuales puede venir una concatenación implícita."""
    return t not in {"|", "("}


def _es_operando_inicial(t: str) -> bool:
    """Tokens antes de los cuales puede venir una concatenación implícita."""
    return t not in {"|", ")", "*", "+", "?"}


def concatenacion_explicita(tokens: list[str]) -> list[str]:
    """Inserta '·' donde hay concatenación implícita (solo para explicar)."""
    salida: list[str] = []
    for i, t in enumerate(tokens):
        salida.append(t)
        if i + 1 < len(tokens) and _es_operando_final(t) and _es_operando_inicial(tokens[i + 1]):
            salida.append(CONCAT)
    return salida


# ---------------------------------------------------------------------- #
# Análisis sintáctico: descenso recursivo -> árbol sintáctico
# ---------------------------------------------------------------------- #
#   union        := concatenacion ('|' concatenacion)*
#   concatenacion:= repeticion repeticion*
#   repeticion   := atomo ('*' | '+' | '?')*
#   atomo        := simbolo | 'ε' | '(' union ')'
#
# Nodos del árbol (tuplas):
#   ('sim', a)  ('eps',)  ('union', i, d)  ('concat', i, d)
#   ('estrella', r)  ('mas', r)  ('opc', r)

class _Parser:
    def __init__(self, tokens: list[str], alfabeto: list[str]):
        self.t = tokens
        self.i = 0
        self.alfabeto = alfabeto

    def ver(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def tomar(self):
        tok = self.ver()
        self.i += 1
        return tok

    def error(self, mensaje: str):
        if self.i >= len(self.t):
            donde = "al final de la expresión"
        else:
            donde = f"en el token {self.i + 1}: «{self.t[self.i]}»"
        raise ErrorEntrada(f"{mensaje} ({donde}).", "expresion")

    def analizar(self):
        arbol = self.union()
        if self.ver() is not None:
            if self.ver() == ")":
                self.error("Hay un paréntesis de cierre «)» sin su «(» correspondiente")
            self.error(f"No se esperaba «{self.ver()}» en este punto")
        return arbol

    def union(self):
        izq = self.concatenacion()
        while self.ver() == "|":
            self.tomar()
            der = self.concatenacion()
            izq = ("union", izq, der)
        return izq

    def concatenacion(self):
        tok = self.ver()
        if tok is None or tok in {"|", ")"}:
            if tok == "|" or (self.i > 0 and self.t[self.i - 1] == "|"):
                self.error("Falta un operando a un lado del operador «|»")
            if tok == ")" and self.i > 0 and self.t[self.i - 1] == "(":
                self.error("Los paréntesis «()» están vacíos; usa (ε) si quieres la cadena vacía")
            self.error("Falta un operando")
        izq = self.repeticion()
        while self.ver() is not None and self.ver() not in {"|", ")"}:
            der = self.repeticion()
            izq = ("concat", izq, der)
        return izq

    def repeticion(self):
        nodo = self.atomo()
        while self.ver() in {"*", "+", "?"}:
            op = self.tomar()
            nodo = ({"*": "estrella", "+": "mas", "?": "opc"}[op], nodo)
        return nodo

    def atomo(self):
        tok = self.ver()
        if tok in {"*", "+", "?"}:
            self.error(f"El operador «{tok}» debe ir después de un símbolo o de un grupo entre paréntesis")
        if tok == "(":
            self.tomar()
            nodo = self.union()
            if self.ver() != ")":
                self.error("Falta cerrar un paréntesis «)»")
            self.tomar()
            return nodo
        if tok == EPS:
            self.tomar()
            return ("eps",)
        if tok in self.alfabeto:
            self.tomar()
            return ("sim", tok)
        self.error(f"No se esperaba «{tok}»")


def analizar(tokens: list[str], alfabeto: list[str]):
    return _Parser(tokens, alfabeto).analizar()


# ---------------------------------------------------------------------- #
# Utilidades de presentación
# ---------------------------------------------------------------------- #
_PRECEDENCIA = {"union": 1, "concat": 2, "estrella": 3, "mas": 3, "opc": 3, "sim": 4, "eps": 4}


def a_texto(nodo, padre: int = 0) -> str:
    """Reconstruye la subexpresión de un nodo con los paréntesis mínimos."""
    tipo = nodo[0]
    p = _PRECEDENCIA[tipo]
    if tipo == "sim":
        s = nodo[1]
    elif tipo == "eps":
        s = EPS
    elif tipo == "union":
        s = a_texto(nodo[1], p) + "|" + a_texto(nodo[2], p + 1)
    elif tipo == "concat":
        s = a_texto(nodo[1], p) + a_texto(nodo[2], p + 1)
    else:
        s = a_texto(nodo[1], p + 1) + {"estrella": "*", "mas": "+", "opc": "?"}[tipo]
    return f"({s})" if p < padre else s


def a_postfija(nodo) -> list[str]:
    tipo = nodo[0]
    if tipo == "sim":
        return [nodo[1]]
    if tipo == "eps":
        return [EPS]
    if tipo in {"union", "concat"}:
        op = "|" if tipo == "union" else CONCAT
        return a_postfija(nodo[1]) + a_postfija(nodo[2]) + [op]
    return a_postfija(nodo[1]) + [{"estrella": "*", "mas": "+", "opc": "?"}[tipo]]


def a_arbol_texto(nodo, prefijo: str = "", ultimo: bool = True, raiz: bool = True) -> list[str]:
    """Árbol sintáctico dibujado con caracteres, para la explicación."""
    nombres = {"union": "| (unión)", "concat": "· (concatenación)", "estrella": "* (Kleene)",
               "mas": "+ (positiva)", "opc": "? (opcional)", "eps": "ε"}
    etiqueta = nodo[1] if nodo[0] == "sim" else nombres[nodo[0]]
    conector = "" if raiz else ("└── " if ultimo else "├── ")
    lineas = [prefijo + conector + etiqueta]
    hijos = [h for h in nodo[1:] if isinstance(h, tuple)]
    nuevo_prefijo = prefijo + ("" if raiz else ("    " if ultimo else "│   "))
    for k, h in enumerate(hijos):
        lineas += a_arbol_texto(h, nuevo_prefijo, k == len(hijos) - 1, False)
    return lineas
