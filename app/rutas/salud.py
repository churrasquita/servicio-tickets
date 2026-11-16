from fastapi import APIRouter

router = APIRouter(tags=["salud"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "servicio": "tickets"}
