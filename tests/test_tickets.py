import io

import httpx
from PIL import Image

from tests.conftest import ENTRADAS_URL, EVENTOS_URL


def test_health(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ticket_existente_devuelve_png_de_384px(cliente, apis):
    r = cliente.get("/tickets/12345678901234567890")

    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content.startswith(b"\x89PNG\r\n\x1a\n")
    imagen = Image.open(io.BytesIO(r.content))
    assert imagen.format == "PNG"
    assert imagen.width == 384
    assert imagen.height > 200
    # Se consultó primero entradas y después eventos con el evento_id recibido
    assert apis.llamadas == [
        f"{ENTRADAS_URL}/entradas/12345678901234567890",
        f"{EVENTOS_URL}/eventos/1",
    ]


def test_entrada_inexistente_devuelve_404_json_sin_imagen(cliente, apis):
    r = cliente.get("/tickets/99999999999999999999")

    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"error": "ENTRADA_NO_EXISTE", "mensaje": "Entrada no encontrada"}
    # No se consulta la API de eventos ni se genera imagen
    assert apis.llamadas == [f"{ENTRADAS_URL}/entradas/99999999999999999999"]


def test_api_entradas_no_responde_da_504(cliente, apis):
    apis.falla = httpx.ReadTimeout("timeout")
    r = cliente.get("/tickets/12345678901234567890")
    assert r.status_code == 504
    assert r.json()["error"] == "SERVICIO_NO_RESPONDE"
    assert "entradas" in r.json()["mensaje"]


def test_api_caida_da_502(cliente, apis):
    apis.falla = httpx.ConnectError("sin conexión")
    r = cliente.get("/tickets/12345678901234567890")
    assert r.status_code == 502
    assert r.json()["error"] == "SERVICIO_NO_DISPONIBLE"


def test_api_con_error_500_da_502(cliente, apis):
    apis.status_forzado = 500
    r = cliente.get("/tickets/12345678901234567890")
    assert r.status_code == 502
    assert r.json()["error"] == "RESPUESTA_INVALIDA"


def test_evento_inexistente_da_502(cliente, apis):
    apis.eventos.clear()
    r = cliente.get("/tickets/12345678901234567890")
    assert r.status_code == 502
    assert r.json()["error"] == "EVENTO_NO_EXISTE"


def test_sin_variables_de_entorno_da_500(cliente, monkeypatch):
    monkeypatch.delenv("ENTRADAS_URL")
    r = cliente.get("/tickets/12345678901234567890")
    assert r.status_code == 500
    assert r.json() == {
        "error": "CONFIGURACION_INCOMPLETA",
        "mensaje": "Falta configurar la variable ENTRADAS_URL",
    }
