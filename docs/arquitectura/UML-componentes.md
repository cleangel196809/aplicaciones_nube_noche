# UML · Diagrama de componentes e interfaces

**Qué muestra:** los componentes de negocio y los **contratos** (interfaces) que exponen y consumen. Un componente depende de una interfaz, nunca de la implementación de otro: así cada equipo pudo avanzar sin esperar al compañero.

En Python estas interfaces son `Protocol` (tipado estructural, sin herencia) en el lado del consumidor y contratos HTTP (`/openapi.json`) en el lado del proveedor.

```mermaid
classDiagram
    direction LR

    class ICatalogo {
        <<interface>>
        +GET /api/v1/productos/:sku ProductoRespuesta
        +GET /api/v1/productos?categoria=&limite= list
        +POST /api/v1/productos 201 · 409 · 422
        +PUT /api/v1/productos/:sku 200 · 404
        +DELETE /api/v1/productos/:sku 204 · 404
    }
    class IInventario {
        <<interface>>
        +GET /api/v1/existencias/:sku disponible
        +POST /api/v1/existencias/:sku/reservas 201 reserva_id · 409
        +DELETE /api/v1/existencias/:sku/reservas/:reserva_id 204
        +GET /api/v1/diagnostico instancia, puerto
    }
    class IPagos {
        <<interface>>
        +POST /api/v1/autorizaciones 201 · 402 · 404 · 409
        +GET /api/v1/autorizaciones/:id 200 · 404
        +PUT /api/v1/autorizaciones/:id/anulacion 200 idempotente
    }
    class IPedidos {
        <<interface>>
        +POST /api/v1/pedidos 201 CONFIRMADO · 402 · 404 · 409
        +GET /api/v1/pedidos/:pedido_id 200 · 404
        +GET /api/v1/pedidos?estado= list
        +GET /api/v1/diagnostico/inventario instancia, puerto
    }
    class IConfiabilidad {
        <<interface>>
        +POST /api/v1/disponibilidad/serie
        +POST /api/v1/disponibilidad/paralelo
        +POST /api/v1/mtbf/serie
        +POST /api/v1/presupuesto-error
    }
    class Resolvedor {
        <<Protocol>>
        +instancias() list~Instancia~
    }
    class Balanceador {
        <<Protocol>>
        +siguiente() Instancia
        +reportar_fallo(instancia) None
    }

    class ms_catalogo {
        <<component · core>>
    }
    class ms_inventario {
        <<component · core · 3 réplicas>>
    }
    class ms_pagos {
        <<component · core con llamadas salientes>>
    }
    class ms_pedidos {
        <<component · compuesto>>
    }
    class bff_web {
        <<component · API>>
        +GET /bff/v1/fichas/:sku
        +GET /bff/v1/catalogo
        +POST /bff/v1/compras
    }
    class ms_confiabilidad {
        <<component · core sin estado>>
    }
    class ResolvedorConsul {
        <<component · A08>>
    }
    class BalanceadorPonderado {
        <<component · A09>>
    }

    ms_catalogo ..|> ICatalogo : provee
    ms_inventario ..|> IInventario : provee
    ms_pagos ..|> IPagos : provee
    ms_pedidos ..|> IPedidos : provee
    ms_confiabilidad ..|> IConfiabilidad : provee
    ResolvedorConsul ..|> Resolvedor : implementa
    BalanceadorPonderado ..|> Balanceador : implementa

    bff_web ..> IPedidos : crea compras
    bff_web ..> ICatalogo : lee fichas
    bff_web ..> IInventario : lee disponible
    ms_pedidos ..> ICatalogo : consulta precio
    ms_pedidos ..> IInventario : reserva y libera
    ms_pedidos ..> IPagos : autoriza
    ms_pagos ..> ICatalogo : consulta precio
    ms_pagos ..> IInventario : verifica disponible
    ms_pedidos ..> Balanceador : elige réplica
    bff_web ..> Balanceador : elige réplica
    BalanceadorPonderado ..> Resolvedor : obtiene instancias sanas
```

**Notación:** `..|>` = realiza/provee la interfaz · `..>` = depende de (usa) la interfaz. Dentro de las clases, `:sku` equivale al parámetro de ruta `{sku}` (Mermaid no admite llaves en los miembros).

## Dentro de `ms-pagos` (implementado)

Así se ven los contratos del lado del consumidor en el código real de `servicios/ms-pagos/app/`:

```mermaid
classDiagram
    direction LR
    class FuentePrecios {
        <<Protocol>>
        +precio(sku) Decimal
    }
    class FuenteDisponible {
        <<Protocol>>
        +disponible(sku) int
    }
    class RepositorioAutorizaciones {
        <<Protocol>>
        +guardar(autorizacion) None
        +obtener(autorizacion_id) Autorizacion
    }
    class AlmacenIdempotencia {
        <<Protocol>>
        +buscar(clave) str
        +registrar(clave, autorizacion_id) None
        +bloqueo(clave) Lock
    }
    class ServicioAutorizaciones {
        +autorizar(solicitud, clave_idempotencia) ResultadoAutorizacion
        +obtener(autorizacion_id) Autorizacion
        +anular(autorizacion_id) Autorizacion
    }
    class ClienteCatalogo
    class ClienteInventario
    class RepositorioAutorizacionesMemoria
    class AlmacenIdempotenciaMemoria

    ServicioAutorizaciones ..> FuentePrecios
    ServicioAutorizaciones ..> FuenteDisponible
    ServicioAutorizaciones ..> RepositorioAutorizaciones
    ServicioAutorizaciones ..> AlmacenIdempotencia
    ClienteCatalogo ..|> FuentePrecios
    ClienteInventario ..|> FuenteDisponible
    RepositorioAutorizacionesMemoria ..|> RepositorioAutorizaciones
    AlmacenIdempotenciaMemoria ..|> AlmacenIdempotencia
```

`ServicioAutorizaciones` no sabe si el precio viene de HTTP o de un doble de prueba: por eso `tests/test_servicio.py` lo prueba sin servidor. Es el **principio de inversión de dependencias** aplicado con `Protocol`.
