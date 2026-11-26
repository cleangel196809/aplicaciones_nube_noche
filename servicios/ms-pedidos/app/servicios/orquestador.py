import uuid
from app.esquemas import PedidoEntrada, PedidoSalida
from app.repositorios.base import RepositorioPedidos
from app.clientes.cliente_externo import ClienteExterno

class ServicioPedidos:
    def __init__(self, repo: RepositorioPedidos, cliente: ClienteExterno):
        self.repo = repo
        self.cliente = cliente

    async def crear_pedido(self, entrada: PedidoEntrada, idempotency_key: str | None) -> PedidoSalida:
        if idempotency_key:
            existente = await self.repo.obtener_por_idempotency_key(idempotency_key)
            if existente:
                return existente

        reservas_realizadas = []
        total = 0.0

        try:
            for item in entrada.items:
                precio = await self.cliente.obtener_precio(item.sku)
                total += precio * item.cantidad
                reserva = await self.cliente.reservar_inventario(item.sku, item.cantidad)
                res_id = reserva.get("reserva_id") or reserva.get("id")
                if res_id:
                    reservas_realizadas.append(res_id)

            pago_key = idempotency_key or str(uuid.uuid4())
            await self.cliente.autorizar_pago(total, pago_key)

            pedido_id = str(uuid.uuid4())
            pedido = PedidoSalida(
                id=pedido_id,
                cliente_id=entrada.cliente_id,
                items=entrada.items,
                total=total,
                estado="CONFIRMADO"
            )

            if idempotency_key:
                await self.repo.guardar_con_key(idempotency_key, pedido)
            else:
                await self.repo.guardar(pedido)

            return pedido

        except Exception as exc:
            for res_id in reservas_realizadas:
                await self.cliente.liberar_inventario(res_id)
            raise exc