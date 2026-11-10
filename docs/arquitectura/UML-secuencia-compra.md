# UML · Secuencias de `POST /bff/v1/compras`

Tres escenarios de la compra en un solo paso (requerimiento 3). `ms-pedidos` **orquesta** la saga: decide el orden, espera las respuestas y compensa cuando algo falla.

Datos de ejemplo de `CONVENCIONES.md`: `CAF-001` cuesta 38 500,00 y tiene 100 unidades; `PAGOS_MONTO_MAXIMO = 1 000 000,00`.

## 1. Flujo feliz

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente (app móvil)
    participant B as bff-web :8080
    participant P as ms-pedidos :8003
    participant CA as ms-catalogo :8001
    participant I as ms-inventario (réplica elegida)
    participant PA as ms-pagos :8004

    C->>B: POST /bff/v1/compras {sku CAF-001, unidades 2, medio_pago tarjeta}<br/>Idempotency-Key: k-123
    B->>P: POST /api/v1/pedidos (mismo cuerpo, reenvía Idempotency-Key tal cual)
    Note over P: ¿k-123 ya procesada? No → inicia la saga
    par T1 y T1' en paralelo (asyncio.gather)
        P->>CA: GET /api/v1/productos/CAF-001
        CA-->>P: 200 {precio 38500.00}
    and
        P->>I: POST /api/v1/existencias/CAF-001/reservas {unidades 2}
        I-->>P: 201 {reserva_id r-9, disponible 98}
    end
    P->>PA: T2 · POST /api/v1/autorizaciones {sku, unidades 2, medio_pago, reserva_id r-9}
    Note over PA: Con reserva_id solo consulta el precio
    PA->>CA: GET /api/v1/productos/CAF-001
    CA-->>PA: 200 {precio 38500.00}
    Note over PA: total = 77000.00 ≤ 1000000.00
    PA-->>P: 201 {autorizacion_id a-7, estado AUTORIZADA}
    Note over P: T3 · guarda el pedido CONFIRMADO, registra k-123<br/>y emite el evento PedidoConfirmado (log estructurado)
    P-->>B: 201 {pedido_id, total 77000.00, estado CONFIRMADO, reserva_id, autorizacion_id}
    B-->>C: 201 {pedido_id, total, estado, mensaje} (sin campos internos)
```

Un reintento con `Idempotency-Key: k-123` devuelve el **mismo** `pedido_id` y `201` sin volver a reservar ni a cobrar.

## 2. Pago rechazado con compensación

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant B as bff-web
    participant P as ms-pedidos
    participant CA as ms-catalogo
    participant I as ms-inventario
    participant PA as ms-pagos

    C->>B: POST /bff/v1/compras {sku CAF-001, unidades 30}
    B->>P: POST /api/v1/pedidos
    par T1 y T1'
        P->>CA: GET /api/v1/productos/CAF-001
        CA-->>P: 200 {precio 38500.00}
    and
        P->>I: POST /api/v1/existencias/CAF-001/reservas {unidades 30}
        I-->>P: 201 {reserva_id r-10, disponible 70}
    end
    P->>PA: POST /api/v1/autorizaciones {..., unidades 30, reserva_id r-10}
    PA->>CA: GET /api/v1/productos/CAF-001
    CA-->>PA: 200 {precio 38500.00}
    Note over PA: total = 1155000.00 > PAGOS_MONTO_MAXIMO
    PA-->>P: 402 {detail "Pago rechazado", estado RECHAZADA}
    rect rgb(255, 235, 230)
        Note over P,I: Compensación · la reserva no puede quedar huérfana
        P->>I: DELETE /api/v1/existencias/CAF-001/reservas/r-10
        I-->>P: 204 (disponible vuelve a 100)
        Note over P: guarda el pedido ANULADO y emite PedidoAnulado
    end
    P-->>B: 402 {detail "Pago rechazado", estado RECHAZADA}
    B-->>C: 402 (se propaga: es un error de negocio)
```

Entre el `201` de la reserva y el `204` de la liberación, el inventario mostró 70 disponibles durante unos milisegundos: es la **consistencia eventual** que la saga acepta a cambio de no usar una transacción distribuida.

## 3. Dependencia caída (`503`)

`ms-pagos` está apagado (conexión rechazada) después de que la reserva ya se hizo.

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant B as bff-web
    participant P as ms-pedidos
    participant CA as ms-catalogo
    participant I as ms-inventario
    participant PA as ms-pagos (caído)

    C->>B: POST /bff/v1/compras {sku CAF-001, unidades 2}
    B->>P: POST /api/v1/pedidos
    par T1 y T1'
        P->>CA: GET /api/v1/productos/CAF-001
        CA-->>P: 200
    and
        P->>I: POST /api/v1/existencias/CAF-001/reservas
        I-->>P: 201 {reserva_id r-11}
    end
    P-xPA: POST /api/v1/autorizaciones
    Note over P,PA: httpx.ConnectError (connection refused)<br/>connect=2.0 s → falla en milisegundos, no espera
    rect rgb(255, 235, 230)
        Note over P,I: Compensación
        P->>I: DELETE /api/v1/existencias/CAF-001/reservas/r-11
        I-->>P: 204
        Note over P: pedido ANULADO · PedidoAnulado
    end
    P-->>B: 503 {detail "ms-pagos no disponible"}
    B-->>C: 503 {detail "ms-pagos no disponible"} en menos de 4 s
```

### Variante verificada en el código: `ms-pagos` con `ms-inventario` caído

Es la verificación 10 del E2E y la que hoy se puede reproducir con el código de `main` (`servicios/ms-pagos/tests/test_dependencia_caida_real.py`):

```mermaid
sequenceDiagram
    autonumber
    participant X as Consumidor (curl o ms-pedidos)
    participant PA as ms-pagos :8004
    participant CA as ms-catalogo :8001
    participant I as ms-inventario (apagado)

    X->>PA: POST /api/v1/autorizaciones {sku CAF-001, unidades 1} (sin reserva_id)
    par asyncio.gather(return_exceptions=True)
        PA->>CA: GET /api/v1/productos/CAF-001
        CA-->>PA: 200 {precio}
    and
        PA-xI: GET /api/v1/existencias/CAF-001
        Note over PA,I: ConnectError → DependenciaNoDisponible("ms-inventario")
    end
    Note over PA: main.py traduce la excepción de dominio a HTTP
    PA-->>X: 503 {detail "ms-inventario no disponible"} (medido: 0,005 s)
```

## Qué ve el cliente en cada fallo

| Fallo | Compensación | Respuesta final |
|---|---|---|
| SKU inexistente (T1 → 404) y la reserva sí se hizo | libera la reserva | `404 No existe el producto con SKU X` |
| Stock insuficiente (T1' → 409) | nada que compensar | `409` con `sku`, `solicitado`, `disponible` |
| Pago rechazado (T2 → 402) | libera la reserva | `402 Pago rechazado` |
| `ms-pagos` caído o lento (T2 → 503/504) | libera la reserva | `503`/`504` con el nombre del servicio |
| `ms-inventario` responde 5xx | nada que compensar | `502 ms-inventario respondio mal` |
