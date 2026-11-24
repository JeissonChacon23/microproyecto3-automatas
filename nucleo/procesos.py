# nucleo/procesos.py
"""
Orquestación de las dos modalidades. Cada proceso devuelve una lista de
"etapas"; cada etapa guarda su explicación paso a paso y el autómata que
produjo, para poder consultarla y compararla con el resultado final (RF-10,
RF-13).
"""

from __future__ import annotations

from .automata import EPS, Automata, texto_conjunto
from .determinizacion import determinizar
from .entrada_automata import leer_automata
from .expresion import (CONCAT, a_arbol_texto, a_postfija, analizar, concatenacion_explicita,
                        tokenizar, validar_alfabeto)
from .minimizacion import completar, eliminar_inaccesibles, minimizar
from .thompson import construir


def _etapa(id_: str, titulo: str, resumen: str, pasos: list[dict], automata: Automata | None = None) -> dict:
    return {
        "id": id_,
        "titulo": titulo,
        "resumen": resumen,
        "pasos": pasos,
        "automata": automata.a_dict() if automata else None,
    }


def _etapas_finales(afd: Automata) -> list[dict]:
    """Inaccesibles + completar + minimizar (comunes a ambas modalidades)."""
    etapas = []
    accesible, pasos_acc = eliminar_inaccesibles(afd)
    completo, pasos_comp = completar(accesible)
    etapas.append(_etapa(
        "inaccesibles", "Estados inaccesibles",
        "Se eliminan los estados a los que no se llega desde el inicial"
        + (" y se completa la función de transición." if pasos_comp else "."),
        pasos_acc + pasos_comp, completo,
    ))
    minimo, pasos_min = minimizar(completo)
    etapas.append(_etapa(
        "minimo", "AFD mínimo",
        "Refinamiento de particiones (Moore): se agrupan los estados indistinguibles.",
        pasos_min, minimo,
    ))
    return etapas


# ---------------------------------------------------------------------- #
# Modalidad A: alfabeto + expresión regular
# ---------------------------------------------------------------------- #
def proceso_expresion(alfabeto_txt: str, expresion: str) -> dict:
    alfabeto = validar_alfabeto(alfabeto_txt)
    tokens = tokenizar(expresion, alfabeto)
    arbol = analizar(tokens, alfabeto)

    pasos_entrada = [
        {"texto": f"Alfabeto válido Σ = {{{', '.join(alfabeto)}}} ({len(alfabeto)} símbolos, sin repetidos ni reservados).", "nivel": "ok"},
        {"texto": "Todos los símbolos de la expresión pertenecen al alfabeto o son operadores.", "nivel": "ok",
         "detalle": ["Tokens: " + "  ".join(tokens)]},
        {"texto": f"Concatenación explícita (se marca con {CONCAT}):",
         "detalle": [" ".join(concatenacion_explicita(tokens))]},
        {"texto": "Notación postfija (orden en que se aplican los operadores):",
         "detalle": [" ".join(a_postfija(arbol))]},
        {"texto": "Árbol sintáctico (precedencia: * + ?  >  concatenación  >  |):",
         "detalle": a_arbol_texto(arbol), "mono": True},
    ]
    etapas = [_etapa("entrada", "Análisis de la expresión",
                     f"Validación de Σ y de la expresión «{expresion.strip()}».", pasos_entrada)]

    afn, pasos_t = construir(arbol, alfabeto)
    etapas.append(_etapa("thompson", "AFN-ε (Thompson)",
                         "Cada subexpresión se convierte en un fragmento y los fragmentos se combinan.",
                         pasos_t, afn))

    afd, pasos_d = determinizar(afn)
    etapas.append(_etapa("afd", "AFD (subconjuntos)",
                         "Cada estado del AFD es un conjunto de estados del AFN-ε.", pasos_d, afd))

    etapas += _etapas_finales(afd)
    return {"modalidad": "A", "etapas": etapas}


# ---------------------------------------------------------------------- #
# Modalidad B: autómata ingresado manualmente
# ---------------------------------------------------------------------- #
def proceso_automata(datos: dict) -> dict:
    original = leer_automata(datos)
    etapas = [_etapa(
        "entrada", "Autómata ingresado",
        "Componentes registrados y validados.",
        [{"texto": f"Q = {texto_conjunto(original.estados)} · Σ = {{{', '.join(original.alfabeto)}}} · "
                   f"q₀ = {original.inicial} · F = {texto_conjunto(original.finales)}", "nivel": "ok"},
         {"texto": f"Se registraron {sum(len(d) for d in original.transiciones.values())} transiciones."}],
        original,
    )]

    # --- Clasificación (RF-05) ---
    pasos_c = []
    eps = original.transiciones_epsilon()
    nd = original.pares_no_deterministas()
    falt = original.pares_faltantes()
    if eps:
        pasos_c.append({"texto": f"Tiene {len(eps)} transiciones ε, así que NO es determinista:", "nivel": "aviso",
                        "detalle": [f"{o} —ε→ {d}" for o, d in eps]})
    else:
        pasos_c.append({"texto": "No tiene transiciones ε.", "nivel": "ok"})
    if nd:
        pasos_c.append({"texto": "Hay pares (estado, símbolo) con más de un destino, así que NO es determinista:",
                        "nivel": "aviso", "detalle": [f"δ({o}, {s}) = {texto_conjunto(ds)}" for o, s, ds in nd]})
    else:
        pasos_c.append({"texto": "Ningún par (estado, símbolo) tiene más de un destino.", "nivel": "ok"})
    if falt and not eps and not nd:
        pasos_c.append({"texto": f"Faltan {len(falt)} transiciones, así que es un AFD incompleto (parcial); "
                                 "se completará con un estado sumidero antes de minimizar.", "nivel": "aviso",
                        "detalle": [f"δ({e}, {a}) sin definir" for e, a in falt]})
    tipo = original.tipo()
    explicacion = {
        "AFN-ε": "Es un AFN con transiciones vacías (AFN-ε).",
        "AFN": "Es un autómata finito NO determinista (AFN).",
        "AFD": "Es un autómata finito determinista (AFD): para cada estado y símbolo hay exactamente un destino.",
        "AFD (incompleto)": "Es determinista: nunca hay más de un destino ni transiciones ε.",
    }[tipo]
    pasos_c.append({"texto": f"Conclusión: {tipo}. {explicacion}", "nivel": "ok"})
    inacc = [e for e in original.estados if e not in set(original.alcanzables())]
    if inacc:
        uno = len(inacc) == 1
        verbo = "no es alcanzable" if uno else "no son alcanzables"
        accion = "se eliminará" if uno else "se eliminarán"
        pasos_c.append({"texto": f"Observación: {', '.join(inacc)} {verbo} desde {original.inicial}; "
                                 f"{accion} antes de minimizar.", "nivel": "aviso"})
    etapas.append(_etapa("clasificacion", "Clasificación", f"El autómata ingresado es: {tipo}.", pasos_c))

    # --- Determinización (si corresponde) ---
    if original.es_determinista():
        afd = original
        etapas.append(_etapa(
            "afd", "AFD",
            "El autómata ya es determinista; no requiere conversión.",
            [{"texto": "El autómata ya es determinista, por lo que no se aplica la construcción de subconjuntos. "
                       "Se continúa directamente con la minimización.", "nivel": "ok"}],
            afd,
        ))
    else:
        afd, pasos_d = determinizar(original)
        etapas.append(_etapa("afd", "AFD (subconjuntos)",
                             "Cada estado del AFD es un conjunto de estados del autómata ingresado.", pasos_d, afd))

    etapas += _etapas_finales(afd)
    return {"modalidad": "B", "etapas": etapas, "tipo_original": tipo}


__all__ = ["proceso_expresion", "proceso_automata", "EPS"]
