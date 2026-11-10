# Arquitectura de MercadoAndino (A11)

Arquitectura **objetivo** (C4 y UML) y decisiones (ADR) de la plataforma, contrastadas con la arquitectura **de implementación** (el código en `servicios/` y `plataforma/`). Cuando las dos divergen, manda el código: las divergencias encontradas y cómo se cerraron están en [`trazabilidad.md`](trazabilidad.md#3-revisión-cruzada-contra-el-código).

Todos los diagramas están en **Mermaid** y GitHub los dibuja al abrir cada archivo.

## Cómo leer los diagramas C4

| Nivel | Archivo | Pregunta que responde | Audiencia |
|---|---|---|---|
| 1 · Contexto | [`C4-1-contexto.md`](C4-1-contexto.md) | ¿Qué es el sistema, quién lo usa y con qué sistemas externos habla? | Cliente, gerencia, personas no técnicas |
| 2 · Contenedores | [`C4-2-contenedores.md`](C4-2-contenedores.md) | ¿En qué piezas desplegables se divide, con qué tecnología y cómo se comunican? | Desarrollo, operaciones, revisión de arquitectura |
| 3 · Componentes | [`C4-3-componentes-ms-pedidos.md`](C4-3-componentes-ms-pedidos.md) | ¿Cómo está organizado por dentro un contenedor y qué hace cada parte? | Quienes programan o revisan ese servicio |

El nivel 4 (código) no se dibuja: es el propio código.

## Contenido

| Archivo | Contenido |
|---|---|
| [`C4-1-contexto.md`](C4-1-contexto.md) | Sistema, actores y sistemas externos |
| [`C4-2-contenedores.md`](C4-2-contenedores.md) | Un contenedor por servicio con puerto, tipo y almacén de datos; Consul; `config-repo` |
| [`C4-3-componentes-ms-pedidos.md`](C4-3-componentes-ms-pedidos.md) | Componentes internos del orquestador de la saga |
| [`UML-componentes.md`](UML-componentes.md) | Interfaces `ICatalogo`, `IInventario`, `IPagos`, `IPedidos` como contratos, y los `Protocol` reales de `ms-pagos` |
| [`UML-secuencia-compra.md`](UML-secuencia-compra.md) | `POST /bff/v1/compras`: flujo feliz, pago rechazado con compensación y dependencia caída (`503`) |
| [`UML-despliegue.md`](UML-despliegue.md) | Nodo, Docker Compose, tres réplicas de inventario y Consul |
| [`clasificacion-servicios.md`](clasificacion-servicios.md) | Tabla de decisión de la semana 2 aplicada a cada servicio, pregunta por pregunta |
| [`trazabilidad.md`](trazabilidad.md) | Requerimiento → API, doce factores con evidencia y **revisión cruzada** |
| [`glosario.md`](glosario.md) | Lenguaje del dominio; por qué «producto» cambia de significado entre contextos |
| [`adr/ADR-001-monorepo.md`](adr/ADR-001-monorepo.md) | Monorepo didáctico frente a un repositorio por servicio |
| [`adr/ADR-002-descubrimiento.md`](adr/ADR-002-descubrimiento.md) | Consul con balanceo en el cliente frente al `Service` de Kubernetes; CAP |
| [`adr/ADR-003-comunicacion.md`](adr/ADR-003-comunicacion.md) | REST con `httpx` frente a gRPC y mensajería; orquestación frente a coreografía |

## Leyenda común

| Color | Tipo de servicio |
|---|---|
| 🟩 verde | API (`bff-web`) |
| 🟧 naranja | Compuesto (`ms-pedidos`) |
| 🟦 azul | Core (`ms-catalogo`, `ms-inventario`, `ms-pagos`, `ms-confiabilidad`) |
| 🟪 morado | Infraestructura (Consul, `config-repo`) |
| borde punteado | Fuera del parcial (gateway, pasarela de pagos) |

Las flechas llevan **verbo y ruta** (por ejemplo «reserva unidades · `POST /api/v1/existencias/{sku}/reservas`»). Las continuas son llamadas de negocio; las punteadas, de plataforma.

## Fuentes

- [`docs/CONVENCIONES.md`](../CONVENCIONES.md): puertos, prefijos, formato de errores e interfaces compartidas.
- Las fichas de [`paquetes/`](../../paquetes/): contrato de cada servicio.
- El código integrado en `main`.

## Formato de las ADR

Cada ADR tiene: **contexto, decisión, alternativas consideradas y consecuencias** (lo que se gana y lo que se paga). Una ADR aceptada no se edita para cambiar la decisión: se escribe otra que la reemplaza.
