# nucleo/thompson.py
"""
Construcción de Thompson: expresión regular -> AFN-ε  (RF-03).

Cada subexpresión produce un "fragmento" con exactamente un estado inicial
y un estado final. Los fragmentos se combinan recorriendo el árbol
sintáctico en postorden (primero los hijos, luego el operador):

  símbolo a :  i --a--> f
  ε         :  i --ε--> f
  r s       :  final(r) --ε--> inicio(s)
  r | s     :  i --ε--> inicio(r), i --ε--> inicio(s),
               final(r) --ε--> f,  final(s) --ε--> f
  r*        :  i --ε--> inicio(r), i --ε--> f,
               final(r) --ε--> inicio(r), final(r) --ε--> f
  r+        :  igual que r* pero SIN i --ε--> f   (al menos una vez)
  r?        :  i --ε--> inicio(r), i --ε--> f, final(r) --ε--> f

Los estados se nombran q0, q1, q2, ... en el orden en que se crean.
"""

from __future__ import annotations

from .automata import EPS, Automata
from .expresion import a_texto


def construir(arbol, alfabeto: list[str]) -> tuple[Automata, list[dict]]:
    estados: list[str] = []
    transiciones: dict[tuple[str, str], set[str]] = {}
    pasos: list[dict] = []

    def nuevo() -> str:
        nombre = f"q{len(estados)}"
        estados.append(nombre)
        return nombre

    def arista(o: str, s: str, d: str) -> str:
        transiciones.setdefault((o, s), set()).add(d)
        return f"{o} —{s}→ {d}"

    def visitar(nodo) -> tuple[str, str]:
        tipo = nodo[0]
        sub = a_texto(nodo)

        if tipo in {"sim", "eps"}:
            s = nodo[1] if tipo == "sim" else EPS
            i, f = nuevo(), nuevo()
            a = arista(i, s, f)
            regla = "Símbolo" if tipo == "sim" else "Cadena vacía"
            pasos.append(_paso(regla, sub, [a], i, f))
            return i, f

        if tipo == "concat":
            i1, f1 = visitar(nodo[1])
            i2, f2 = visitar(nodo[2])
            a = arista(f1, EPS, i2)
            pasos.append(_paso("Concatenación", sub, [a], i1, f2,
                               f"Se une el final de «{a_texto(nodo[1])}» con el inicio de «{a_texto(nodo[2])}»."))
            return i1, f2

        if tipo == "union":
            i1, f1 = visitar(nodo[1])
            i2, f2 = visitar(nodo[2])
            i, f = nuevo(), nuevo()
            aristas = [arista(i, EPS, i1), arista(i, EPS, i2), arista(f1, EPS, f), arista(f2, EPS, f)]
            pasos.append(_paso("Unión", sub, aristas, i, f,
                               "Nuevo inicio que se bifurca con ε a ambas alternativas y nuevo final común."))
            return i, f

        # Operadores unarios
        i1, f1 = visitar(nodo[1])
        i, f = nuevo(), nuevo()
        if tipo == "estrella":
            aristas = [arista(i, EPS, i1), arista(i, EPS, f), arista(f1, EPS, i1), arista(f1, EPS, f)]
            regla, nota = "Cerradura de Kleene", "Permite saltarse r (cero veces) o repetirla volviendo a su inicio."
        elif tipo == "mas":
            aristas = [arista(i, EPS, i1), arista(f1, EPS, i1), arista(f1, EPS, f)]
            regla, nota = "Cerradura positiva", "Como r* pero obliga a recorrer r al menos una vez (sin ε de i a f)."
        else:  # opc
            aristas = [arista(i, EPS, i1), arista(i, EPS, f), arista(f1, EPS, f)]
            regla, nota = "Opcional", "Permite recorrer r una vez o saltarla con ε."
        pasos.append(_paso(regla, sub, aristas, i, f, nota))
        return i, f

    inicial, final = visitar(arbol)
    afn = Automata(estados, alfabeto, inicial, {final}, transiciones)
    pasos.append({
        "texto": f"Resultado: AFN-ε con {len(estados)} estados. Estado inicial {inicial}, estado final {final}.",
        "nivel": "ok",
    })
    return afn, pasos


def _paso(regla: str, sub: str, aristas: list[str], i: str, f: str, nota: str | None = None) -> dict:
    texto = f"{regla} — «{sub}»: inicio {i}, final {f}."
    if nota:
        texto += " " + nota
    return {"texto": texto, "detalle": aristas}
