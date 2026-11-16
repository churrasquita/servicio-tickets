"""Errores del servicio. Todos se responden como JSON {"error", "mensaje"}."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ErrorServicio(Exception):
    """Error con código HTTP, identificador y mensaje legible."""

    def __init__(self, status_code: int, error: str, mensaje: str):
        super().__init__(mensaje)
        self.status_code = status_code
        self.error = error
        self.mensaje = mensaje


class EntradaNoExiste(ErrorServicio):
    def __init__(self):
        super().__init__(404, "ENTRADA_NO_EXISTE", "Entrada no encontrada")


class EventoNoExiste(ErrorServicio):
    # La entrada existe pero su evento no: es una inconsistencia de otra API,
    # por eso se responde 502 y no 404.
    def __init__(self, evento_id):
        super().__init__(
            502,
            "EVENTO_NO_EXISTE",
            f"La entrada apunta al evento {evento_id}, pero la API de eventos no lo encontró",
        )


class ServicioNoResponde(ErrorServicio):
    def __init__(self, servicio: str):
        super().__init__(
            504, "SERVICIO_NO_RESPONDE", f"La API de {servicio} no respondió a tiempo"
        )


class ServicioNoDisponible(ErrorServicio):
    def __init__(self, servicio: str):
        super().__init__(
            502, "SERVICIO_NO_DISPONIBLE", f"No se pudo conectar con la API de {servicio}"
        )


class RespuestaInvalida(ErrorServicio):
    def __init__(self, servicio: str, detalle: str):
        super().__init__(
            502, "RESPUESTA_INVALIDA", f"Respuesta inesperada de la API de {servicio}: {detalle}"
        )


class ConfiguracionIncompleta(ErrorServicio):
    def __init__(self, variable: str):
        super().__init__(
            500, "CONFIGURACION_INCOMPLETA", f"Falta configurar la variable {variable}"
        )


class CodigoNoImprimible(ErrorServicio):
    def __init__(self, detalle: str):
        super().__init__(422, "CODIGO_NO_IMPRIMIBLE", detalle)


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorServicio)
    async def manejar_error_servicio(_: Request, exc: ErrorServicio) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error, "mensaje": exc.mensaje},
        )
