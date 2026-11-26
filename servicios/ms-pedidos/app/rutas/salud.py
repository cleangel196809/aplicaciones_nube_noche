from fastapi import APIRouter
from app.config import get_configuracion

router = APIRouter(tags=["Salud"])

@router.get("/health")
def salud():
    return {"estado": "activo", "servicio": "ms-pedidos"}

@router.get("/diagnostico")
def diagnostico():
    cfg = get_configuracion()
    return {
        "entorno": cfg.entorno,
        "nivel_log": cfg.nivel_log,
        "servicio": cfg.nombre_servicio
    }