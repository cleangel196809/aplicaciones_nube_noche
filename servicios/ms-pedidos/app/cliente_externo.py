import httpx
from app.errores import ErrorDependencia, ExcepcionDominio

class ClienteExterno:
    def __init__(self, client: httpx.AsyncClient, base_url_catalogo: str, base_url_inventario: str, base_url_pagos: str):
        self.client = client
        self.url_cat = base_url_catalogo
        self.url_inv = base_url_inventario
        self.url_pag = base_url_pagos
        self.timeout = httpx.Timeout(connect=2.0, read=3.0, write=2.0, pool=1.0)

    async def obtener_precio(self, sku: str) -> float:
        try:
            resp = await self.client.get(f"{self.url_cat}/productos/{sku}", timeout=self.timeout)
            if resp.status_code == 404:
                raise ExcepcionDominio(f"No existe el producto con SKU {sku}", 404)
            if resp.status_code >= 500:
                raise ErrorDependencia("ms-catalogo", 502, "ms-catalogo respondio mal")
            resp.raise_for_status()
            return float(resp.json().get("precio", 0.0))
        except httpx.ConnectError:
            raise ErrorDependencia("ms-catalogo", 503, "ms-catalogo no disponible")
        except httpx.ReadTimeout:
            raise ErrorDependencia("ms-catalogo", 504, "ms-catalogo no respondio")

    async def reservar_inventario(self, sku: str, cantidad: int) -> dict:
        try:
            resp = await self.client.post(
                f"{self.url_inv}/inventario/reservas",
                json={"sku": sku, "cantidad": cantidad},
                timeout=self.timeout
            )
            if resp.status_code == 409:
                data = resp.json()
                raise ExcepcionDominio(data.get("detail", f"Stock insuficiente para {sku}"), 409, data)
            if resp.status_code == 404:
                raise ExcepcionDominio(f"No existe el producto con SKU {sku}", 404)
            if resp.status_code >= 500:
                raise ErrorDependencia("ms-inventario", 502, "ms-inventario respondio mal")
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            raise ErrorDependencia("ms-inventario", 503, "ms-inventario no disponible")
        except httpx.ReadTimeout:
            raise ErrorDependencia("ms-inventario", 504, "ms-inventario no respondio")

    async def liberar_inventario(self, reserva_id: str) -> None:
        try:
            await self.client.delete(f"{self.url_inv}/inventario/reservas/{reserva_id}", timeout=self.timeout)
        except Exception:
            pass

    async def autorizar_pago(self, monto: float, idempotency_key: str) -> dict:
        headers = {"Idempotency-Key": idempotency_key}
        try:
            resp = await self.client.post(
                f"{self.url_pag}/pagos/autorizaciones",
                json={"monto": monto},
                headers=headers,
                timeout=self.timeout
            )
            if resp.status_code == 402:
                data = resp.json()
                raise ExcepcionDominio(data.get("detail", "Pago rechazado"), 402, data)
            if resp.status_code >= 500:
                raise ErrorDependencia("ms-pagos", 502, "ms-pagos respondio mal")
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            raise ErrorDependencia("ms-pagos", 503, "ms-pagos no disponible")
        except httpx.ReadTimeout:
            raise ErrorDependencia("ms-pagos", 504, "ms-pagos no respondio")