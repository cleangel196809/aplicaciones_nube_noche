from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.config import get_configuracion
from app.rutas import pedidos, salud
from app.errores import ExcepcionDominio, ErrorDependencia

@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_configuracion()
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()

cfg = get_configuracion()
app = FastAPI(
    title="MercadoAndino - ms-pedidos",
    version="1.0.0",
    docs_url="/docs" if cfg.docs_habilitada else None,
    lifespan=lifespan
)

app.include_router(salud.router)
app.include_router(pedidos.router)

@app.exception_handler(ExcepcionDominio)
async def manejar_excepcion_dominio(request: Request, exc: ExcepcionDominio):
    content = {"detail": exc.mensaje}
    if exc.detalles:
        content.update(exc.detalles)
    return JSONResponse(status_code=exc.codigo_estado, content=content)

@app.exception_handler(ErrorDependencia)
async def manejar_error_dependencia(request: Request, exc: ErrorDependencia):
    return JSONResponse(
        status_code=exc.codigo_estado,
        content={"detail": exc.mensaje}
    )