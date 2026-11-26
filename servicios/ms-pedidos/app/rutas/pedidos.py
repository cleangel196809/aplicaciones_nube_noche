from fastapi import APIRouter, Depends, Header, status, Response
from typing import Annotated
from app.esquemas import PedidoEntrada, PedidoSalida
from app.servicios.orquestador import ServicioPedidos
from app.dependencias import get_servicio_pedidos

router = APIRouter(prefix="/api/v1/pedidos", tags=["Pedidos"])

@router.post("", status_code=status.HTTP_201_CREATED, response_model=PedidoSalida)
async def crear_pedido(
    entrada: PedidoEntrada,
    response: Response,
    servicio: Annotated[ServicioPedidos, Depends(get_servicio_pedidos)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None
):
    pedido = await servicio.crear_pedido(entrada, idempotency_key)
    response.headers["Location"] = f"/api/v1/pedidos/{pedido.id}"
    return pedido