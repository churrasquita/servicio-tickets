"""Pruebas de la imagen: el Code 128 dibujado corresponde EXACTAMENTE al código."""

import io

import pytest
from PIL import Image

from app.errores import CodigoNoImprimible
from app.ticket.imagen import (
    ANCHO,
    MIN_PX_POR_MODULO,
    ZONA_SILENCIO_MODULOS,
    dibujar_codigo_barras,
    formatear_fecha,
    generar_ticket_png,
    patron_code128,
)

CODIGO_20 = "01234567890123456789"  # 20 dígitos, como los que emitirá el sistema
# Respaldo: si algún día el código trae letras y no cabe horizontal, va vertical
CODIGO_ALFANUMERICO_LARGO = "EP-A1B2C3D4E5F6G7H8I"


def _leer_patron(pixeles: list[int]) -> tuple[str, int, int]:
    """Reconstruye los módulos ('1' barra / '0' espacio) de una línea de píxeles.

    Devuelve (patrón, px por módulo, zona de silencio en módulos).
    """
    negros = [i for i, p in enumerate(pixeles) if p < 128]
    inicio, fin = negros[0], negros[-1]
    anchos, actual, largo = [], True, 0
    for p in pixeles[inicio : fin + 1]:
        if (p < 128) == actual:
            largo += 1
        else:
            anchos.append(largo)
            actual, largo = p < 128, 1
    anchos.append(largo)
    modulo = min(anchos)
    bits = "".join("1" if p < 128 else "0" for p in pixeles[inicio : fin + 1 : modulo])
    return bits, modulo, inicio // modulo


def test_codigo_de_20_digitos_va_horizontal_y_es_exacto():
    # Code 128 agrupa los dígitos de a dos: 20 dígitos caben en 384 px con módulos de 2 px
    imagen = dibujar_codigo_barras(CODIGO_20)
    fila = [imagen.getpixel((x, imagen.height // 2)) for x in range(imagen.width)]
    bits, px_modulo, zona = _leer_patron(fila)

    assert imagen.width == ANCHO
    assert imagen.height < 200  # horizontal, no vertical
    assert bits == patron_code128(CODIGO_20)
    assert px_modulo >= MIN_PX_POR_MODULO  # >= 0,25 mm por módulo a 203 dpi
    assert zona >= ZONA_SILENCIO_MODULOS


def test_codigo_alfanumerico_largo_va_vertical_con_barras_legibles():
    imagen = dibujar_codigo_barras(CODIGO_ALFANUMERICO_LARGO)
    columna = [imagen.getpixel((imagen.width // 2, y)) for y in range(imagen.height)]
    bits, px_modulo, zona = _leer_patron(columna)

    assert imagen.width == ANCHO
    # Leído de arriba abajo o de abajo arriba, el patrón es el del código exacto
    assert patron_code128(CODIGO_ALFANUMERICO_LARGO) in (bits, bits[::-1])
    assert px_modulo >= MIN_PX_POR_MODULO  # >= 0,25 mm por módulo a 203 dpi
    assert zona >= ZONA_SILENCIO_MODULOS


def test_ticket_de_20_caracteres_mide_384px_de_ancho():
    png = generar_ticket_png("Festival Norte", "2027-01-10T19:00:00", CODIGO_20)
    imagen = Image.open(io.BytesIO(png))
    assert imagen.format == "PNG"
    assert imagen.width == 384


def test_otro_codigo_da_otro_patron():
    assert patron_code128(CODIGO_20) != patron_code128("01234567890123456788")


def test_codigo_absurdamente_largo_se_rechaza():
    with pytest.raises(CodigoNoImprimible):
        dibujar_codigo_barras("X" * 200)


def test_formatear_fecha():
    assert formatear_fecha("2027-01-10T19:00:00") == "10 de enero de 2027, 19:00"
    assert formatear_fecha("2027-12-03") == "3 de diciembre de 2027"
    assert formatear_fecha(None) == "Fecha por confirmar"
    assert formatear_fecha("pronto") == "pronto"
