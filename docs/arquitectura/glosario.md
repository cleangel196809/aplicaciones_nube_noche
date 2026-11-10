# Glosario del dominio y contextos delimitados

Un **contexto delimitado** es la frontera dentro de la cual una palabra tiene un significado único. Cada servicio core es un contexto delimitado: por eso la misma palabra puede significar cosas distintas en dos servicios **sin que sea un error**.

## «Producto» no significa lo mismo en todas partes

| Contexto (servicio) | Qué es «producto» allí | Atributos que le importan | Qué **no** le importa |
|---|---|---|---|
| **Catálogo** (`ms-catalogo`) | Algo que se ofrece y se describe | `sku`, `nombre`, `precio`, `categoria`, `activo` | Cuántas unidades hay, quién lo compró |
| **Inventario** (`ms-inventario`) | Una **existencia** física en una bodega | `sku`, `bodega`, `cantidad`, `reservadas`, `disponible` | Nombre, precio, categoría |
| **Pedidos** (`ms-pedidos`) | Una **línea del pedido**: lo que un cliente pidió en un momento dado | `sku`, `unidades`, precio **congelado** al confirmar, `total` | Si el precio cambia después en catálogo |
| **Pagos** (`ms-pagos`) | Solo la base de un cobro | `sku`, `unidades`, `precio` → `total` | Nombre, categoría, bodega |
| **Canal web** (`bff-web`) | Una **ficha** para mostrar | `sku`, `nombre`, `categoria`, `precio` (texto), `disponible` | `reservadas`, `bodega`, identificadores internos |

**Por qué importa:** si existiera un único modelo `Producto` compartido por todos, un cambio que necesita inventario (por ejemplo, agregar `lote`) obligaría a desplegar catálogo, pedidos y pagos. Cada contexto tiene su propio modelo y se comunican solo por el **`sku`**, el identificador que todos comparten. Por la misma razón cada servicio define sus propios esquemas Pydantic y nunca reutiliza los de otro (ver la regla de A05).

**El precio congelado:** catálogo es dueño del precio *actual*; pedidos guarda el precio *al momento de la compra*. Si mañana el café sube, los pedidos de ayer no cambian. No es duplicación: son dos conceptos distintos.

## Términos

| Término | Contexto | Definición |
|---|---|---|
| **SKU** | todos | Código único de un producto (`CAF-001`). Es el idioma común entre contextos. |
| **Existencia** | Inventario | Registro de un SKU en una bodega con `cantidad` y `reservadas`. |
| **Disponible** | Inventario | `cantidad − reservadas`: lo que se puede reservar ya. |
| **Reserva** | Inventario | Unidades apartadas para un pedido aún no confirmado. Tiene `reserva_id` y se libera con `DELETE`. |
| **Autorización** | Pagos | Aprobación de un cobro por `total = precio × unidades`. Estados: `AUTORIZADA`, `ANULADA`. Un rechazo (`402`) no se guarda. |
| **Anulación** | Pagos | Paso de `AUTORIZADA` a `ANULADA`. Idempotente. |
| **Pedido** | Pedidos | Intención de compra coordinada por la saga. Estados: `CONFIRMADO`, `ANULADO`. |
| **Saga** | Pedidos | Secuencia de transacciones locales (reservar, autorizar, confirmar) en la que cada paso tiene una **compensación**, en vez de una transacción distribuida. |
| **Orquestación** | Pedidos | Estilo de saga en el que un servicio central (`ms-pedidos`) decide el orden y las compensaciones. Lo opuesto es la coreografía (ver [ADR-003](adr/ADR-003-comunicacion.md)). |
| **Compensación** | Pedidos | Acción que deshace el efecto de un paso ya hecho; aquí, liberar la reserva. |
| **Consistencia eventual** | Pedidos | Entre la reserva y la compensación el sistema está temporalmente inconsistente; al final converge. |
| **`Idempotency-Key`** | Pedidos, Pagos, BFF | Cabecera que identifica un intento. La misma clave devuelve la misma respuesta (mismo id, `201`) sin repetir el efecto. |
| **Ficha** | Canal web | Vista de producto para el cliente: catálogo + disponible. |
| **Degradación elegante** | Canal web | Si un dato secundario falla (disponible), se muestra lo demás con `"degradado": true` en vez de fallar todo. |
| **Instancia / réplica** | Plataforma | Una copia en ejecución de un servicio (`ms-inventario-1:8002`). Id único `nombre-host-puerto`. |
| **Peso** | Plataforma | Etiqueta `peso=N` en Consul: proporción de tráfico que recibe una réplica. |
| **Resolvedor** | Plataforma | Componente que pregunta a Consul por instancias **sanas** y las guarda en caché con TTL. |
| **Modo degradado (descubrimiento)** | Plataforma | Si Consul no responde, el resolvedor usa la última lista conocida. |
| **Disponibilidad (A)** | Confiabilidad | Fracción del tiempo en que el servicio funciona. En serie: `∏Aᵢ`; en paralelo: `1 − (1 − A)ⁿ`. |
| **MTBF / MTTR** | Confiabilidad | Tiempo medio entre fallas / tiempo medio de reparación. `A = MTBF / (MTBF + MTTR)`. |
| **Presupuesto de error** | Confiabilidad | `1 − SLO`: cuánta indisponibilidad se puede «gastar» en un mes. |
| **Perfil** | Configuración | Conjunto de valores por entorno (`local`, `dev`, `test`, `prod`) en `config-repo`. |
