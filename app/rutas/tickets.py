"""GET /tickets/{codigo}: entrada -> evento -> imagen PNG."""

import httpx
from fastapi import APIRouter, Depends, Response
from starlette.concurrency import run_in_threadpool

from app.clientes.entradas import obtener_entrada
from app.clientes.eventos import obtener_evento
from app.clientes.http import obtener_cliente_http
from app.config import obtener_configuracion
from app.errores import EntradaNoExiste, EventoNoExiste
from app.ticket.imagen import generar_ticket_png

router = APIRouter(tags=["tickets"])

RESPUESTA_404 = {
    "description": "La entrada no existe",
    "content": {
        "application/json": {
            "example": {"error": "ENTRADA_NO_EXISTE", "mensaje": "Entrada no encontrada"}
        }
    },
}


@router.get(
    "/tickets/{codigo}",
    response_class=Response,
    responses={
        200: {"content": {"image/png": {}}, "description": "Imagen del ticket (384 px de ancho)"},
        404: RESPUESTA_404,
        502: {"description": "La API de entradas o de eventos falló"},
        504: {"description": "La API de entradas o de eventos no respondió a tiempo"},
    },
)
async def obtener_ticket(
    codigo: str, cliente: httpx.AsyncClient = Depends(obtener_cliente_http)
) -> Response:
    config = obtener_configuracion()

    # 1. ¿La entrada existe? (API de entradas, Equipo 5)
    entrada = await obtener_entrada(cliente, config.entradas_url, codigo)
    if entrada is None:
        raise EntradaNoExiste()  # 404 JSON, no se genera imagen

    # 2. Datos del evento (API de eventos)
    evento_id = entrada["evento_id"]
    evento = await obtener_evento(cliente, config.eventos_url, evento_id)
    if evento is None:
        raise EventoNoExiste(evento_id)

    # 3. Imagen (Pillow es síncrono: se ejecuta en un hilo para no bloquear el servidor)
    codigo_entrada = str(entrada.get("codigo") or codigo)
    png = await run_in_threadpool(
        generar_ticket_png, evento["nombre"], evento.get("fecha"), codigo_entrada
    )

    # 4. Respuesta image/png
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="ticket-{codigo_entrada}.png"'},
    )
