# Clasificación de los servicios con la tabla de decisión

## La regla (semana 2)

Se aplican las preguntas **en orden**; la **primera respuesta afirmativa** determina el tipo.

| # | Pregunta | Si la respuesta es «sí» |
|---|---|---|
| P1 | ¿Es dueño exclusivo de una tabla o colección de negocio? | **Core** |
| P2 | ¿Su razón de existir es coordinar dos o más servicios core? | **Compuesto** |
| P3 | ¿Existe únicamente para dar forma a la respuesta de un canal? | **API** |
| P4 | ¿Solo enruta, autentica o limita el tráfico? | **Perimetral** |
| P5 | ¿Ninguna de las anteriores? | El corte está mal planteado |

Y la taxonomía que la respalda:

| Tipo | Posee datos | Llama a otros servicios de negocio | Decide reglas |
|---|---|---|---|
| Core | Sí, en exclusiva | No | Sí, las de su dominio |
| Compuesto | No de dominio | Sí, a varios core | Sí, de orquestación |
| API | No | Sí, a compuestos y core | No, solo adapta y agrega |

## Resumen

| Servicio | P1 | P2 | P3 | P4 | Tipo |
|---|---|---|---|---|---|
| `ms-catalogo` | **Sí** | — | — | — | **Core** |
| `ms-inventario` | **Sí** | — | — | — | **Core** |
| `ms-pagos` | **Sí** | — | — | — | **Core** (con llamadas salientes) |
| `ms-pedidos` | No | **Sí** | — | — | **Compuesto** |
| `bff-web` | No | No | **Sí** | — | **API** |
| `gateway` (semana 7) | No | No | No | **Sí** | **Perimetral** |
| `ms-confiabilidad` | No* | No | No | No | **Core sin estado** (*ver análisis*) |

## Justificación, pregunta por pregunta

### `ms-catalogo` → Core

- **P1: sí.** Es el único dueño de la colección *productos* (`sku`, `nombre`, `precio`, `categoria`, `activo`). Nadie más escribe precios: `ms-pedidos`, `ms-pagos` y `bff-web` solo los **leen** por `GET /api/v1/productos/{sku}`.
- Se detiene aquí. Confirmación con la taxonomía: no llama a ningún servicio de negocio y decide sus propias reglas (SKU único → `409`, límite de página).

### `ms-inventario` → Core

- **P1: sí.** Dueño exclusivo de *existencias* y *reservas* (`cantidad`, `reservadas`, `disponible`). La regla «no vender lo que no se tiene» vive solo aquí (`409` al reservar más del disponible).
- Confirmación: no llama a otros servicios; sus tres réplicas no cambian el tipo, solo la disponibilidad.

### `ms-pagos` → Core (con llamadas salientes)

- **P1: sí.** Es dueño exclusivo de las *autorizaciones* y de sus claves de idempotencia (`RepositorioAutorizaciones`, `AlmacenIdempotencia` en `servicios/ms-pagos/app/repositorios/`). Decide reglas de su dominio: tope `PAGOS_MONTO_MAXIMO` → `402`, anulación idempotente.
- La tabla se detiene en P1, pero la taxonomía dice que un core **no** llama a otros servicios de negocio, y `ms-pagos` sí llama a catálogo e inventario. Es la **excepción definida en la semana 3** (`CONVENCIONES.md` §2): las llamadas son de **solo lectura** (precio y disponible), no coordinan ni compensan nada y no cambian el estado de nadie. Por eso sigue siendo core y no compuesto: su razón de existir es *autorizar pagos*, no *coordinar* servicios.
- **Riesgo aceptado:** al llamar a dos servicios, su disponibilidad es como mucho `A_pagos × A_catalogo × A_inventario`. Se mitiga con la llamada en paralelo, timeouts de 3 s y el atajo de `reserva_id` (con reserva previa solo consulta catálogo).

### `ms-pedidos` → Compuesto

- **P1: no.** Guarda el *estado del pedido* y sus claves de idempotencia, pero **no** es dueño de productos ni de existencias: el precio lo consulta en catálogo, el stock lo reserva en inventario y el cobro lo autoriza pagos. Sus datos son de coordinación, no del dominio de otro.
- **P2: sí.** Existe para coordinar **tres** servicios core en una saga (T1 catálogo ∥ T1' inventario → T2 pagos → T3 confirmar) y compensar si algo falla. Decide reglas de **orquestación** (orden, compensación, idempotencia), no de dominio.
- **¿Por qué no es core?** Porque no es dueño exclusivo de ninguna colección de negocio de la que otros dependan; si mañana catálogo cambia el precio, pedidos no tiene autoridad sobre él.
- **¿Por qué no es API?** Porque **sí decide**: calcula el total, reserva, cobra y compensa. Un servicio API solo adapta y agrega; si `ms-pedidos` desapareciera, la regla «nunca queda una reserva huérfana» desaparecería con él.

### `bff-web` → API

- **P1: no.** No tiene base de datos.
- **P2: no.** Aunque llama a catálogo, inventario y pedidos, no coordina una operación de negocio: la compra la delega completa a `ms-pedidos` (`POST /api/v1/pedidos`).
- **P3: sí.** Existe para que la app móvil haga **una** llamada en vez de seis: agrega la ficha (catálogo ∥ inventario), oculta campos internos (`reservadas`, `bodega`, `reserva_id`) y degrada con elegancia (`"disponible": null, "degradado": true`). No calcula totales ni valida stock.

### `gateway` → Perimetral (fuera del parcial)

- P1, P2 y P3: no. **P4: sí:** solo enruta, termina TLS, limita la tasa y autentica. No es un cuarto tipo de servicio de negocio, es infraestructura (semana 7).

### `ms-confiabilidad` → Core sin estado (análisis honesto)

Aplicada al pie de la letra, la tabla **no** lo clasifica:

- **P1: no** en sentido estricto: no guarda ninguna tabla ni colección (es sin estado).
- **P2: no:** no llama a ningún servicio.
- **P3: no:** no da forma a la respuesta de un canal.
- **P4: no:** no enruta tráfico.
- → caería en **P5, «el corte está mal planteado»**.

**Por qué igual se clasifica como core:** P1 está formulada para servicios con persistencia. La taxonomía de la que se deriva la tabla tiene tres criterios, y `ms-confiabilidad` cumple los tres del core: **posee su dominio** (el conocimiento de confiabilidad: fórmulas de disponibilidad en serie y en paralelo, MTBF, presupuesto de error, cola larga), **no llama a otros servicios de negocio** y **decide las reglas de su dominio** (qué valores son válidos → `422`). Su «dato propio» son las reglas de cálculo, no filas. Por eso `CONVENCIONES.md` lo llama *core sin estado*.

**Lo que esta discrepancia enseña:** la tabla es una herramienta de decisión rápida, no una definición. Si un servicio cae en P5 hay que preguntarse si el corte es malo; aquí el corte es bueno (un contexto delimitado claro, que cambia por razones distintas a los demás y se despliega solo), así que lo que se ajusta es la lectura de P1. Si en cambio un servicio cayera en P5 por ser, por ejemplo, un `ms-utilidades` que formatea fechas para todos, la conclusión correcta sería que no merece ser un servicio.
