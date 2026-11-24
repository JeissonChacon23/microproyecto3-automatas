# app.py
"""
Servidor Flask del software educativo de autómatas finitos.

Rutas:
  GET  /                    interfaz web
  POST /api/expresion       Modalidad A (alfabeto + expresión regular)
  POST /api/automata        Modalidad B (autómata ingresado)
  POST /api/simular         simulación de una cadena sobre el autómata de una etapa

Ejecutar en local:  python app.py   ->  http://127.0.0.1:5000
"""

from flask import Flask, jsonify, render_template, request

from nucleo.automata import Automata
from nucleo.errores import ErrorEntrada
from nucleo.procesos import proceso_automata, proceso_expresion
from nucleo.simulacion import simular

app = Flask(__name__)
app.json.ensure_ascii = False


@app.errorhandler(ErrorEntrada)
def error_entrada(e: ErrorEntrada):
    return jsonify(e.a_dict()), 400


def _json() -> dict:
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorEntrada("La solicitud no tiene un cuerpo JSON válido.")
    return datos


@app.get("/")
def inicio():
    return render_template("index.html")


@app.post("/api/expresion")
def api_expresion():
    d = _json()
    return jsonify(proceso_expresion(d.get("alfabeto", ""), d.get("expresion", "")))


@app.post("/api/automata")
def api_automata():
    return jsonify(proceso_automata(_json()))


@app.post("/api/simular")
def api_simular():
    d = _json()
    try:
        automata = Automata.desde_dict(d["automata"])
    except (KeyError, TypeError):
        raise ErrorEntrada("No se recibió un autómata válido para simular.")
    return jsonify(simular(automata, d.get("cadena", "")))


if __name__ == "__main__":
    app.run(debug=True)
