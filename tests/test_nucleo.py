# tests/test_nucleo.py
"""
Pruebas automáticas del núcleo. Ejecutar con:  python -m pytest -q

Además de casos resueltos a mano, se verifica la EQUIVALENCIA: para muchas
expresiones aleatorias, el AFD mínimo acepta exactamente las mismas cadenas
que el módulo `re` de Python (que se usa solo como juez, nunca en la app).
"""

import itertools
import random
import re as re_python

import pytest

from nucleo.automata import Automata
from nucleo.errores import ErrorEntrada
from nucleo.procesos import proceso_automata, proceso_expresion
from nucleo.simulacion import simular


def automata_de(resultado, etapa):
    datos = next(e for e in resultado["etapas"] if e["id"] == etapa)["automata"]
    return Automata.desde_dict(datos)


def cadenas(alfabeto, max_len):
    for n in range(max_len + 1):
        for t in itertools.product(alfabeto, repeat=n):
            yield "".join(t)


def acepta(aut, cadena):
    return simular(aut, cadena)["acepta"]


def es_minimo(afd: Automata) -> bool:
    """Fuerza bruta: todo par de estados se distingue con alguna cadena corta."""
    n = len(afd.estados)

    def final_desde(q, w):
        for c in w:
            q = next(iter(afd.destinos(q, c)))
        return q in afd.finales

    palabras = list(cadenas(afd.alfabeto, max(n - 1, 0)))
    firmas = {tuple(final_desde(q, w) for w in palabras) for q in afd.estados}
    return len(firmas) == n


# ---------------------------------------------------------------------- #
# Casos resueltos a mano
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize("alfabeto, expresion, minimos", [
    ("a,b", "(a|b)*abb", 4),   # ejemplo clásico del libro del Dragón
    ("a,b", "ab", 4),          # q0 -a-> q1 -b-> q2 + sumidero
    ("a", "a*", 1),
    ("a,b", "a*", 2),          # a* + sumidero
    ("a", "ε", 2),
    ("0,1", "(0|1)*1(0|1)", 4),
    ("a,b", "(a|b)*", 1),
    ("a,b", "a+b?", 4),
])
def test_estados_minimos(alfabeto, expresion, minimos):
    r = proceso_expresion(alfabeto, expresion)
    minimo = automata_de(r, "minimo")
    assert len(minimo.estados) == minimos
    assert minimo.es_determinista() and minimo.es_completo()
    assert es_minimo(minimo)


def test_dragon_tabla_subconjuntos():
    r = proceso_expresion("a,b", "(a|b)*abb")
    afd = automata_de(r, "afd")
    assert len(afd.estados) == 5            # A, B, C, D, E del libro
    assert automata_de(r, "thompson").tipo() == "AFN-ε"


def test_modalidad_b_afd_incompleto_con_inaccesible():
    datos = {"estados": "q0,q1,q2,q3,q4", "alfabeto": "0,1", "inicial": "q0", "finales": "q2",
             "transiciones": "q0,0->q1\nq0,1->q3\nq1,0->q2\nq3,0->q2\nq4,1->q0"}
    r = proceso_automata(datos)
    assert r["tipo_original"] == "AFD (incompleto)"
    acc = automata_de(r, "inaccesibles")
    assert "q4" not in acc.estados
    minimo = automata_de(r, "minimo")
    assert len(minimo.estados) == 4         # {q0}, {q1,q3}, {q2}, sumidero
    assert es_minimo(minimo)
    for w in cadenas("01", 5):
        assert acepta(minimo, w) == (w in {"00", "10"})


def test_modalidad_b_afn():
    datos = {"estados": "p q r", "alfabeto": "a b", "inicial": "p", "finales": "r",
             "transiciones": "p, a -> p, q\np, b -> p\nq, b -> r"}
    r = proceso_automata(datos)
    assert r["tipo_original"] == "AFN"
    original = automata_de(r, "entrada")
    minimo = automata_de(r, "minimo")
    for w in cadenas("ab", 7):
        assert acepta(original, w) == acepta(minimo, w) == w.endswith("ab")


def test_afd_ya_minimo_no_cambia():
    datos = {"estados": "A B", "alfabeto": "0 1", "inicial": "A", "finales": "B",
             "transiciones": "A,0->A\nA,1->B\nB,0->A\nB,1->B"}
    r = proceso_automata(datos)
    assert r["tipo_original"] == "AFD"
    assert len(automata_de(r, "minimo").estados) == 2


# ---------------------------------------------------------------------- #
# Equivalencia con expresiones aleatorias
# ---------------------------------------------------------------------- #
def expresion_aleatoria(rng, alfabeto, profundidad):
    if profundidad == 0 or rng.random() < 0.25:
        return rng.choice(alfabeto + ["ε"]) if rng.random() < 0.9 else "ε"
    op = rng.choice(["|", "·", "*", "+", "?"])
    if op in "|·":
        i = expresion_aleatoria(rng, alfabeto, profundidad - 1)
        d = expresion_aleatoria(rng, alfabeto, profundidad - 1)
        return f"({i}|{d})" if op == "|" else f"({i})({d})"
    return f"({expresion_aleatoria(rng, alfabeto, profundidad - 1)}){op}"


def test_equivalencia_aleatoria_con_re():
    rng = random.Random(2026)
    for _ in range(250):
        alfabeto = rng.choice([["a", "b"], ["0", "1"], ["a", "b", "c"]])
        expr = expresion_aleatoria(rng, alfabeto, 4)
        r = proceso_expresion(",".join(alfabeto), expr)
        etapas = {e: automata_de(r, e) for e in ("thompson", "afd", "minimo")}
        patron = re_python.compile(expr.replace("ε", "(?:)"))
        for w in cadenas(alfabeto, 5 if len(alfabeto) == 2 else 4):
            esperado = patron.fullmatch(w) is not None
            for nombre, aut in etapas.items():
                assert acepta(aut, w) == esperado, (expr, w, nombre)
        assert es_minimo(etapas["minimo"]), expr


# ---------------------------------------------------------------------- #
# Validaciones y mensajes de error
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize("alfabeto", ["", "a,a", "ab", "a,|", "a,ε"])
def test_alfabeto_invalido(alfabeto):
    with pytest.raises(ErrorEntrada):
        proceso_expresion(alfabeto, "a")


@pytest.mark.parametrize("expresion", ["", "a|", "|a", "()", "(a", "a)", "*a", "a+c", "(a|)"])
def test_expresion_invalida(expresion):
    with pytest.raises(ErrorEntrada) as e:
        proceso_expresion("a,b", expresion)
    assert e.value.campo == "expresion"


@pytest.mark.parametrize("cambio, campo", [
    ({"inicial": "z"}, "inicial"),
    ({"finales": "q9"}, "finales"),
    ({"transiciones": "q0, c -> q1"}, "transiciones"),
    ({"transiciones": "q0, a -> q7"}, "transiciones"),
    ({"transiciones": "q0 a"}, "transiciones"),
    ({"estados": "q0, q0"}, "estados"),
])
def test_automata_invalido(cambio, campo):
    datos = {"estados": "q0 q1", "alfabeto": "a b", "inicial": "q0", "finales": "q1",
             "transiciones": "q0, a -> q1"}
    datos.update(cambio)
    with pytest.raises(ErrorEntrada) as e:
        proceso_automata(datos)
    assert e.value.campo == campo
