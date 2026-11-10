# C4 · Nivel 2 · Contenedores

**Pregunta que responde:** ¿en qué piezas desplegables se divide MercadoAndino, qué tecnología usa cada una y cómo se comunican?
**Audiencia:** el equipo de desarrollo y operaciones; el docente en la revisión de arquitectura.

Cada caja es un **contenedor C4**: un proceso con su propio ciclo de vida, su propia imagen Docker y, cuando es *core*, su propio almacén de datos.

```mermaid
flowchart TB
    cliente(["👤 Cliente web / app móvil"])
    operador(["👤 Operador"])

    subgraph mercado["MercadoAndino · docker compose (red interna)"]
        direction TB
        gateway["gateway :8000<br/><b>Perimetral</b> · semana 7<br/>FUERA DEL PARCIAL"]

        bff["<b>bff-web</b> :8080<br/><b>API</b> · FastAPI<br/>Da forma a la respuesta del canal.<br/>No decide reglas. Sin datos de dominio"]

        pedidos["<b>ms-pedidos</b> :8003<br/><b>Compuesto</b> · FastAPI<br/>Orquesta la saga de compra"]
        db_pedidos[("Pedidos y claves de idempotencia<br/>memoria (local) → PostgreSQL propio (dev/prod)")]

        catalogo["<b>ms-catalogo</b> :8001<br/><b>Core</b> · FastAPI<br/>Productos, precios y categorías"]
        db_catalogo[("Productos<br/>memoria (local) → PostgreSQL propio")]

        inventario["<b>ms-inventario</b> ×3<br/>:8002 · :8012 · :8022<br/><b>Core</b> · FastAPI<br/>Existencias y reservas"]
        db_inventario[("Existencias y reservas<br/>memoria por réplica → PostgreSQL propio")]

        pagos["<b>ms-pagos</b> :8004<br/><b>Core con llamadas salientes</b> · FastAPI<br/>Autoriza y anula pagos"]
        db_pagos[("Autorizaciones y claves de idempotencia<br/>memoria (local) → PostgreSQL propio")]

        confiabilidad["<b>ms-confiabilidad</b> :8005<br/><b>Core sin estado</b> · FastAPI<br/>Disponibilidad, MTBF y presupuesto de error"]

        consul{{"<b>Consul</b> :8500 (HTTP/UI) · :8600/udp (DNS)<br/><b>Infraestructura</b><br/>Los servicios conectados se registran al arrancar<br/>(PUT /v1/agent/service/register, check a /health cada 10 s)<br/>y se cancelan en el finally del lifespan.<br/>ms-pagos NO se registra (su ficha no lo exige)"}}
    end

    config[("<b>config-repo</b> (Git)<br/>default.yaml + perfil dev/test/prod<br/>cargar_config.py → variables de entorno")]

    cliente -->|"GET /bff/v1/fichas/{sku}<br/>POST /bff/v1/compras"| bff
    cliente -.->|"futuro: entrará por aquí"| gateway
    gateway -.-> bff

    bff -->|"crea la compra<br/>POST /api/v1/pedidos<br/>(reenvía Idempotency-Key)"| pedidos
    bff -->|"arma la ficha (en paralelo)<br/>GET /api/v1/productos/{sku}"| catalogo
    bff -->|"arma la ficha (en paralelo)<br/>GET /api/v1/existencias/{sku}"| inventario

    pedidos -->|"consulta el precio<br/>GET /api/v1/productos/{sku}"| catalogo
    pedidos -->|"reserva y libera unidades<br/>POST .../existencias/{sku}/reservas<br/>DELETE .../reservas/{reserva_id}"| inventario
    pedidos -->|"autoriza el cobro<br/>POST /api/v1/autorizaciones (con reserva_id)"| pagos

    pagos -->|"consulta el precio<br/>GET /api/v1/productos/{sku}"| catalogo
    pagos -->|"verifica el disponible si no hay reserva<br/>GET /api/v1/existencias/{sku}"| inventario

    operador -->|"administra productos<br/>POST/PUT/DELETE /api/v1/productos"| catalogo
    operador -->|"ajusta existencias<br/>POST/PUT /api/v1/existencias"| inventario
    operador -->|"calcula disponibilidad<br/>POST /api/v1/disponibilidad/serie"| confiabilidad

    pedidos -->|"guarda"| db_pedidos
    catalogo -->|"guarda"| db_catalogo
    inventario -->|"guarda"| db_inventario
    pagos -->|"guarda"| db_pagos

    catalogo & inventario & confiabilidad -.-> consul
    pedidos -.->|"se registran y resuelven instancias sanas<br/>GET /v1/health/service/{nombre}?passing=true"| consul
    bff -.-> consul
    config -.->|"inyecta CATALOGO_*, INVENTARIO_*, PAGOS_*,<br/>PEDIDOS_*, BFF_*, CONFIABILIDAD_*"| mercado

    classDef api fill:#2e7d32,stroke:#1b5e20,color:#fff
    classDef compuesto fill:#ef6c00,stroke:#b54d00,color:#fff
    classDef core fill:#1168bd,stroke:#0b4884,color:#fff
    classDef infra fill:#6a1b9a,stroke:#4a126b,color:#fff
    classDef datos fill:#e3f2fd,stroke:#1168bd,color:#0b2f55
    classDef persona fill:#08427b,stroke:#052e56,color:#fff
    classDef futuro fill:#ffffff,stroke:#999,color:#666,stroke-dasharray:5 5
    class bff api
    class pedidos compuesto
    class catalogo,inventario,pagos,confiabilidad core
    class consul,config infra
    class db_pedidos,db_catalogo,db_inventario,db_pagos datos
    class cliente,operador persona
    class gateway futuro
```

**Leyenda de tipos (taxonomía del syllabus):** 🟩 API · 🟧 Compuesto · 🟦 Core · 🟪 Infraestructura · borde punteado = fuera del parcial. Flechas continuas = llamadas de negocio por HTTP/JSON con `httpx`; punteadas = plataforma (registro, descubrimiento, configuración).

## Tabla de contenedores

| Contenedor | Puerto | Tipo | Datos propios | Prefijo de variables | Llama a |
|---|---|---|---|---|---|
| `bff-web` | 8080 | API | ninguno | `BFF_` | `ms-pedidos`, `ms-catalogo`, `ms-inventario` |
| `ms-pedidos` | 8003 | Compuesto | estado del pedido + claves de idempotencia (no de dominio de catálogo ni inventario) | `PEDIDOS_` | `ms-catalogo`, `ms-inventario`, `ms-pagos` |
| `ms-catalogo` | 8001 | Core | productos | `CATALOGO_` | — |
| `ms-inventario` (×3) | 8002, 8012, 8022 | Core | existencias y reservas | `INVENTARIO_` | — |
| `ms-pagos` | 8004 | Core con llamadas salientes | autorizaciones + claves de idempotencia | `PAGOS_` | `ms-catalogo`, `ms-inventario` (excepción de la semana 3) |
| `ms-confiabilidad` | 8005 | Core sin estado | ninguno (cálculo puro) | `CONFIABILIDAD_` | — |
| Consul | 8500, 8600/udp | Infraestructura | catálogo de servicios | — | — |
| `config-repo` | — | Infraestructura (Git) | YAML por servicio y perfil | — | — |

## Notas de implementación

- **Base de datos por servicio:** en el corte 1 cada servicio usa un repositorio en memoria detrás de un `Protocol`; el perfil `dev`/`prod` de `config-repo` apunta a un PostgreSQL **propio** de cada servicio. Ningún servicio lee la base de otro: el acceso es solo por su API.
- **Réplicas de inventario:** cada réplica tiene su propia memoria, por lo que en el corte 1 las existencias **no** se comparten entre réplicas. Es una limitación conocida, documentada por A02 y registrada en [`trazabilidad.md`](trazabilidad.md#3-revisión-cruzada-contra-el-código).
- `ms-pagos` usa direcciones **estáticas** (`PAGOS_URL_CATALOGO`, `PAGOS_URL_INVENTARIO`) y **no se registra en Consul** (la ficha A03 no lo pide). Por eso `ms-pedidos` debe llegar a `ms-pagos` por `PEDIDOS_URL_PAGOS` o el nombre del contenedor en la red de Compose. Ver divergencia D3 en [`trazabilidad.md`](trazabilidad.md#3-revisión-cruzada-contra-el-código).
- Los consumidores con descubrimiento por Consul son `ms-pedidos` y `bff-web`; el único servicio con varias réplicas es `ms-inventario`.
