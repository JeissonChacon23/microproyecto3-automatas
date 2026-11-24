# Microproyecto #3 · Autómatas finitos

Software educativo para Teoría de la Computación (UFPS). Construye, determiniza y minimiza autómatas finitos y explica cada paso.

- **Estudiante:** Jeisson Javier Chacón Parada · Código 1151594
- **Docente:** Janeth Parada
- **Aplicación desplegada:** https://microproyecto3-automatas.vercel.app

- **Modalidad A:** alfabeto + expresión regular → AFN-ε (Thompson) → AFD (subconjuntos) → inaccesibles → AFD mínimo (Moore)
- **Modalidad B:** autómata ingresado → clasificación AFD/AFN/AFN-ε → AFD (si hace falta) → inaccesibles → AFD mínimo
- En cada etapa se muestran la tabla de transición, el diagrama y la explicación paso a paso. También se pueden comparar las etapas con el resultado final y simular cadenas sobre cualquiera de ellas.

## Instalación y ejecución

Requiere Python 3.9 o superior.

```bash
git clone https://github.com/JeissonChacon23/microproyecto3-automatas.git
cd microproyecto3-automatas
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python app.py
```

Luego abre http://127.0.0.1:5000. En Windows, el entorno se activa con `.venv\Scripts\activate`.

Pruebas automáticas (resultado esperado: `33 passed`):

```bash
python -m pytest -q
```

Para desplegar en Vercel: `vercel` desde la raíz del proyecto (usa `vercel.json`).

## Sintaxis de entrada

**Alfabeto:** símbolos de un solo carácter separados por comas (`a, b`). No se permiten símbolos repetidos ni reservados: `( ) | * + ? ε , · ∅`.

**Expresión regular**

| Sintaxis | Significado |
|---|---|
| `a` | símbolo del alfabeto |
| `ε` | cadena vacía |
| `r\|s` | unión |
| `rs` | concatenación (implícita) |
| `r*`, `r+`, `r?` | cero o más, una o más, cero o una |
| `(r)` | agrupación |

Precedencia: `* + ?` > concatenación > `|`.

**Autómata (Modalidad B):** estados, alfabeto, estado inicial, finales y una transición por línea:

```
q0, a -> q1
q0, a -> q1, q2     # varios destinos = no determinismo
q1, ε -> q2         # también se acepta "eps"
```

## Estructura

```
app.py                     Servidor Flask (rutas /api/expresion, /api/automata, /api/simular)
nucleo/
  automata.py              Estructura de datos, tabla de transición, código DOT
  expresion.py             Alfabeto, análisis léxico y sintáctico (descenso recursivo)
  thompson.py              Construcción de Thompson
  determinizacion.py       ε-cerradura, mover, construcción de subconjuntos
  minimizacion.py          Inaccesibles, completado con sumidero, Moore
  simulacion.py            Simulación de cadenas en AFD y AFN
  entrada_automata.py      Lectura y validación de la Modalidad B
  procesos.py              Orquesta las etapas de cada modalidad
templates/index.html       Interfaz
static/app.js, estilos.css
static/vendor/viz-global.js  Viz.js 3.31 (MIT), Graphviz en WebAssembly
tests/test_nucleo.py       Pruebas (casos resueltos + equivalencia aleatoria)
```

## Bibliotecas

- **Flask:** servidor web y API JSON.
- **Viz.js:** solo dibuja los diagramas a partir del código DOT que genera `automata.py`. No interviene en ningún algoritmo.
- **pytest:** solo se usa para las pruebas. En ellas, el módulo `re` de Python sirve como juez para comprobar la equivalencia; la aplicación no lo usa.

Las tres construcciones del autómata (Thompson, subconjuntos y Moore) están implementadas a mano en `nucleo/`.

## Nombres de estados

| Etapa | Nombres | Correspondencia |
|---|---|---|
| Thompson | `q0, q1, …` en orden de creación | — |
| Subconjuntos | `S0, S1, …` en orden de descubrimiento | conjunto de estados `q` que contiene cada uno |
| Mínimo | `M0, M1, …` (`M0` es el inicial) | grupo de estados de la etapa anterior |
| Sumidero agregado | `Ø` | — |
