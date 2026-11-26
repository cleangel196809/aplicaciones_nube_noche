from typing import Optional
from app.esquemas import PedidoSalida
from app.repositorios.base import RepositorioPedidos

class RepositorioMemoriaPedidos(RepositorioPedidos):
    def __init__(self):
        self._pedidos: dict[str, PedidoSalida] = {}
        self._idempotencia: dict[str, PedidoSalida] = {}

    async def guardar(self, pedido: PedidoSalida) -> None:
        self._pedidos[pedido.id] = pedido

    async def obtener_por_id(self, pedido_id: str) -> Optional[PedidoSalida]:
        return self._pedidos.get(pedido_id)

    async def obtener_por_idempotency_key(self, key: str) -> Optional[PedidoSalida]:
        return self._idempotencia.get(key)

    async def guardar_con_key(self, key: str, pedido: PedidoSalida) -> None:
        self._pedidos[pedido.id] = pedido
        self._idempotencia[key] = pedido