"""Configuración del servicio, leída desde variables de entorno.

El docente configura ENTRADAS_URL y EVENTOS_URL en Railway. En local se
pueden poner en un archivo .env (ver .env.example).
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Carga .env si existe (en Railway no hay .env y se usan las variables reales).
load_dotenv()


@dataclass(frozen=True)
class Configuracion:
    entradas_url: str
    eventos_url: str
    timeout_segundos: float


def _limpiar_url(valor: str | None) -> str:
    # Quita espacios y la barra final para poder concatenar "/entradas/...".
    return (valor or "").strip().rstrip("/")


def obtener_configuracion() -> Configuracion:
    """Lee el entorno en cada llamada (así las pruebas pueden cambiarlo)."""
    return Configuracion(
        entradas_url=_limpiar_url(os.getenv("ENTRADAS_URL")),
        eventos_url=_limpiar_url(os.getenv("EVENTOS_URL")),
        timeout_segundos=float(os.getenv("HTTP_TIMEOUT_SEGUNDOS", "5")),
    )
