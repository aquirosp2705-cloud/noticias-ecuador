# Noticias Ecuador

Aplicación local que muestra las noticias del momento para:

- **Guayaquil**
- **Samborondón**
- **Ecuador** (nacional)
- **Internacional**

Cada noticia incluye foto, medio, tiempo de publicación y enlace al artículo. Puedes elegir el periodo (6 horas, 24 horas, 3, 7 o 30 días) y actualizar cuando quieras; además se refresca sola cada 10 minutos.

## Requisitos

- Python 3.9 o superior (no necesita instalar librerías externas).
- Conexión a internet.

## Uso

**Forma fácil (Windows):** haz doble clic en `INICIAR NOTICIAS.bat`.

**Desde la terminal:**

```bash
python server.py
```

Se abre el navegador en `http://127.0.0.1:8000`. Para detenerla, presiona `Ctrl+C` en la terminal.

## Cómo funciona

- **Noticias:** se consultan los feeds RSS de Google News con la búsqueda de cada zona y la edición regional de Ecuador o Estados Unidos (en español).
- **Fotos:** para cada noticia se resuelve el enlace real del medio y se lee la imagen principal (`og:image`) de su artículo.
- **Caché:** los feeds se reutilizan 15 minutos y las fotos 6 horas, para no saturar las fuentes.

## Limitaciones

- Google News devuelve unas 100 noticias recientes por búsqueda; los periodos largos (30 días) pueden mostrar menos resultados.
- Algunos medios no publican foto en su página; en ese caso se muestra un recuadro con la inicial del medio.
- La primera carga de una zona tarda unos segundos mientras se buscan las fotos; las siguientes son casi inmediatas.
## Versión publicada (cualquier dispositivo)

La app está publicada con GitHub Pages en
https://aquirosp2705-cloud.github.io/noticias-ecuador/

- **GitHub Actions** ejecuta `scripts/generar_datos.py` cada hora, busca noticias y fotos y guarda los resultados en `docs/data/*.json`.
- **GitHub Pages** publica la carpeta `docs/`, que lee esos JSON y filtra por periodo en el navegador.
- Para forzar una actualización: pestaña **Actions → Actualizar noticias → Run workflow**.

## Estructura

```
server.py                         Servidor local y lógica de noticias/fotos
scripts/generar_datos.py          Genera los JSON para la versión publicada
.github/workflows/actualizar.yml  Tarea programada de GitHub Actions
docs/index.html                   Página principal
docs/style.css                    Estilos (modo claro y oscuro)
docs/app.js                       Pestañas, periodo, actualización y tarjetas
docs/data/                        Noticias generadas (JSON)
```
