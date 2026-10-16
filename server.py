"""Servidor de noticias de Ecuador (Guayaquil, Samborondón, Ecuador e internacional).

Usa solo la librería estándar de Python. Las noticias vienen de los feeds RSS de
Google News (sin API key) y las fotos se toman de la metaetiqueta og:image de cada
artículo.

Uso:
    python server.py            -> abre http://127.0.0.1:8000
"""

import concurrent.futures as cf
import email.utils
import json
import re
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NoticiasEcuador/1.0"

# Zonas disponibles: cada una es una búsqueda en Google News con su edición regional.
ZONAS = {
    "guayaquil": {"nombre": "Guayaquil", "q": "Guayaquil", "gl": "EC", "ceid": "EC:es-419"},
    "samborondon": {"nombre": "Samborondón", "q": "Samborondón OR Samborondon", "gl": "EC", "ceid": "EC:es-419"},
    "ecuador": {"nombre": "Ecuador", "q": "Ecuador", "gl": "EC", "ceid": "EC:es-419"},
    "internacional": {"nombre": "Internacional", "q": "internacional OR mundo", "gl": "US", "ceid": "US:es-419"},
}

# Periodos de publicación que puede elegir el usuario.
PERIODOS = {
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

MAX_NOTICIAS = 40          # noticias máximas que se devuelven por consulta
TTL_FEED = 15 * 60         # segundos que se reutiliza el feed RSS de una zona
TTL_IMAGEN = 6 * 60 * 60   # segundos que se recuerda la foto de un artículo

_cache_feed = {}           # zona -> (momento, [noticias])
_cache_imagen = {}         # enlace -> (momento, url_imagen o None)
_lock = threading.Lock()


def descargar(url, limite=2_000_000, timeout=10):
    """Descarga una URL y devuelve (url_final, bytes). Sigue redirecciones."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es-EC,es;q=0.9"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as respuesta:
        return respuesta.geturl(), respuesta.read(limite)


def construir_url_feed(zona):
    cfg = ZONAS[zona]
    params = urllib.parse.urlencode(
        {"q": cfg["q"], "hl": "es-419", "gl": cfg["gl"], "ceid": cfg["ceid"]}
    )
    return f"https://news.google.com/rss/search?{params}"


def parsear_rss(contenido):
    raiz = ET.fromstring(contenido)
    noticias = []
    for item in raiz.iter("item"):
        titulo = (item.findtext("title") or "").strip()
        enlace = (item.findtext("link") or "").strip()
        fuente = item.find("source")
        medio = fuente.text.strip() if fuente is not None and fuente.text else ""
        # Google News añade " - Medio" al final del título; lo quitamos.
        if medio and titulo.endswith(" - " + medio):
            titulo = titulo[: -(len(medio) + 3)]
        try:
            fecha = email.utils.parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        if titulo and enlace:
            noticias.append({"titulo": titulo, "enlace": enlace, "medio": medio, "fecha": fecha})
    return noticias


def obtener_feed(zona, refrescar=False):
    """Devuelve las noticias crudas de una zona, con caché de unos minutos."""
    ahora = time.time()
    with _lock:
        previo = _cache_feed.get(zona)
    if previo and not refrescar and ahora - previo[0] < TTL_FEED:
        return previo[1]
    _, contenido = descargar(construir_url_feed(zona))
    noticias = parsear_rss(contenido)
    with _lock:
        _cache_feed[zona] = (ahora, noticias)
    return noticias


def url_real_de_google(enlace):
    """Resuelve el enlace de Google News (news.google.com/rss/articles/...) a la URL del medio.

    Google no redirige por HTTP: pide una firma y un timestamp en la página intermedia
    y luego los canjea en su endpoint batchexecute.
    """
    m = re.search(r"/articles/([^?/]+)", enlace)
    if not m:
        return None
    id_articulo = m.group(1)
    _, pagina = descargar(f"https://news.google.com/rss/articles/{id_articulo}", timeout=8)
    texto = pagina.decode("utf-8", "ignore")
    firma = re.search(r'data-n-a-sg="([^"]+)"', texto)
    marca = re.search(r'data-n-a-ts="([^"]+)"', texto)
    if not firma or not marca:
        return None

    interno = json.dumps([
        "garturlreq",
        [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
         "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
        id_articulo, int(marca.group(1)), firma.group(1),
    ])
    cuerpo = urllib.parse.urlencode(
        {"f.req": json.dumps([[["Fbv4je", interno, None, "generic"]]])}
    ).encode()
    peticion = urllib.request.Request(
        "https://news.google.com/_/DotsSplashUi/data/batchexecute",
        data=cuerpo,
        headers={
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(peticion, timeout=8) as respuesta:
        texto = respuesta.read().decode("utf-8", "ignore")
    m_url = re.search(r'\\"garturlres\\",\\"(https?:[^\\"]+)\\"', texto)
    return m_url.group(1) if m_url else None


PATRON_IMAGEN = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)(?::src)?["\'][^>]*?content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
PATRON_IMAGEN_INVERSO = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*?(?:property|name)=["\'](?:og:image|twitter:image)(?::src)?["\']',
    re.IGNORECASE,
)


def buscar_imagen(enlace):
    """Intenta obtener la foto principal de un artículo. Devuelve URL o None."""
    try:
        destino = url_real_de_google(enlace)
        if not destino:
            return None
        url_final, contenido = descargar(destino, limite=400_000, timeout=6)
    except Exception:
        return None
    html = contenido.decode("utf-8", "ignore")
    m = PATRON_IMAGEN.search(html) or PATRON_IMAGEN_INVERSO.search(html)
    if not m:
        return None
    return urllib.parse.urljoin(url_final, m.group(1).replace("&amp;", "&"))


def imagen_con_cache(enlace):
    ahora = time.time()
    with _lock:
        previo = _cache_imagen.get(enlace)
    if previo and ahora - previo[0] < TTL_IMAGEN:
        return previo[1]
    imagen = buscar_imagen(enlace)
    with _lock:
        _cache_imagen[enlace] = (ahora, imagen)
    return imagen


def obtener_noticias(zona, periodo, refrescar=False):
    ahora = datetime.now(timezone.utc)
    desde = ahora - PERIODOS[periodo]

    crudas = obtener_feed(zona, refrescar)
    vistos = set()
    seleccion = []
    for noticia in sorted(crudas, key=lambda n: n["fecha"], reverse=True):
        clave = noticia["titulo"].lower()
        if noticia["fecha"] < desde or clave in vistos:
            continue
        vistos.add(clave)
        seleccion.append(noticia)
        if len(seleccion) == MAX_NOTICIAS:
            break

    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        imagenes = list(pool.map(imagen_con_cache, [n["enlace"] for n in seleccion]))

    return {
        "zona": zona,
        "nombre": ZONAS[zona]["nombre"],
        "periodo": periodo,
        "actualizado": ahora.isoformat(timespec="seconds"),
        "total": len(seleccion),
        "noticias": [
            {
                "titulo": n["titulo"],
                "enlace": n["enlace"],
                "medio": n["medio"],
                "fecha": n["fecha"].isoformat(timespec="seconds"),
                "imagen": img,
            }
            for n, img in zip(seleccion, imagenes)
        ],
    }


class Manejador(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        ruta = urllib.parse.urlparse(self.path)
        if ruta.path != "/api/noticias":
            return super().do_GET()

        params = urllib.parse.parse_qs(ruta.query)
        zona = params.get("zona", ["ecuador"])[0]
        periodo = params.get("periodo", ["24h"])[0]
        refrescar = params.get("refrescar", ["0"])[0] == "1"

        if zona not in ZONAS or periodo not in PERIODOS:
            return self._enviar_json(400, {"error": "Zona o periodo no válido."})
        try:
            datos = obtener_noticias(zona, periodo, refrescar)
        except Exception as exc:
            return self._enviar_json(
                502, {"error": f"No se pudieron cargar las noticias: {exc}"}
            )
        return self._enviar_json(200, datos)

    def _enviar_json(self, codigo, objeto):
        cuerpo = json.dumps(objeto, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, formato, *args):
        pass  # silencia el log de cada petición


def main():
    servidor = ThreadingHTTPServer((HOST, PORT), Manejador)
    url = f"http://{HOST}:{PORT}"
    print(f"Noticias Ecuador en {url} (Ctrl+C para detener)")
    webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
