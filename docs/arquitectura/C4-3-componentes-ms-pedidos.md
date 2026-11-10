# C4 · Nivel 3 · Componentes de `ms-pedidos`

**Pregunta que responde:** ¿cómo está organizado por dentro el contenedor más complejo, quién es responsable de qué y por dónde entra y sale cada petición?
**Audiencia:** quienes programan o revisan `ms-pedidos` (A04) y quienes integran con él.

`ms-pedidos` es el **orquestador de la saga** de compra. Se eligió para el nivel 3 porque concentra las decisiones más delicadas: llamadas en paralelo, compensación, idempotencia y traducción de fallos.

```mermaid
flowchart TB
    bff(["bff-web<br/>(contenedor externo)"])

    subgraph ms_pedidos["Contenedor ms-pedidos :8003 · FastAPI"]
        direction TB

        main["<b>main.py</b><br/><i>Ensamblador</i><br/>lifespan: crea el único httpx.AsyncClient,<br/>registra en Consul y cancela en el finally.<br/>Middleware structlog (ruta, estado, duracion_ms).<br/>Manejadores: excepción de dominio → 402/404/409/502/503/504"]

        rutas["<b>rutas/pedidos.py</b><br/><i>Router</i><br/>POST /api/v1/pedidos · GET /api/v1/pedidos/{id}<br/>GET /api/v1/pedidos?estado= · GET /api/v1/diagnostico/inventario<br/>Solo traduce HTTP ↔ caso de uso"]

        deps["<b>dependencias.py</b><br/><i>Inyección (Annotated + Depends)</i><br/>Arma el servicio con clientes y repositorios"]

        config["<b>config.py</b><br/><i>Configuracion(BaseSettings)</i><br/>PEDIDOS_MODO_DESCUBRIMIENTO, PEDIDOS_URL_*,<br/>timeouts · get_configuracion() con lru_cache"]

        servicio["<b>servicios/pedidos.py</b><br/><i>Caso de uso · orquestador de la saga</i><br/>T1 ∥ T1' con asyncio.gather(return_exceptions=True)<br/>T2 autoriza · T3 confirma · compensa liberando la reserva<br/>NO importa FastAPI"]

        errores["<b>errores.py</b><br/><i>Excepciones de dominio</i><br/>ProductoNoEncontrado, StockInsuficiente,<br/>PagoRechazado, DependenciaNoDisponible…"]

        subgraph repos["repositorios/"]
            repo_base["<b>base.py</b><br/><i>Protocol</i><br/>RepositorioPedidos · AlmacenIdempotencia"]
            repo_mem["<b>memoria.py</b><br/>implementación en memoria"]
        end

        subgraph clientes["clientes/ (httpx)"]
            cli_cat["<b>catalogo.py</b><br/>ICatalogo"]
            cli_inv["<b>inventario.py</b><br/>IInventario"]
            cli_pag["<b>pagos.py</b><br/>IPagos"]
        end

        subgraph desc["descubrimiento (módulos de A08 y A09 copiados a app/)"]
            resolvedor["<b>ResolvedorConsul</b><br/>caché con TTL + modo degradado"]
            balanceador["<b>BalanceadorPonderado</b><br/>round robin por crédito"]
        end
    end

    catalogo(["ms-catalogo :8001"])
    inventario(["ms-inventario ×3"])
    pagos(["ms-pagos :8004"])
    consul{{"Consul :8500"}}

    bff -->|"POST /api/v1/pedidos<br/>+ Idempotency-Key"| rutas
    main -->|"incluye el router y<br/>registra manejadores"| rutas
    rutas -->|"obtiene el servicio por"| deps
    deps -->|"lee"| config
    rutas -->|"invoca crear_pedido()"| servicio
    servicio -->|"lanza"| errores
    main -.->|"traduce a HTTP"| errores
    servicio -->|"guarda pedido y clave"| repo_base
    repo_mem -.->|"implementa"| repo_base
    servicio -->|"precio (T1)"| cli_cat
    servicio -->|"reserva (T1') y libera (compensación)"| cli_inv
    servicio -->|"autoriza (T2)"| cli_pag
    cli_inv -->|"pide la siguiente instancia"| balanceador
    balanceador -->|"instancias sanas"| resolvedor
    resolvedor -->|"GET /v1/health/service/ms-inventario?passing=true"| consul
    cli_cat -->|"GET /api/v1/productos/{sku}"| catalogo
    cli_inv -->|"POST /api/v1/existencias/{sku}/reservas<br/>DELETE .../reservas/{reserva_id}"| inventario
    cli_pag -->|"POST /api/v1/autorizaciones"| pagos

    classDef comp fill:#85bbf0,stroke:#5d82a8,color:#000
    classDef nucleo fill:#1168bd,stroke:#0b4884,color:#fff
    classDef ext fill:#999,stroke:#6b6b6b,color:#fff
    class main,rutas,deps,config,errores,repo_base,repo_mem,cli_cat,cli_inv,cli_pag,resolvedor,balanceador comp
    class servicio nucleo
    class bff,catalogo,inventario,pagos,consul ext
```

**Leyenda:** azul oscuro = núcleo del dominio (caso de uso) · azul claro = componentes de soporte · gris = contenedores externos a `ms-pedidos`.

## Reglas que el diagrama hace visibles

| Regla | Dónde se ve |
|---|---|
| La capa de servicio no conoce HTTP | `servicios/pedidos.py` solo habla con `errores`, `repositorios` y `clientes`; `main.py` traduce |
| Un solo `httpx.AsyncClient` | Se crea en el `lifespan` de `main.py` y lo comparten los tres clientes |
| El servicio depende de contratos, no de clases | `repositorios/base.py` y las interfaces `ICatalogo`, `IInventario`, `IPagos` (ver [UML de componentes](UML-componentes.md)) |
| Solo inventario se balancea | Es el único con réplicas; catálogo y pagos tienen una instancia en el corte 1 |
| Nunca queda una reserva huérfana | La compensación vive en el caso de uso, no en el router (ver [secuencias](UML-secuencia-compra.md)) |

> Este nivel 3 describe la arquitectura **objetivo** según la ficha A04. Cuando el código de `ms-pedidos` llegue a `main`, se contrasta archivo por archivo en la [revisión cruzada](trazabilidad.md#3-revisión-cruzada-contra-el-código).
