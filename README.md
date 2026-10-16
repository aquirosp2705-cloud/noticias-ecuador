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
- GitHub guarda el código, pero no ejecuta Python: la app corre en tu computador (o en un servicio como Render o Railway si quieres publicarla).

## Estructura

```
server.py          Servidor y lógica de noticias/fotos
static/index.html  Página principal
static/style.css   Estilos (modo claro y oscuro)
static/app.js     Pestañas, periodo, actualización y tarjetas
```
