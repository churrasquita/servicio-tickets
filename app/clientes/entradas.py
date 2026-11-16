"""Cliente de la API de entradas (Equipo 5)."""

from urllib.parse import quote

import httpx

from app.clientes.http import obtener_json
from app.errores import ConfiguracionIncompleta, RespuestaInvalida

SERVICIO = "entradas"


async def obtener_entrada(cliente: httpx.AsyncClient, base_url: str, codigo: str) -> dict | None:
    """GET {ENTRADAS_URL}/entradas/{codigo}.

    Devuelve {"codigo", "evento_id", "estado", ...} o None si la entrada no existe.
    """
    if not base_url:
        raise ConfiguracionIncompleta("ENTRADAS_URL")

    entrada = await obtener_json(cliente, f"{base_url}/entradas/{quote(codigo, safe='')}", SERVICIO)
    if entrada is None:
        return None
    if entrada.get("evento_id") is None:
        raise RespuestaInvalida(SERVICIO, "falta evento_id")
    return entrada
