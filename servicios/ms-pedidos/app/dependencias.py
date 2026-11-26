from fastapi import Request
from app.repositorios.memoria import RepositorioMemoriaPedidos
from app.clientes.cliente_externo import ClienteExterno
from app.servicios.orquestador import ServicioPedidos
from app.config import get_configuracion

_repo_global = RepositorioMemoriaPedidos()

def get_servicio_pedidos(request: Request) -> ServicioPedidos:
    client = request.app.state.http_client
    cfg = get_configuracion()
    cliente_ext = ClienteExterno(client, cfg.url_catalogo, cfg.url_inventario, cfg.url_pagos)
    return ServicioPedidos(_repo_global, cliente_ext)