# ADR-003 · REST con `httpx` y saga orquestada

- **Estado:** aceptada
- **Fecha:** 8 de noviembre de 2026
- **Autor:** Andrés Camilo Cortés Vela (A11)
- **Requerimientos:** R2 «no vender lo que no se tiene» y R3 «compra en un solo paso»

Esta ADR responde dos preguntas relacionadas: **cómo se hablan** los servicios y **quién coordina** la compra.

## Contexto

La compra toca tres servicios core con datos propios (catálogo, inventario, pagos). No hay una base de datos compartida, así que **no existe una transacción ACID** que abarque los tres. Hay que garantizar que nunca quede una reserva huérfana y que un reintento no cobre dos veces.

El alcance del parcial son las semanas 1 a 4: la mensajería asíncrona es de la semana 6 y la resiliencia con cortocircuito de la semana 5.

## Decisión 1 · Comunicación: REST/JSON síncrono con `httpx.AsyncClient`

- Contratos HTTP con JSON, documentados en `/openapi.json` de cada servicio.
- Un **único** `httpx.AsyncClient` por proceso, creado en el `lifespan`, con los **cuatro timeouts** explícitos (`connect=2, read=3, write=2, pool=1`; lectura de 8 s del BFF hacia pedidos).
- Llamadas independientes en **paralelo** con `asyncio.gather`.
- Fallos de red traducidos a `502` / `503` / `504` con el nombre del servicio; los de negocio (`404`, `409`, `402`) se propagan.

### Alternativas

| Alternativa | A favor | En contra |
|---|---|---|
| **REST + JSON con `httpx`** (elegida) | Legible con `curl`; contrato autodocumentado con FastAPI; lo cubren las semanas 1 a 4; depuración sencilla | Texto más pesado que binario; acoplamiento temporal: si el llamado está caído, la petición falla |
| **gRPC (HTTP/2 + Protobuf)** | Binario y rápido; contrato fuerte con `.proto`; *streaming* | Herramientas adicionales (generación de código); no se prueba con `curl`; fuera del temario del parcial; los navegadores no lo hablan directo (el BFF tendría que traducir igual) |
| **Mensajería (RabbitMQ / Kafka)** | Desacopla en el tiempo: si pagos está caído, el mensaje espera; absorbe picos | La app móvil quiere la respuesta **ya** («compra en un solo paso»); agrega un broker que operar; consistencia más difícil de explicar; es la semana 6 |

## Decisión 2 · Coordinación de la saga: orquestación en `ms-pedidos`

`ms-pedidos` (servicio compuesto) **orquesta**: T1 catálogo ∥ T1' reserva → T2 autorización (con `reserva_id`) → T3 confirmar; y si T2 falla, **compensa** liberando la reserva. Ver las [secuencias](../UML-secuencia-compra.md).

### Alternativas

| Alternativa | A favor | En contra |
|---|---|---|
| **Orquestación** (elegida) | Toda la lógica de la saga en un lugar: fácil de leer, probar y explicar; el orden y las compensaciones son explícitos; encaja con la llamada síncrona del cliente | `ms-pedidos` conoce a los tres core (acoplamiento de dependencias); es un punto de complejidad y, si cae, no hay compras |
| **Coreografía** (eventos: `ReservaCreada` → pagos escucha → `PagoAutorizado` → pedidos escucha…) | Ningún servicio central; cada uno reacciona; muy desacoplado | El flujo queda **repartido** entre servicios: difícil saber quién compensa qué; necesita mensajería (semana 6); difícil de depurar y de responder al cliente en la misma petición |
| **Transacción distribuida (2PC)** | Consistencia fuerte | Bloquea recursos entre servicios; un coordinador caído deja todo bloqueado; contradice la base de datos por servicio |

## Consecuencias

**Lo que se gana**

- Contratos simples y verificables con `curl` y pruebas con `httpx.MockTransport` (sin levantar las dependencias).
- Respuesta inmediata al cliente con el resultado final de la compra.
- Compensación explícita: «nunca queda una reserva huérfana» se lee en un solo archivo (`servicios/pedidos.py`).
- Idempotencia con `Idempotency-Key` en `POST /api/v1/pedidos` y `POST /api/v1/autorizaciones`: los reintentos son seguros.

**Lo que se paga**

- **Acoplamiento temporal:** la disponibilidad de la compra es el **producto** de las disponibilidades de la cadena. Con cinco servicios al 99,9 %: `0,999⁵ ≈ 99,5 %`, unos **215,6 min/mes** de indisponibilidad (cálculo de `ms-confiabilidad`).
- **Cola larga:** con 5 llamadas, la probabilidad de evitar el p99 en todas es `0,99⁵ ≈ 95 %`; 1 de cada 20 compras sufre la latencia del peor.
- **Consistencia eventual:** entre la reserva y la compensación, el disponible baja y luego vuelve.
- Si `ms-pedidos` se cae entre la reserva y la compensación, la reserva **sí** queda huérfana: haría falta un proceso de limpieza por expiración (trabajo futuro).

**Trabajo futuro (fuera del parcial):** cortocircuito y reintentos con retroceso (semana 5); eventos `PedidoConfirmado` / `PedidoAnulado` publicados en un broker (semana 6) para que otros contextos reaccionen sin acoplarse.
