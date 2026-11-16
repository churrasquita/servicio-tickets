"""Lógica HTTP común a los clientes de entradas y eventos."""

from collections.abc import AsyncIterator

import httpx

from app.config import obtener_configuracion
from app.errores import RespuestaInvalida, ServicioNoDisponible, ServicioNoResponde


async def obtener_cliente_http() -> AsyncIterator[httpx.AsyncClient]:
    """Dependencia de FastAPI: un cliente HTTP por solicitud.

    En las pruebas se reemplaza por un cliente con transporte simulado (mock).
    """
    config = obtener_configuracion()
    async with httpx.AsyncClient(timeout=config.timeout_segundos) as cliente:
        yield cliente


async def obtener_json(cliente: httpx.AsyncClient, url: str, servicio: str) -> dict | None:
    """Hace GET a `url` y devuelve el JSON.

    - 404 de la API externa  -> devuelve None (el llamador decide qué significa).
    - Timeout                -> ServicioNoResponde (504).
    - Sin conexión / DNS     -> ServicioNoDisponible (502).
    - Otro error o no-JSON   -> RespuestaInvalida (502).
    """
    try:
        respuesta = await cliente.get(url, headers={"Accept": "application/json"})
    except httpx.TimeoutException as exc:
        raise ServicioNoResponde(servicio) from exc
    except httpx.RequestError as exc:
        raise ServicioNoDisponible(servicio) from exc

    if respuesta.status_code == 404:
        return None
    if respuesta.status_code >= 400:
        raise RespuestaInvalida(servicio, f"HTTP {respuesta.status_code}")

    try:
        datos = respuesta.json()
    except ValueError as exc:
        raise RespuestaInvalida(servicio, "el cuerpo no es JSON") from exc
    if not isinstance(datos, dict):
        raise RespuestaInvalida(servicio, "se esperaba un objeto JSON")
    return datos
