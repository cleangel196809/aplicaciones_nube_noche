from pydantic import BaseModel, Field
from typing import List

class ItemPedido(BaseModel):
    sku: str
    cantidad: int = Field(..., gt=0)

class PedidoEntrada(BaseModel):
    cliente_id: str
    items: List[ItemPedido]

class PedidoSalida(BaseModel):
    id: str
    cliente_id: str
    items: List[ItemPedido]
    total: float
    estado: str