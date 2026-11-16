# servicio-tickets — EventPass, Equipo 7

Servicio HTTP (FastAPI) que transforma una entrada ya emitida por el Equipo 5 en una
**imagen PNG de 384 px de ancho** para la impresora térmica, con el nombre del evento,
la fecha, el código y un **código de barras Code 128** con el código exacto de la entrada
(códigos numéricos de 20 dígitos).

Este repositorio contiene **solo el módulo del Equipo 7**; las APIs de entradas y
eventos, el Gateway y los demás componentes son de otros equipos.

La web (Equipo 6) muestra la imagen y el agente de impresión (Equipo 8) descarga
la misma imagen. El Gateway expone `/api/tickets/{codigo}` y reenvía a este servicio.

## Endpoints

| Método | Ruta | Respuesta |
| ------ | ---- | --------- |
| GET | `/health` | `200 {"status":"ok","servicio":"tickets"}` |
| GET | `/tickets/{codigo}` | `200` `Content-Type: image/png` |
| | | `404 {"error":"ENTRADA_NO_EXISTE","mensaje":"Entrada no encontrada"}` (sin imagen) |
| | | `502` / `504` JSON si la API de entradas o de eventos falla o no responde |

Documentación interactiva: `/docs`.

### Flujo de `GET /tickets/{codigo}`

1. `GET {ENTRADAS_URL}/entradas/{codigo}` → `{codigo, evento_id, estado}`. Si responde 404 → 404 JSON.
2. `GET {EVENTOS_URL}/eventos/{evento_id}` → `{nombre, fecha, ...}`.
3. Genera el PNG (384 px de ancho, alto según el contenido).
4. Responde `image/png`.

Diagrama de secuencia UML: [`docs/secuencia.puml`](docs/secuencia.puml).

### Errores (todos en JSON `{"error", "mensaje"}`)

| HTTP | `error` | Cuándo |
| ---- | ------- | ------ |
| 404 | `ENTRADA_NO_EXISTE` | La API de entradas responde 404 |
| 502 | `EVENTO_NO_EXISTE` | La entrada existe, pero su evento no |
| 502 | `SERVICIO_NO_DISPONIBLE` | No hay conexión con una API externa |
| 502 | `RESPUESTA_INVALIDA` | Una API externa responde 5xx, no-JSON o sin campos obligatorios |
| 504 | `SERVICIO_NO_RESPONDE` | Una API externa supera el tiempo de espera (`HTTP_TIMEOUT_SEGUNDOS`) |
| 500 | `CONFIGURACION_INCOMPLETA` | Falta `ENTRADAS_URL` o `EVENTOS_URL` |
| 422 | `CODIGO_NO_IMPRIMIBLE` | El código no cabe o no se puede codificar en Code 128 |

## Estructura

```
main.py                 # punto de entrada: app = crear_app()
app/
  __init__.py           # crea la app FastAPI y registra rutas y errores
  config.py             # ENTRADAS_URL, EVENTOS_URL, HTTP_TIMEOUT_SEGUNDOS
  errores.py            # errores del servicio -> respuestas JSON
  clientes/
    http.py             # GET + manejo de timeouts, caídas y respuestas inválidas
    entradas.py         # cliente de la API de entradas (Equipo 5)
    eventos.py          # cliente de la API de eventos
  ticket/
    imagen.py           # PNG 384 px + Code 128 (Pillow + python-barcode)
  rutas/
    salud.py            # GET /health
    tickets.py          # GET /tickets/{codigo}
tests/                  # pruebas con las APIs externas simuladas (mock)
docs/secuencia.puml     # diagrama de secuencia UML
```

### Sobre el código de barras

python-barcode calcula el patrón Code 128 y el servicio dibuja cada barra con un
**ancho entero de píxeles** y zona de silencio de 10 módulos, así la impresora
(203 dpi, 384 puntos de ancho en papel de 58 mm) no reescala la imagen.

Los códigos de entrada son **numéricos de 20 dígitos**. Code 128 (subconjunto C)
agrupa los dígitos de a dos, así que ocupan 145 módulos + 20 de silencio = 165:
caben **horizontales** en 384 px con 2 px por módulo (0,25 mm a 203 dpi, el mínimo
recomendado para un escáner de mano). Con letras, el máximo horizontal sería de 12
caracteres.

Respaldo: si un código no cabe horizontal con ≥ 2 px por módulo (p. ej. uno
alfanumérico largo), se dibuja **vertical**, a lo largo del ticket.

La prueba `tests/test_imagen.py` lee la imagen generada y comprueba que el patrón
dibujado es exactamente el del código y que cada módulo mide al menos 2 px.

## Ejecutar en local

Requisitos: Python 3.12 o superior.

```bash
python -m venv .venv
```

```bash
.venv/Scripts/activate        # Windows (Git Bash). En Linux/macOS: source .venv/bin/activate
```

```bash
pip install -r requirements-dev.txt
```

```bash
cp .env.example .env          # y ajustar ENTRADAS_URL / EVENTOS_URL
```

```bash
uvicorn main:app --reload --port 8000
```

Luego abrir <http://localhost:8000/health> o `http://localhost:8000/tickets/01234567890123456789`.

### Pruebas

```bash
python -m pytest -q
```

Las pruebas simulan las APIs de entradas y eventos con `httpx.MockTransport`
(no hacen llamadas reales) y verifican: PNG de 384 px, 404 JSON sin imagen y sin
consultar eventos, timeouts (504), caídas (502), configuración faltante (500) y
que el Code 128 contiene el código exacto.

## Solicitud de despliegue al docente (Railway)

> Profesor/a, solicitamos desplegar el servicio de tickets del **Equipo 7**:
>
> - **Repositorio:** https://github.com/churrasquita/servicio-tickets
> - **Rama:** `main`
> - **Lenguaje:** Python 3.12
> - **Dependencias:** `requirements.txt` — FastAPI, Uvicorn, httpx, **Pillow** (imagen PNG),
>   **python-barcode** (Code 128), python-dotenv
> - **Comando de inicio:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
> - **Variables de entorno:**
>   - `ENTRADAS_URL` = URL interna de la API de entradas (Equipo 5)
>   - `EVENTOS_URL` = URL interna de la API de eventos
>   - (opcional) `HTTP_TIMEOUT_SEGUNDOS` = 5
> - **Health check:** `GET /health`
>
> Por favor, compartir la URL pública del servicio con el Equipo 6.
