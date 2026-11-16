from fastapi import FastAPI

from app.errores import registrar_manejadores
from app.rutas import salud, tickets


def crear_app() -> FastAPI:
    app = FastAPI(
        title="EventPass - Servicio de tickets (Equipo 7)",
        description="Genera la imagen PNG del ticket con código de barras Code 128.",
        version="0.1.0",
    )
    registrar_manejadores(app)
    app.include_router(salud.router)
    app.include_router(tickets.router)
    return app
