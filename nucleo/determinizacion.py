# nucleo/determinizacion.py
"""
Construcción de subconjuntos: AFN / AFN-ε -> AFD  (RF-06).

Operaciones:
  ε-cerradura(T): todos los estados alcanzables desde T usando solo ε
                  (incluye a T). Se calcula con una pila.
  mover(T, a):    estados alcanzables desde algún estado de T con una
                  transición etiquetada con a.

Algoritmo:
  1. S0 = ε-cerradura({inicial del AFN}); se marca como pendiente.
  2. Mientras haya un estado S pendiente, para cada símbolo a:
       U = ε-cerradura(mover(S, a))
       si U no existe todavía, se crea como estado nuevo (pendiente).
       Se agrega la transición S --a--> U.
  3. Un estado del AFD es final si contiene algún final del AFN.

Nombres: los estados nuevos se llaman S0, S1, ... en orden de descubrimiento
y en `correspondencia` se guarda qué estados del AFN contiene cada uno.
El conjunto vacío ∅ se conserva como un estado más (estado sumidero),
así el AFD resultante es completo.
"""

from __future__ import annotations

from collections import deque

from .automata import EPS, Automata, ordenar, texto_conjunto


def epsilon_cerradura(afn: Automata, conjunto: set[str]) -> frozenset[str]:
    resultado = set(conjunto)
    pila = list(conjunto)
    while pila:
        e = pila.pop()
        for d in afn.destinos(e, EPS):
            if d not in resultado:
                resultado.add(d)
                pila.append(d)
    return frozenset(resultado)


def mover(afn: Automata, conjunto, simbolo: str) -> set[str]:
    resultado: set[str] = set()
    for e in conjunto:
        resultado |= afn.destinos(e, simbolo)
    return resultado


def determinizar(afn: Automata) -> tuple[Automata, list[dict]]:
    pasos: list[dict] = []
    con_eps = afn.tiene_epsilon()

    nombres: dict[frozenset[str], str] = {}
    orden: list[frozenset[str]] = []

    def registrar(conj: frozenset[str]) -> str:
        if conj not in nombres:
            nombres[conj] = f"S{len(orden)}"
            orden.append(conj)
        return nombres[conj]

    s0 = epsilon_cerradura(afn, {afn.inicial})
    registrar(s0)
    if con_eps:
        pasos.append({"texto": f"S0 = ε-cerradura({{{afn.inicial}}}) = {texto_conjunto(s0)}", "nivel": "ok"})
    else:
        pasos.append({"texto": f"El AFN no tiene transiciones ε, así que la ε-cerradura de un conjunto es el mismo "
                               f"conjunto. S0 = {{{afn.inicial}}}", "nivel": "ok"})

    transiciones: dict[tuple[str, str], set[str]] = {}
    pendientes = deque([s0])
    filas = []
    while pendientes:
        actual = pendientes.popleft()
        nombre_actual = nombres[actual]
        detalle = []
        for a in afn.alfabeto:
            m = mover(afn, actual, a)
            u = epsilon_cerradura(afn, m)
            es_nuevo = u not in nombres
            nombre_u = registrar(u)
            if es_nuevo:
                pendientes.append(u)
            transiciones[(nombre_actual, a)] = {nombre_u}
            if con_eps:
                txt = f"mover({nombre_actual}, {a}) = {texto_conjunto(m)};  ε-cerradura = {texto_conjunto(u)}"
            else:
                txt = f"mover({nombre_actual}, {a}) = {texto_conjunto(u)}"
            txt += f"  →  {'NUEVO estado ' if es_nuevo else 'ya existe: '}{nombre_u}"
            detalle.append(txt)
            filas.append([nombre_actual, a, texto_conjunto(m), texto_conjunto(u), nombre_u + (" (nuevo)" if es_nuevo else "")])
        pasos.append({"texto": f"Se procesa {nombre_actual} = {texto_conjunto(actual)}", "detalle": detalle})

    estados = [nombres[c] for c in orden]
    finales = {nombres[c] for c in orden if c & afn.finales}
    correspondencia = {nombres[c]: ordenar(c) for c in orden}
    afd = Automata(estados, list(afn.alfabeto), "S0", finales, transiciones, correspondencia)

    pasos.append({
        "texto": "Resumen de la construcción de subconjuntos",
        "tabla": {
            "encabezados": ["Estado", "Símbolo", "mover", "ε-cerradura" if con_eps else "Destino", "Resultado"],
            "filas": filas,
        },
    })
    finales_txt = ", ".join(f"{n} {texto_conjunto(correspondencia[n])}" for n in ordenar(finales)) or "ninguno"
    pasos.append({
        "texto": f"Estados finales del AFD (contienen algún final del AFN {texto_conjunto(afn.finales)}): {finales_txt}.",
    })
    vacios = [nombres[c] for c in orden if not c]
    if vacios:
        pasos.append({"texto": f"{vacios[0]} = ∅ es el estado sumidero: una vez allí ninguna cadena puede aceptarse.",
                      "nivel": "aviso"})
    pasos.append({"texto": f"Resultado: AFD con {len(estados)} estados.", "nivel": "ok"})
    return afd, pasos
