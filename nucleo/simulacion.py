# nucleo/simulacion.py
"""
Simulación de cadenas (RF-12).

- En un AFD se sigue un único camino: δ(q, a) para cada símbolo.
- En un AFN / AFN-ε se sigue el CONJUNTO de estados activos:
      activos = ε-cerradura(mover(activos, a))
  La cadena se acepta si al final algún estado activo es final.
"""

from __future__ import annotations

from .automata import Automata, texto_conjunto
from .determinizacion import epsilon_cerradura, mover
from .errores import ErrorEntrada


def _validar_cadena(automata: Automata, cadena: str) -> list[str]:
    cadena = cadena.replace(" ", "")
    if cadena in {"ε", ""}:
        return []
    for i, c in enumerate(cadena):
        if c not in automata.alfabeto:
            raise ErrorEntrada(
                f"El símbolo «{c}» (posición {i + 1}) no pertenece al alfabeto {{{', '.join(automata.alfabeto)}}}.",
                "cadena",
            )
    return list(cadena)


def simular(automata: Automata, cadena: str) -> dict:
    simbolos = _validar_cadena(automata, cadena)
    if automata.es_determinista():
        return _simular_afd(automata, simbolos)
    return _simular_afn(automata, simbolos)


def _simular_afd(afd: Automata, simbolos: list[str]) -> dict:
    actual = afd.inicial
    recorrido = [actual]
    pasos = []
    for k, a in enumerate(simbolos, 1):
        ds = afd.destinos(actual, a)
        if not ds:
            pasos.append({"paso": k, "desde": actual, "simbolo": a, "hacia": "—",
                          "nota": f"δ({actual}, {a}) no está definida: la cadena se rechaza."})
            return _resultado(afd, simbolos, pasos, recorrido, False, f"Rechazada: no hay transición desde {actual} con «{a}».", {actual})
        siguiente = next(iter(ds))
        pasos.append({"paso": k, "desde": actual, "simbolo": a, "hacia": siguiente, "nota": f"δ({actual}, {a}) = {siguiente}"})
        actual = siguiente
        recorrido.append(actual)
    acepta = actual in afd.finales
    motivo = (f"Aceptada: termina en {actual}, que es final." if acepta
              else f"Rechazada: termina en {actual}, que no es final.")
    return _resultado(afd, simbolos, pasos, recorrido, acepta, motivo, {actual})


def _simular_afn(afn: Automata, simbolos: list[str]) -> dict:
    activos = epsilon_cerradura(afn, {afn.inicial})
    pasos = [{"paso": 0, "desde": "", "simbolo": "", "hacia": texto_conjunto(activos),
              "nota": f"Estados activos iniciales = ε-cerradura({{{afn.inicial}}})"}]
    for k, a in enumerate(simbolos, 1):
        m = mover(afn, activos, a)
        nuevos = epsilon_cerradura(afn, m)
        pasos.append({"paso": k, "desde": texto_conjunto(activos), "simbolo": a, "hacia": texto_conjunto(nuevos),
                      "nota": f"mover = {texto_conjunto(m)}; ε-cerradura = {texto_conjunto(nuevos)}"})
        activos = nuevos
        if not activos:
            break
    finales_activos = activos & afn.finales
    acepta = bool(finales_activos) and len(pasos) == len(simbolos) + 1
    if acepta:
        motivo = f"Aceptada: entre los estados activos {texto_conjunto(activos)} hay finales: {texto_conjunto(finales_activos)}."
    elif not activos:
        motivo = "Rechazada: el conjunto de estados activos quedó vacío."
    else:
        motivo = f"Rechazada: ningún estado activo {texto_conjunto(activos)} es final."
    return _resultado(afn, simbolos, pasos, None, acepta, motivo, set(activos))


def _resultado(aut, simbolos, pasos, recorrido, acepta, motivo, resaltar) -> dict:
    color = "#86efac" if acepta else "#fca5a5"
    return {
        "cadena": "".join(simbolos) or "ε",
        "modo": "AFD" if recorrido is not None else "AFN",
        "pasos": pasos,
        "recorrido": recorrido,
        "acepta": acepta,
        "motivo": motivo,
        "dot": aut.dot(resaltar=resaltar, color_resaltado=color),
    }
