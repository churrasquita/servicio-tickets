"""Punto de entrada. Railway lo ejecuta con:

    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

from app import crear_app

app = crear_app()
