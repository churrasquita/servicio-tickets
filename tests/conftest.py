"""Fixtures: la app con las APIs externas simuladas (mock) mediante httpx.MockTransport.

Ninguna prueba hace llamadas de red reales.
"""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.clientes.http import obtener_cliente_http
from main import app

ENTRADAS_URL = "http://entradas.test"
EVENTOS_URL = "http://eventos.test"

ENTRADA_OK = {"codigo": "12345678901234567890", "evento_id": 1, "estado": "EMITIDA"}
EVENTO_OK = {
    "id": 1,
    "nombre": "Festival Norte",
    "fecha": "2027-01-10T19:00:00",
    "capacidad": 100,
    "disponibles": 99,
}


class ApisSimuladas:
    """Responde como las APIs de entradas y eventos y registra las URLs pedidas."""

    def __init__(self):
        self.entradas = {ENTRADA_OK["codigo"]: ENTRADA_OK}
        self.eventos = {"1": EVENTO_OK}
        self.llamadas: list[str] = []
        self.falla: Exception | None = None  # para simular timeouts / caídas
        self.status_forzado: int | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.llamadas.append(str(request.url))
        if self.falla is not None:
            raise self.falla
        if self.status_forzado is not None:
            return httpx.Response(self.status_forzado, text="error interno")

        host, partes = request.url.host, request.url.path.strip("/").split("/")
        if host == "entradas.test" and partes[0] == "entradas":
            datos = self.entradas.get(partes[1])
        elif host == "eventos.test" and partes[0] == "eventos":
            datos = self.eventos.get(partes[1])
        else:
            datos = None
        if datos is None:
            return httpx.Response(404, json={"error": "NO_ENCONTRADO"})
        return httpx.Response(200, content=json.dumps(datos), headers={"Content-Type": "application/json"})


@pytest.fixture
def apis(monkeypatch) -> ApisSimuladas:
    monkeypatch.setenv("ENTRADAS_URL", ENTRADAS_URL)
    monkeypatch.setenv("EVENTOS_URL", EVENTOS_URL)
    return ApisSimuladas()


@pytest.fixture
def cliente(apis: ApisSimuladas):
    async def cliente_http_simulado():
        async with httpx.AsyncClient(transport=httpx.MockTransport(apis)) as c:
            yield c

    app.dependency_overrides[obtener_cliente_http] = cliente_http_simulado
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
