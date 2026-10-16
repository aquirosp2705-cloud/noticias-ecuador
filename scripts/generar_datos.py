"""Genera docs/data/<zona>.json con noticias y fotos.

Lo ejecuta GitHub Actions cada hora (ver .github/workflows/actualizar.yml).
Las fotos ya resueltas en la ejecución anterior se reutilizan para no repetir
peticiones.
"""

import concurrent.futures as cf
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import server  # noqa: E402  (reutiliza la lógica de server.py)

CARPETA_SALIDA = RAIZ / "docs" / "data"
MAX_NOTICIAS = 60


def cargar_previas(zona):
    """Mapa enlace -> imagen de la ejecución anterior, para no volver a buscarlas."""
    ruta = CARPETA_SALIDA / f"{zona}.json"
    if not ruta.exists():
        return {}
    previo = json.loads(ruta.read_text(encoding="utf-8"))
    return {n["enlace"]: n["imagen"] for n in previo.get("noticias", []) if n.get("imagen")}


def generar_zona(zona, ahora):
    cfg = server.ZONAS[zona]
    crudas = server.obtener_feed(zona, refrescar=True)

    vistos = set()
    seleccion = []
    for noticia in sorted(crudas, key=lambda n: n["fecha"], reverse=True):
        clave = noticia["titulo"].lower()
        if clave in vistos:
            continue
        vistos.add(clave)
        seleccion.append(noticia)
        if len(seleccion) == MAX_NOTICIAS:
            break

    conocidas = cargar_previas(zona)
    pendientes = [n["enlace"] for n in seleccion if n["enlace"] not in conocidas]
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        resueltas = dict(zip(pendientes, pool.map(server.imagen_con_cache, pendientes)))

    datos = {
        "zona": zona,
        "nombre": cfg["nombre"],
        "actualizado": ahora,
        "noticias": [
            {
                "titulo": n["titulo"],
                "enlace": n["enlace"],
                "medio": n["medio"],
                "fecha": n["fecha"].isoformat(timespec="seconds"),
                "imagen": conocidas.get(n["enlace"]) or resueltas.get(n["enlace"]),
            }
            for n in seleccion
        ],
    }
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA_SALIDA / f"{zona}.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    con_imagen = sum(1 for n in datos["noticias"] if n["imagen"])
    print(f"{zona}: {len(datos['noticias'])} noticias, {con_imagen} con foto")


def main():
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for zona in server.ZONAS:
        generar_zona(zona, ahora)


if __name__ == "__main__":
    main()
