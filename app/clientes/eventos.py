"""Cliente de la API de eventos."""

from urllib.parse import quote

import httpx

from app.clientes.http import obtener_json
from app.errores import ConfiguracionIncompleta, RespuestaInvalida

SERVICIO = "eventos"


async def obtener_evento(cliente: httpx.AsyncClient, base_url: str, evento_id) -> dict | None:
    """GET {EVENTOS_URL}/eventos/{evento_id}.

    Devuelve {"id", "nombre", "fecha", "capacidad", "disponibles", ...} o None.
    """
    if not base_url:
        raise ConfiguracionIncompleta("EVENTOS_URL")

    evento = await obtener_json(cliente, f"{base_url}/eventos/{quote(str(evento_id), safe='')}", SERVICIO)
    if evento is None:
        return None
    if not evento.get("nombre"):
        raise RespuestaInvalida(SERVICIO, "falta nombre")
    return evento
