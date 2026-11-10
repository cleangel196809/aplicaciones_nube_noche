# ADR-002 · Consul con balanceo del lado del cliente frente al `Service` de Kubernetes

- **Estado:** aceptada
- **Fecha:** 8 de noviembre de 2026
- **Autor:** Andrés Camilo Cortés Vela (A11)
- **Requerimiento:** R4 «escale de forma horizontal sin editar direcciones en ningún archivo»

## Contexto

`ms-inventario` corre en tres réplicas (8002, 8012, 8022). Los consumidores (`ms-pedidos`, `bff-web`) necesitan saber **qué réplicas existen y cuáles están sanas** sin que nadie edite una URL cuando se agrega o se cae una. Además, el curso quiere demostrar **balanceo ponderado** (pesos 3:2:1) y expulsión de réplicas caídas en menos de 30 s.

El parcial se despliega con Docker Compose en un solo equipo (no hay Kubernetes hasta la semana 8).

## Decisión

Usar **Consul** como registro de servicios y hacer el **balanceo del lado del cliente**:

1. Cada réplica se **registra** al arrancar (`PUT /v1/agent/service/register`) con id `nombre-host-puerto`, etiqueta `peso=N` y un *check* HTTP a `/health` cada 10 s; **cancela** su registro en el `finally` del `lifespan`.
2. El consumidor usa un `ResolvedorConsul` (A08) que consulta `GET /v1/health/service/{nombre}?passing=true`, guarda el resultado en **caché con TTL** y, si Consul no responde, sigue con la última lista (**modo degradado**).
3. Un `BalanceadorPonderado` (A09) elige la réplica en el propio proceso del consumidor y la expulsa localmente tras N fallos seguidos.

## Alternativas consideradas

| Alternativa | Cómo funciona | A favor | En contra |
|---|---|---|---|
| **Consul + balanceo en el cliente** (elegida) | El cliente pregunta al registro y elige | Sin salto de red extra; pesos y expulsión bajo nuestro control; funciona en Compose; enseña el mecanismo completo | Lógica replicada en cada consumidor (Python hoy; habría que reescribirla en otro lenguaje); cada cliente puede tener una vista distinta durante el TTL |
| **`Service` de Kubernetes (lado del servidor)** | Una IP virtual estable; `kube-proxy` reparte el tráfico | El cliente no sabe nada: solo llama a `http://ms-inventario`; salud por *readiness probes*; estándar de la industria | Requiere Kubernetes (semana 8); reparto casi aleatorio, **sin pesos** por réplica sin una malla de servicios; menos visible para aprender |
| **Balanceador central (Nginx / HAProxy)** | Un proxy delante de las réplicas | Lenguaje-agnóstico; un solo lugar de configuración | Un salto de red más y un **punto único de falla**; hay que regenerar su configuración al cambiar las réplicas (o volver a necesitar un registro) |
| **DNS de Docker Compose** | `ms-inventario` resuelve a varias IP | Cero código | Sin comprobación de salud ni pesos; la caché de DNS ignora réplicas caídas |
| **Eureka (Netflix)** | Registro AP con *heartbeats* | Muy usado con Spring | Ecosistema Java; en Python hay menos soporte; elige disponibilidad sobre consistencia (ver CAP) |

## CAP: qué pasa ante una partición de red

El teorema CAP dice que, ante una **partición** (P), un sistema distribuido debe elegir entre **consistencia** (C) y **disponibilidad** (A).

- **Consul es CP:** usa Raft con quórum. Si los servidores pierden la mayoría, **deja de aceptar escrituras** (registros nuevos) antes que mostrar datos contradictorios. Lecturas por defecto también requieren líder.
- **Eureka es AP:** cada nodo sigue respondiendo con lo que tiene, aunque pueda estar desactualizado (entra en «modo de autopreservación»).

**Cómo lo compensamos:** nuestro `ResolvedorConsul` agrega una capa **AP del lado del cliente**: si Consul no responde, usa la **última lista conocida** (modo degradado). Es decir, durante la partición preferimos llamar a una réplica que quizá ya murió (y que el balanceador expulsará tras N fallos) antes que dejar de vender. En el parcial Consul corre en modo `-dev` (un solo servidor), así que la partición entre servidores no se puede observar; en producción se usarían 3 o 5 servidores.

## Consecuencias

**Lo que se gana**

- R4 se cumple: agregar una réplica es arrancar un contenedor con otro `PUERTO_SERVICIO`; nadie edita URLs.
- Reparto ponderado verificable (6:4:2 en 12 peticiones) y expulsión activa sin esperar al TTL.
- Un salto de red menos que con un balanceador central.

**Lo que se paga**

- **Tiempo de expulsión** = intervalo del *check* (10 s) + propagación + TTL de la caché del resolvedor (10 s): hasta ~20–30 s llamando a una réplica muerta si no fuera por la expulsión activa del balanceador.
- La lógica de descubrimiento y balanceo vive **en cada consumidor** y en un solo lenguaje.
- Consul es una pieza más que operar; en modo `-dev` no es apto para producción.
- Cuando migremos a Kubernetes (semana 8) esta decisión se **revisa**: lo más probable es usar el `Service` para el reparto y conservar Consul solo si se necesita descubrimiento entre clústeres o pesos finos.
