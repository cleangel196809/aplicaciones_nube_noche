# UML · Diagrama de despliegue

**Qué muestra:** dónde corre cada artefacto en tiempo de ejecución. El entorno del parcial es **un solo nodo** (el equipo anfitrión con Docker Engine) que levanta todo con `docker compose up --build` (A12).

```mermaid
flowchart TB
    subgraph host["«device» Equipo anfitrión · Windows / Linux / macOS"]
        direction TB
        subgraph engine["«execution environment» Docker Engine + Docker Compose"]
            direction TB
            subgraph red["«network» red de Compose (bridge) · resolución DNS por nombre de contenedor"]
                direction TB
                consul{{"«container» consul<br/>hashicorp/consul:1.21 · agent -dev<br/>8500/tcp · 8600/udp"}}

                bff["«container» bff-web<br/>python:3.13-slim + uv · 8080<br/>BFF_MODO_DESCUBRIMIENTO=consul"]
                pedidos["«container» ms-pedidos<br/>python:3.13-slim + uv · 8003<br/>PEDIDOS_MODO_DESCUBRIMIENTO=consul"]
                catalogo["«container» ms-catalogo · 8001"]
                inv1["«container» ms-inventario-1<br/>PUERTO_SERVICIO=8002<br/>HOST_ANUNCIADO=ms-inventario-1<br/>PESO_SERVICIO=3"]
                inv2["«container» ms-inventario-2<br/>PUERTO_SERVICIO=8012<br/>HOST_ANUNCIADO=ms-inventario-2<br/>PESO_SERVICIO=2"]
                inv3["«container» ms-inventario-3<br/>PUERTO_SERVICIO=8022<br/>HOST_ANUNCIADO=ms-inventario-3<br/>PESO_SERVICIO=1"]
                pagos["«container» ms-pagos<br/>python:3.13-slim + uv 0.5 · 8004<br/>uvicorn app.main:app --host 0.0.0.0"]
                confiab["«container» ms-confiabilidad · 8005"]
            end
        end
        envfile[/"«artifact» .env (NO versionado)<br/>+ salida de config-repo/cargar_config.py"/]
        secretos[/"«artifact» /run/secrets/*<br/>credenciales (solo prod)"/]
    end

    navegador(["«device» Navegador / app móvil"])

    navegador -->|"HTTP :8080"| bff
    bff -->|"HTTP · nombre resuelto en Consul"| pedidos
    pedidos -->|"HTTP"| catalogo
    pedidos -->|"HTTP · balanceo ponderado 3:2:1"| inv1 & inv2 & inv3
    pedidos -->|"HTTP"| pagos
    pagos -->|"HTTP http://ms-catalogo:8001"| catalogo
    pagos -->|"HTTP http://ms-inventario-1:8002"| inv1
    catalogo & inv1 & inv2 & inv3 & pedidos & bff & confiab -.->|"registro + check /health cada 10 s"| consul
    envfile -.->|"variables de entorno al arrancar"| engine
    secretos -.->|"montados como archivos"| engine

    classDef api fill:#2e7d32,stroke:#1b5e20,color:#fff
    classDef compuesto fill:#ef6c00,stroke:#b54d00,color:#fff
    classDef core fill:#1168bd,stroke:#0b4884,color:#fff
    classDef infra fill:#6a1b9a,stroke:#4a126b,color:#fff
    classDef art fill:#fff8e1,stroke:#c79a00,color:#000
    class bff api
    class pedidos compuesto
    class catalogo,inv1,inv2,inv3,pagos,confiab core
    class consul infra
    class envfile,secretos art
```

**Leyenda:** 🟩 API · 🟧 Compuesto · 🟦 Core · 🟪 Infraestructura · amarillo = artefactos de configuración.

## Decisiones visibles en el despliegue

| Decisión | Por qué |
|---|---|
| Tres réplicas de `ms-inventario` con pesos 3, 2 y 1 | Demuestra el balanceo ponderado de A09: en 12 peticiones el reparto esperado es 6:4:2 |
| `HOST_ANUNCIADO` = nombre del contenedor | Dentro de un contenedor `localhost` es el propio contenedor: anunciarlo en Consul haría que los consumidores se llamen a sí mismos |
| Identificador `ms-inventario-<host>-<puerto>` | Un identificador repetido haría que una réplica pise el registro de otra |
| `.env` fuera de Git y secretos en `/run/secrets` | Factor III: la configuración vive en el entorno; ninguna credencial entra al repositorio |
| Consul en modo `-dev` | Solo para el parcial: en producción serían 3 o 5 servidores con quórum |
| `ms-pagos` llama a inventario por una URL fija | No usa Consul en el corte 1; con inventario replicado, la URL fija apunta a **una** réplica (ver D4 en [trazabilidad](trazabilidad.md#3-revisión-cruzada-contra-el-código)) |

## Evolución prevista (fuera del parcial)

En producción el nodo único se reemplaza por un clúster (semana 8, Kubernetes): cada contenedor pasa a ser un *Pod*, Consul se sustituye o convive con el `Service` de Kubernetes y el `gateway :8000` (semana 7) se convierte en la única entrada pública. Ver [ADR-002](adr/ADR-002-descubrimiento.md).
