# nucleo/minimizacion.py
"""
Eliminación de estados inaccesibles (RF-07) y minimización de AFD (RF-09).

Minimización por refinamiento de particiones (algoritmo de Moore):
  1. Se eliminan los estados inaccesibles desde el inicial.
  2. Si el AFD es incompleto, se completa con un estado sumidero (el
     algoritmo exige que la función de transición sea total).
  3. Partición inicial P0 = { F, Q − F } (finales y no finales).
  4. Refinamiento: dos estados de un mismo grupo siguen juntos solo si,
     para cada símbolo, van a parar al MISMO grupo de la partición actual.
     Cada estado recibe una "firma" = (grupo destino con cada símbolo) y
     los grupos se dividen según la firma.
  5. Se repite hasta que la partición no cambie. Cada grupo final es un
     estado del AFD mínimo (estados equivalentes = indistinguibles).

Nombres: los estados del AFD mínimo se llaman M0, M1, ... (M0 es el inicial)
y `correspondencia` indica qué estados de la etapa anterior agrupa cada uno.
"""

from __future__ import annotations

from collections import deque

from .automata import Automata, ordenar, texto_conjunto


def eliminar_inaccesibles(afd: Automata) -> tuple[Automata, list[dict]]:
    alcanzables = afd.alcanzables()
    inaccesibles = [e for e in afd.estados if e not in set(alcanzables)]
    pasos = [{
        "texto": f"Recorrido en anchura desde {afd.inicial}. Estados alcanzables (en orden de visita): "
                 f"{', '.join(alcanzables)}.",
    }]
    if not inaccesibles:
        pasos.append({"texto": "No hay estados inaccesibles; el autómata no cambia.", "nivel": "ok"})
        return afd, pasos
    pasos.append({"texto": f"Estados inaccesibles eliminados: {', '.join(inaccesibles)} "
                           "(ningún camino desde el estado inicial llega a ellos).", "nivel": "aviso"})
    conservar = set(alcanzables)
    trans = {
        (o, s): set(ds) & conservar
        for (o, s), ds in afd.transiciones.items()
        if o in conservar
    }
    corr = None
    if afd.correspondencia is not None:
        corr = {e: afd.correspondencia[e] for e in afd.estados if e in conservar}
    nuevo = Automata([e for e in afd.estados if e in conservar], afd.alfabeto, afd.inicial,
                     afd.finales & conservar, trans, corr)
    return nuevo, pasos


def completar(afd: Automata) -> tuple[Automata, list[dict]]:
    faltantes = afd.pares_faltantes()
    if not faltantes:
        return afd, []
    nombre = "Ø"
    k = 1
    while nombre in afd.estados:
        nombre = f"Ø{k}"
        k += 1
    trans = {k_: set(v) for k_, v in afd.transiciones.items()}
    for (e, a) in faltantes:
        trans[(e, a)] = {nombre}
    for a in afd.alfabeto:
        trans[(nombre, a)] = {nombre}
    corr = dict(afd.correspondencia) if afd.correspondencia is not None else None
    if corr is not None:
        corr[nombre] = []
    completo = Automata(afd.estados + [nombre], afd.alfabeto, afd.inicial, afd.finales, trans, corr)
    pares = ", ".join(f"δ({e},{a})" for e, a in faltantes)
    return completo, [{
        "texto": f"El AFD es incompleto (faltan {len(faltantes)} transiciones: {pares}). Se agrega el estado "
                 f"sumidero {nombre}, no final, al que van todas ellas y que se cicla con todos los símbolos.",
        "nivel": "aviso",
    }]


def minimizar(afd: Automata) -> tuple[Automata, list[dict]]:
    pasos: list[dict] = []
    alfabeto = afd.alfabeto
    finales = [e for e in afd.estados if e in afd.finales]
    no_finales = [e for e in afd.estados if e not in afd.finales]

    particion: list[list[str]] = [g for g in (finales, no_finales) if g]

    def grupo_de(p: list[list[str]]) -> dict[str, int]:
        return {e: i for i, g in enumerate(p) for e in g}

    def texto_particion(p: list[list[str]]) -> str:
        return ",  ".join(f"G{i + 1}={texto_conjunto(g)}" for i, g in enumerate(p))

    pasos.append({
        "texto": f"P0 = {{ F, Q−F }}: finales {texto_conjunto(finales)} y no finales {texto_conjunto(no_finales)}.",
        "detalle": [texto_particion(particion)],
    })

    iteracion = 0
    while True:
        iteracion += 1
        g = grupo_de(particion)
        filas = []
        nueva: list[list[str]] = []
        divisiones = []
        for gi, grupo in enumerate(particion):
            por_firma: dict[tuple, list[str]] = {}
            for e in grupo:
                firma = tuple(g[next(iter(afd.destinos(e, a)))] for a in alfabeto)
                por_firma.setdefault(firma, []).append(e)
                filas.append([f"G{gi + 1}", e] + [
                    f"{next(iter(afd.destinos(e, a)))} ∈ G{g[next(iter(afd.destinos(e, a)))] + 1}" for a in alfabeto
                ])
            subgrupos = list(por_firma.values())
            if len(subgrupos) > 1:
                divisiones.append(f"G{gi + 1} se divide en " + " y ".join(texto_conjunto(s) for s in subgrupos)
                                  + " porque sus estados van a grupos distintos.")
            nueva.extend(subgrupos)

        pasos.append({
            "texto": f"Iteración {iteracion}: se compara a qué grupo de P{iteracion - 1} lleva cada símbolo.",
            "tabla": {"encabezados": ["Grupo", "Estado"] + [f"con {a}" for a in alfabeto], "filas": filas},
            "detalle": (divisiones or ["Ningún grupo se divide."]) + [f"P{iteracion} = " + texto_particion(nueva)],
        })
        if len(nueva) == len(particion):
            pasos.append({"texto": f"P{iteracion} = P{iteracion - 1}: la partición es estable. "
                                   f"Cada grupo es un estado del AFD mínimo.", "nivel": "ok"})
            break
        particion = nueva

    # Se numeran los grupos en el orden de un recorrido desde el inicial,
    # así M0 es siempre el estado inicial.
    g = grupo_de(particion)
    orden_grupos: list[int] = []
    cola = deque([g[afd.inicial]])
    vistos = {g[afd.inicial]}
    while cola:
        gi = cola.popleft()
        orden_grupos.append(gi)
        rep = particion[gi][0]
        for a in alfabeto:
            dj = g[next(iter(afd.destinos(rep, a)))]
            if dj not in vistos:
                vistos.add(dj)
                cola.append(dj)
    nombre_grupo = {gi: f"M{k}" for k, gi in enumerate(orden_grupos)}

    trans = {}
    for gi in orden_grupos:
        rep = particion[gi][0]
        for a in alfabeto:
            trans[(nombre_grupo[gi], a)] = {nombre_grupo[g[next(iter(afd.destinos(rep, a)))]]}
    estados = [nombre_grupo[gi] for gi in orden_grupos]
    finales_min = {nombre_grupo[gi] for gi in orden_grupos if particion[gi][0] in afd.finales}
    corr = {nombre_grupo[gi]: ordenar(particion[gi]) for gi in orden_grupos}
    minimo = Automata(estados, alfabeto, nombre_grupo[g[afd.inicial]], finales_min, trans, corr)

    pasos.append({
        "texto": "Correspondencia de estados",
        "tabla": {"encabezados": ["Estado mínimo", "Agrupa a", "Final"],
                  "filas": [[n, texto_conjunto(corr[n]), "sí" if n in finales_min else "no"] for n in estados]},
    })
    ahorro = len(afd.estados) - len(estados)
    pasos.append({
        "texto": f"Resultado: AFD mínimo con {len(estados)} estados"
                 + (f" ({ahorro} menos que el AFD de entrada)." if ahorro else " (el AFD ya era mínimo)."),
        "nivel": "ok",
    })
    return minimo, pasos
