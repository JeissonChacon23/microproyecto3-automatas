// static/app.js
// Interfaz: envía las entradas al servidor Flask, muestra cada etapa
// (pasos, tabla y diagrama), la comparación con el AFD mínimo y la simulación.
// Toda la lógica de autómatas vive en el servidor (carpeta nucleo/).

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];

let resultado = null;     // respuesta del servidor
let etapaActual = 0;
const vizListo = Viz.instance();

// -------------------------------------------------------------------- //
// Utilidades
// -------------------------------------------------------------------- //
function el(etiqueta, props = {}, ...hijos) {
  const n = document.createElement(etiqueta);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else n.setAttribute(k, v);
  }
  for (const h of hijos.flat()) if (h != null) n.append(h);
  return n;
}

async function post(url, datos) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  });
  const json = await r.json().catch(() => ({ error: "Respuesta inválida del servidor." }));
  if (!r.ok) throw json;
  return json;
}

async function dibujar(contenedor, dot) {
  contenedor.replaceChildren(el("p", { class: "nota", text: "Dibujando…" }));
  try {
    const viz = await vizListo;
    const svg = viz.renderSVGElement(dot);
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    contenedor.replaceChildren(svg);
  } catch (e) {
    contenedor.replaceChildren(el("p", { class: "error", text: "No se pudo dibujar el diagrama: " + e }));
  }
}

function tablaTransicion(tabla) {
  const thead = el("thead", {}, el("tr", {}, el("th", { text: "" }),
    tabla.encabezados.map((h) => el("th", { text: h }))));
  const filas = tabla.filas.map((f) => el("tr", { class: f.marca.includes("*") ? "final" : "" },
    el("td", { class: "marca", text: f.marca }),
    el("td", { class: "estado", text: f.estado }),
    f.celdas.map((c) => el("td", { text: c })),
    f.corresponde !== undefined ? el("td", { class: "corr", text: f.corresponde }) : null,
  ));
  return el("table", { class: "tabla" }, thead, el("tbody", {}, filas));
}

function tablaSimple(encabezados, filas) {
  return el("table", { class: "tabla" },
    el("thead", {}, el("tr", {}, encabezados.map((h) => el("th", { text: h })))),
    el("tbody", {}, filas.map((f) => el("tr", {}, f.map((c) => el("td", { text: String(c) }))))));
}

function mostrarError(form, err) {
  $$(".invalido", form).forEach((i) => i.classList.remove("invalido"));
  const p = $("[data-error]", form);
  p.textContent = err ? (err.error || String(err)) : "";
  if (err && err.campo) {
    const campo = form.elements[err.campo];
    if (campo) { campo.classList.add("invalido"); campo.focus(); }
  }
}

// -------------------------------------------------------------------- //
// Entrada
// -------------------------------------------------------------------- //
$$(".pestana").forEach((b) => b.addEventListener("click", () => {
  $$(".pestana").forEach((x) => x.classList.toggle("activa", x === b));
  $("#formA").classList.toggle("oculto", b.dataset.modo !== "A");
  $("#formB").classList.toggle("oculto", b.dataset.modo !== "B");
}));

$$(".teclado button").forEach((b) => b.addEventListener("click", () => {
  const inp = $("#expresion");
  const [i, f] = [inp.selectionStart ?? inp.value.length, inp.selectionEnd ?? inp.value.length];
  inp.value = inp.value.slice(0, i) + b.dataset.ins + inp.value.slice(f);
  inp.focus();
  inp.setSelectionRange(i + b.dataset.ins.length, i + b.dataset.ins.length);
}));

$$('[data-form="A"] button').forEach((b) => b.addEventListener("click", () => {
  const f = $("#formA");
  f.elements.alfabeto.value = b.dataset.a;
  f.elements.expresion.value = b.dataset.e;
  f.requestSubmit();
}));

const EJEMPLOS_B = {
  afn: { estados: "p, q, r", alfabeto: "a, b", inicial: "p", finales: "r",
    transiciones: "p, a -> p, q\np, b -> p\nq, b -> r" },
  afne: { estados: "q0, q1, q2", alfabeto: "a, b, c", inicial: "q0", finales: "q2",
    transiciones: "q0, a -> q0\nq0, ε -> q1\nq1, b -> q1\nq1, ε -> q2\nq2, c -> q2" },
  afd: { estados: "A, B, C, D, E, F, G, H", alfabeto: "0, 1", inicial: "A", finales: "C",
    transiciones: "A, 0 -> B\nA, 1 -> F\nB, 0 -> G\nB, 1 -> C\nC, 0 -> A\nC, 1 -> C\nD, 0 -> C\nD, 1 -> G\n" +
      "E, 0 -> H\nE, 1 -> F\nF, 0 -> C\nF, 1 -> G\nG, 0 -> G\nG, 1 -> E\nH, 0 -> G\nH, 1 -> C" },
  incompleto: { estados: "q0, q1, q2, q3, q4", alfabeto: "0, 1", inicial: "q0", finales: "q2",
    transiciones: "q0, 0 -> q1\nq0, 1 -> q3\nq1, 0 -> q2\nq3, 0 -> q2\n# q4 no es alcanzable\nq4, 1 -> q0" },
};

$$('[data-form="B"] button').forEach((b) => b.addEventListener("click", () => {
  const f = $("#formB");
  for (const [k, v] of Object.entries(EJEMPLOS_B[b.dataset.ej])) f.elements[k].value = v;
  f.requestSubmit();
}));

async function procesar(form, url, datos) {
  const boton = $("button[type=submit]", form);
  boton.disabled = true;
  mostrarError(form, null);
  try {
    resultado = await post(url, datos);
    mostrarResultados();
  } catch (err) {
    mostrarError(form, err);
  } finally {
    boton.disabled = false;
  }
}

$("#formA").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const f = ev.target.elements;
  procesar(ev.target, "/api/expresion", { alfabeto: f.alfabeto.value, expresion: f.expresion.value });
});

$("#formB").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const f = ev.target.elements;
  const datos = {};
  for (const k of ["estados", "alfabeto", "inicial", "finales", "transiciones"]) datos[k] = f[k].value;
  procesar(ev.target, "/api/automata", datos);
});

// -------------------------------------------------------------------- //
// Resultados
// -------------------------------------------------------------------- //
function etapasConAutomata() {
  return resultado.etapas.map((e, i) => ({ ...e, indice: i })).filter((e) => e.automata);
}

function mostrarResultados() {
  $("#resultados").classList.remove("oculto");
  const nav = $("#etapas");
  nav.replaceChildren(...resultado.etapas.map((e, i) => {
    const b = el("button", { class: "etapa-boton" },
      el("span", { class: "num", text: String(i + 1) }),
      el("span", { class: "txt", text: e.titulo }),
      e.automata ? el("span", { class: "cnt", text: `${e.automata.num_estados} est.` }) : null);
    b.addEventListener("click", () => mostrarEtapa(i));
    return b;
  }));
  mostrarEtapa(resultado.etapas.length - 1);   // se abre en el AFD mínimo
  prepararComparacion();
  prepararSimulacion();
  $("#resultados").scrollIntoView({ behavior: "smooth", block: "start" });
}

function mostrarEtapa(i) {
  etapaActual = i;
  const e = resultado.etapas[i];
  $$(".etapa-boton").forEach((b, k) => b.classList.toggle("activa", k === i));
  $("#etapaNumero").textContent = `Etapa ${i + 1} de ${resultado.etapas.length}`;
  $("#etapaTitulo").textContent = e.titulo;
  $("#etapaResumen").textContent = e.resumen;
  $("#etapaTipo").textContent = e.automata ? e.automata.tipo : "";
  $("#etapaTipo").classList.toggle("oculto", !e.automata);

  const zona = $("#etapaAutomata");
  zona.classList.toggle("oculto", !e.automata);
  if (e.automata) {
    $("#etapaTabla").replaceChildren(tablaTransicion(e.automata.tabla));
    dibujar($("#etapaDiagrama"), e.automata.dot);
  }

  $("#etapaPasos").replaceChildren(...e.pasos.map((p) => {
    const li = el("li", { class: p.nivel ? "nivel-" + p.nivel : "" }, el("p", { text: p.texto }));
    if (p.detalle && p.detalle.length) {
      li.append(el("pre", { class: p.mono ? "detalle arbol" : "detalle", text: p.detalle.join("\n") }));
    }
    if (p.tabla) {
      li.append(el("div", { class: "tabla-envoltura" }, tablaSimple(p.tabla.encabezados, p.tabla.filas)));
    }
    return li;
  }));
}

function prepararComparacion() {
  const conAut = etapasConAutomata();
  const final = conAut[conAut.length - 1];
  const sel = $("#compararIzq");
  sel.replaceChildren(...conAut.slice(0, -1).map((e) =>
    el("option", { value: String(e.indice), text: `Etapa ${e.indice + 1}: ${e.titulo}` })));
  sel.onchange = () => {
    const e = resultado.etapas[Number(sel.value)];
    $("#compararTablaIzq").replaceChildren(tablaTransicion(e.automata.tabla));
    dibujar($("#compararDiagramaIzq"), e.automata.dot);
  };
  if (conAut.length > 1) sel.onchange();
  $("#compararTablaDer").replaceChildren(tablaTransicion(final.automata.tabla));
  dibujar($("#compararDiagramaDer"), final.automata.dot);

  const max = Math.max(...conAut.map((e) => e.automata.num_estados));
  $("#resumenEstados").replaceChildren(...conAut.map((e) => el("div", { class: "barra" },
    el("span", { class: "barra-txt", text: e.titulo }),
    el("span", { class: "barra-pista" },
      el("span", { class: "barra-relleno", style: `width:${(100 * e.automata.num_estados) / max}%` })),
    el("span", { class: "barra-num", text: `${e.automata.num_estados} estados · ${e.automata.tipo}` }))));
}

function prepararSimulacion() {
  const conAut = etapasConAutomata();
  $("#simAutomata").replaceChildren(...conAut.map((e) =>
    el("option", { value: String(e.indice), text: `${e.titulo} (${e.automata.tipo})` })));
  $("#simAutomata").value = String(conAut[conAut.length - 1].indice);
  $("#simResultado").classList.add("oculto");
  $("#simError").textContent = "";
}

$("#formSim").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const etapa = resultado.etapas[Number($("#simAutomata").value)];
  $("#simError").textContent = "";
  try {
    const r = await post("/api/simular", { automata: etapa.automata, cadena: $("#cadena").value });
    const v = $("#simVeredicto");
    v.textContent = `«${r.cadena}» — ${r.motivo}`;
    v.className = "veredicto " + (r.acepta ? "acepta" : "rechaza");
    const filas = r.pasos.map((p) => [p.paso, p.desde, p.simbolo, p.hacia, p.nota]);
    const enc = r.modo === "AFD" ? ["#", "Desde", "Símbolo", "Hacia", "Operación"]
                                 : ["#", "Activos", "Símbolo", "Nuevos activos", "Operación"];
    $("#simPasos").replaceChildren(
      r.recorrido ? el("p", { class: "recorrido mono", text: "Recorrido: " + r.recorrido.join(" → ") }) : "",
      tablaSimple(enc, filas));
    $("#simResultado").classList.remove("oculto");
    dibujar($("#simDiagrama"), r.dot);
  } catch (err) {
    $("#simError").textContent = err.error || String(err);
  }
});

// -------------------------------------------------------------------- //
// Descarga del diagrama como SVG (útil para la documentación)
// -------------------------------------------------------------------- //
$$("[data-descargar]").forEach((b) => b.addEventListener("click", () => {
  const svg = $("#" + b.dataset.descargar + " svg");
  if (!svg) return;
  const blob = new Blob([new XMLSerializer().serializeToString(svg)], { type: "image/svg+xml" });
  const a = el("a", { href: URL.createObjectURL(blob),
    download: `${resultado.etapas[etapaActual].id}.svg` });
  a.click();
  URL.revokeObjectURL(a.href);
}));
