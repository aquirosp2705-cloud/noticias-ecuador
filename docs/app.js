const rejilla = document.getElementById("rejilla");
const estado = document.getElementById("estado");
const selectPeriodo = document.getElementById("periodo");
const botonActualizar = document.getElementById("actualizar");
const pestanas = document.querySelectorAll("#pestanas button");

const INTERVALO_AUTO_MS = 10 * 60 * 1000; // refresco automático cada 10 minutos
const PERIODOS_MS = {
  "6h": 6 * 3600e3,
  "24h": 24 * 3600e3,
  "3d": 3 * 24 * 3600e3,
  "7d": 7 * 24 * 3600e3,
  "30d": 30 * 24 * 3600e3,
};
// En tu PC (servidor local) se usa la API; en GitHub Pages, los JSON que genera GitHub Actions.
const EN_LOCAL = ["localhost", "127.0.0.1"].includes(location.hostname);
let zona = "ecuador";
let temporizador = null;

async function obtenerDatos(zonaElegida, periodo, refrescar) {
  if (EN_LOCAL) {
    const params = new URLSearchParams({ zona: zonaElegida, periodo, refrescar: refrescar ? "1" : "0" });
    const respuesta = await fetch(`/api/noticias?${params}`);
    const datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(datos.error || "Error desconocido");
    return datos;
  }
  // Modo publicado: se filtra el periodo en el navegador sobre los JSON ya generados.
  const respuesta = await fetch(`data/${zonaElegida}.json?t=${Date.now()}`, { cache: "no-store" });
  if (!respuesta.ok) throw new Error("No se pudieron leer las noticias publicadas");
  const datos = await respuesta.json();
  const desde = Date.now() - PERIODOS_MS[periodo];
  const noticias = datos.noticias.filter((n) => new Date(n.fecha).getTime() >= desde);
  return { ...datos, periodo, total: noticias.length, noticias };
}

function tiempoRelativo(fechaIso) {
  const minutos = Math.round((Date.now() - new Date(fechaIso).getTime()) / 60000);
  if (minutos < 1) return "justo ahora";
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  const dias = Math.round(horas / 24);
  return `hace ${dias} d`;
}

function crearTarjeta(noticia) {
  const tarjeta = document.createElement("article");
  tarjeta.className = "tarjeta";

  let imagen;
  if (noticia.imagen) {
    imagen = document.createElement("img");
    imagen.className = "imagen";
    imagen.loading = "lazy";
    imagen.alt = "";
    imagen.src = noticia.imagen;
    imagen.onerror = () => imagen.replaceWith(crearPlaceholder(noticia.medio));
  } else {
    imagen = crearPlaceholder(noticia.medio);
  }

  const cuerpo = document.createElement("div");
  cuerpo.className = "cuerpo";

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = `${noticia.medio || "Medio desconocido"} · ${tiempoRelativo(noticia.fecha)}`;

  const enlace = document.createElement("a");
  enlace.className = "titulo";
  enlace.href = noticia.enlace;
  enlace.target = "_blank";
  enlace.rel = "noopener noreferrer";
  enlace.textContent = noticia.titulo;

  cuerpo.append(meta, enlace);
  tarjeta.append(imagen, cuerpo);
  return tarjeta;
}

function crearPlaceholder(medio) {
  const div = document.createElement("div");
  div.className = "imagen";
  div.textContent = (medio || "N").trim().charAt(0).toUpperCase();
  return div;
}

function mostrarEsqueleto() {
  rejilla.replaceChildren(...Array.from({ length: 6 }, () => {
    const d = document.createElement("div");
    d.className = "esqueleto";
    return d;
  }));
}

async function cargar({ refrescar = false } = {}) {
  const periodo = selectPeriodo.value;
  const nombreZona = document.querySelector(`#pestanas button[data-zona="${zona}"]`).textContent;
  botonActualizar.disabled = true;
  estado.textContent = `Cargando noticias de ${nombreZona}…`;
  mostrarEsqueleto();

  try {
    const datos = await obtenerDatos(zona, periodo, refrescar);

    if (datos.noticias.length === 0) {
      rejilla.replaceChildren(Object.assign(document.createElement("p"), {
        className: "vacio",
        textContent: "No hay noticias en este periodo. Prueba con un rango más amplio.",
      }));
    } else {
      rejilla.replaceChildren(...datos.noticias.map(crearTarjeta));
    }
    const hora = new Date(datos.actualizado).toLocaleTimeString("es-EC", { hour: "2-digit", minute: "2-digit" });
    const nota = EN_LOCAL ? "" : " · se actualiza cada hora";
    estado.textContent = `${datos.total} noticias de ${nombreZona} · actualizado a las ${hora}${nota}`;
  } catch (error) {
    rejilla.replaceChildren();
    estado.textContent = `Error: ${error.message}. Revisa tu conexión y vuelve a intentar.`;
  } finally {
    botonActualizar.disabled = false;
  }
}

function reiniciarAutoactualizacion() {
  clearInterval(temporizador);
  temporizador = setInterval(() => cargar({ refrescar: true }), INTERVALO_AUTO_MS);
}

pestanas.forEach((boton) => {
  boton.addEventListener("click", () => {
    zona = boton.dataset.zona;
    pestanas.forEach((b) => b.classList.toggle("activa", b === boton));
    cargar();
  });
});

selectPeriodo.addEventListener("change", () => cargar());
botonActualizar.addEventListener("click", () => {
  cargar({ refrescar: true });
  reiniciarAutoactualizacion();
});

cargar();
reiniciarAutoactualizacion();
