"""Generación de la imagen PNG del ticket (384 px de ancho, impresora térmica).

384 px = ancho de impresión de una impresora térmica de 58 mm a 203 dpi,
así que cada píxel corresponde a un punto de la impresora (sin reescalar).

El código de barras se dibuja a mano con Pillow a partir del patrón Code 128
que calcula python-barcode: así cada barra mide un número ENTERO de píxeles y
el escáner físico lo lee sin problemas (al reescalar aparecen barras borrosas).
"""

import io
import textwrap
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from barcode import Code128
from PIL import Image, ImageDraw, ImageFont

from app.errores import CodigoNoImprimible

ANCHO = 384
MARGEN = 16
ZONA_SILENCIO_MODULOS = 10  # espacio en blanco mínimo a cada lado (norma Code 128)
ALTO_BARRAS = 110  # largo de las barras cuando el código va horizontal
MIN_PX_POR_MODULO = 2  # 2 puntos = 0,25 mm a 203 dpi: mínimo legible por escáner
MAX_PX_POR_MODULO = 3
ALTO_MAXIMO_VERTICAL = 1200  # ~15 cm de papel

BLANCO = 255
NEGRO = 0

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _ruta_roboto(estilo: str) -> Path | None:
    try:
        import font_roboto
    except ImportError:
        return None
    ruta = Path(font_roboto.__file__).parent / "files" / f"Roboto-{estilo}.ttf"
    return ruta if ruta.exists() else None


@lru_cache(maxsize=None)
def _fuente(tamano: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    # Roboto viene en el paquete font-roboto (requirements.txt), así no se depende de
    # las fuentes del servidor (Railway no trae). La fuente por defecto de Pillow es
    # el último recurso: no tiene tildes ni ñ.
    ruta = _ruta_roboto("Bold" if negrita else "Regular")
    if ruta:
        return ImageFont.truetype(str(ruta), tamano)
    return ImageFont.load_default(size=tamano)


def _fuente_que_quepa(texto: str, tamano: int, ancho_max: int, negrita: bool = False):
    """Reduce el tamaño hasta que `texto` quepa en una línea de `ancho_max` px."""
    while tamano > 10:
        fuente = _fuente(tamano, negrita)
        if fuente.getlength(texto) <= ancho_max:
            return fuente
        tamano -= 1
    return _fuente(tamano, negrita)


def formatear_fecha(fecha: str | None) -> str:
    """'2027-01-10T19:00:00' -> '10 de enero de 2027, 19:00'. Si no se puede, la deja igual."""
    if not fecha:
        return "Fecha por confirmar"
    try:
        dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
    except ValueError:
        return fecha
    texto = f"{dt.day} de {MESES[dt.month - 1]} de {dt.year}"
    if "T" in fecha or " " in fecha:
        texto += f", {dt:%H:%M}"
    return texto


def patron_code128(codigo: str) -> str:
    """Devuelve el patrón de módulos ('1' = barra, '0' = espacio) del Code 128."""
    try:
        return Code128(codigo).build()[0]
    except Exception as exc:  # caracteres que Code 128 no admite, etc.
        raise CodigoNoImprimible(f"No se puede codificar '{codigo}' en Code 128") from exc


def _dibujar_barras(patron: str, px_por_modulo: int, largo_barra: int) -> Image.Image:
    """Barras horizontales en fila (código "acostado"), con zona de silencio incluida."""
    ancho = (len(patron) + 2 * ZONA_SILENCIO_MODULOS) * px_por_modulo
    imagen = Image.new("L", (ancho, largo_barra), BLANCO)
    dibujo = ImageDraw.Draw(imagen)
    x = ZONA_SILENCIO_MODULOS * px_por_modulo
    for modulo in patron:
        if modulo == "1":
            dibujo.rectangle([x, 0, x + px_por_modulo - 1, largo_barra - 1], fill=NEGRO)
        x += px_por_modulo
    return imagen


def dibujar_codigo_barras(codigo: str, ancho: int = ANCHO) -> Image.Image:
    """Imagen de `ancho` px con el Code 128 centrado.

    - Si cabe en horizontal con al menos 2 px por módulo, se dibuja horizontal.
    - Si no (p. ej. códigos de 20 caracteres alfanuméricos = 255 módulos), se dibuja
      VERTICAL a lo largo del ticket con 2 px por módulo: en horizontal quedaría con
      barras de 1 px (0,125 mm), que un escáner de mano no lee de forma confiable.
    """
    patron = patron_code128(codigo)
    modulos_totales = len(patron) + 2 * ZONA_SILENCIO_MODULOS

    px_horizontal = min(MAX_PX_POR_MODULO, ancho // modulos_totales)
    if px_horizontal >= MIN_PX_POR_MODULO:
        barras = _dibujar_barras(patron, px_horizontal, ALTO_BARRAS)
    else:
        largo_barra = ancho - 2 * MARGEN
        barras = _dibujar_barras(patron, MIN_PX_POR_MODULO, largo_barra).rotate(90, expand=True)
        if barras.height > ALTO_MAXIMO_VERTICAL:
            raise CodigoNoImprimible(
                f"El código '{codigo}' es demasiado largo para imprimirlo como Code 128"
            )

    imagen = Image.new("L", (ancho, barras.height), BLANCO)
    imagen.paste(barras, ((ancho - barras.width) // 2, 0))
    return imagen


def _texto_centrado(dibujo: ImageDraw.ImageDraw, y: int, texto: str, fuente) -> int:
    """Dibuja `texto` centrado y devuelve la y siguiente."""
    izq, arriba, der, abajo = dibujo.textbbox((0, 0), texto, font=fuente)
    dibujo.text(((ANCHO - (der - izq)) // 2 - izq, y - arriba), texto, font=fuente, fill=NEGRO)
    return y + (abajo - arriba)


def generar_ticket_png(nombre_evento: str, fecha: str | None, codigo: str) -> bytes:
    """Genera el ticket completo y devuelve los bytes del PNG."""
    f_marca = _fuente(18, negrita=True)
    f_nombre = _fuente(28, negrita=True)
    f_fecha = _fuente(20)
    f_codigo = _fuente_que_quepa(codigo, 24, ANCHO - 2 * MARGEN, negrita=True)
    f_pie = _fuente(14)

    lineas_nombre = textwrap.wrap(nombre_evento, width=22) or [nombre_evento]
    fecha_texto = formatear_fecha(fecha)
    barras = dibujar_codigo_barras(codigo)

    # Lienzo alto de sobra; al final se recorta al contenido.
    lienzo = Image.new("L", (ANCHO, 2000), BLANCO)
    d = ImageDraw.Draw(lienzo)

    y = MARGEN
    y = _texto_centrado(d, y, "EVENTPASS", f_marca) + 10
    d.line([MARGEN, y, ANCHO - MARGEN, y], fill=NEGRO, width=2)
    y += 14
    for linea in lineas_nombre:
        y = _texto_centrado(d, y, linea, f_nombre) + 6
    y += 4
    y = _texto_centrado(d, y, fecha_texto, f_fecha) + 16
    d.line([MARGEN, y, ANCHO - MARGEN, y], fill=NEGRO, width=1)
    y += 16
    lienzo.paste(barras, (0, y))
    y += barras.height + 10
    y = _texto_centrado(d, y, codigo, f_codigo) + 14
    y = _texto_centrado(d, y, "Presenta este ticket en el acceso", f_pie) + MARGEN

    ticket = lienzo.crop((0, 0, ANCHO, y))
    salida = io.BytesIO()
    ticket.save(salida, format="PNG", optimize=True)
    return salida.getvalue()
