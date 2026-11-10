# Trazabilidad, doce factores y revisión cruzada

## 1. De los requerimientos del cliente a la API

La arquitectura se deriva **de lo que el cliente pide** (indicador 1.3), no del modelo de datos. Cadena: *requerimiento → caso de uso → capacidad de negocio → contexto delimitado → servicio → API*. Los requerimientos son los cinco de [`ENUNCIADO.md`](../ENUNCIADO.md) §1.

| # | Requerimiento del cliente | Caso de uso UML | Capacidad de negocio | Contexto delimitado | Servicio (tipo) | API |
|---|---|---|---|---|---|---|
| R1 | «Muestre el catálogo filtrado por categoría y la disponibilidad real de cada producto» | Consultar catálogo · Ver ficha de producto | Gestión del surtido + control de existencias | Catálogo · Inventario · Canal web | `ms-catalogo` (core), `ms-inventario` (core), `bff-web` (API) | `GET /bff/v1/catalogo?categoria=` · `GET /bff/v1/fichas/{sku}` → `GET /api/v1/productos?categoria=` + `GET /api/v1/existencias/{sku}` |
| R2 | «No venda lo que no tiene: reserve el inventario antes de confirmar» | Reservar unidades de un pedido | Control de existencias | Inventario | `ms-inventario` (core); verificación adicional en `ms-pagos` (core) | `POST /api/v1/existencias/{sku}/reservas` → `409`; `POST /api/v1/autorizaciones` sin `reserva_id` → `409` |
| R3 | «Haga la compra en un solo paso desde la app móvil» | Comprar | Gestión de pedidos + cobro | Pedidos · Pagos · Canal web | `bff-web` (API) → `ms-pedidos` (compuesto) → `ms-pagos` (core) | `POST /bff/v1/compras` → `POST /api/v1/pedidos` → `POST /api/v1/autorizaciones` |
| R4 | «Escale de forma horizontal sin editar direcciones en ningún archivo» | Agregar una réplica · Retirar una réplica | Descubrimiento y balanceo | Plataforma | Consul + `plataforma/descubrimiento` (A08) + `plataforma/balanceador` (A09) | `PUT /v1/agent/service/register` · `GET /v1/health/service/ms-inventario?passing=true` · `GET /api/v1/diagnostico/inventario` |
| R5 | «Demuestre con números qué disponibilidad percibe realmente el cliente» | Calcular disponibilidad de la cadena | Ingeniería de confiabilidad | Confiabilidad | `ms-confiabilidad` (core sin estado) | `POST /api/v1/disponibilidad/serie` · `/paralelo` · `/api/v1/mtbf/serie` · `/api/v1/presupuesto-error` |

## 2. Doce factores con evidencia del repositorio

Evidencia tomada del código que **está en `main`** (`servicios/ms-pagos/`) y de los archivos comunes. Se completará con la de los demás servicios en la revisión cruzada final.

| Factor | Qué exige | Evidencia concreta en el repositorio | Estado |
|---|---|---|---|
| **I. Código base** | Un código base por aplicación, muchos despliegues | Cada servicio es autónomo: su `pyproject.toml`, `uv.lock`, `Dockerfile` y `README.md` (`servicios/ms-pagos/`). El monorepo es una concesión didáctica: [ADR-001](adr/ADR-001-monorepo.md) | ✅ con excepción documentada |
| **III. Configuración** | Configuración en el entorno, no en el código | `servicios/ms-pagos/app/config.py`: `Configuracion(BaseSettings)` con `env_prefix="PAGOS_"`, validadores y `get_configuracion()` con `lru_cache`. Un valor inválido (`PAGOS_MONTO_MAXIMO=0`) impide el arranque (`tests/test_salud.py::test_valor_invalido_impide_arranque`). `.env` ignorado en `.gitignore`; solo `.env.example` versionado | ✅ |
| **IV. Servicios de respaldo** | Los recursos externos se tratan como adjuntos intercambiables por configuración | `PAGOS_URL_CATALOGO` y `PAGOS_URL_INVENTARIO` (nunca fijas en el código); repositorios detrás de `Protocol` (`app/repositorios/base.py`) para cambiar memoria por PostgreSQL sin tocar el servicio | ✅ |
| **VI. Procesos** | Procesos sin estado; el estado vive en servicios de respaldo | `ms-pagos` guarda autorizaciones **en memoria del proceso** (`RepositorioAutorizacionesMemoria`): si se reinicia, se pierden, y dos réplicas no compartirían claves de idempotencia. Aceptable en el corte 1 por diseño del curso; el perfil `prod` debe apuntar a PostgreSQL | ⚠️ parcial, conocido |
| **IX. Desechabilidad** | Arranque rápido y apagado elegante | `lifespan` en `app/main.py`: crea el `httpx.AsyncClient` al arrancar y lo cierra en el `finally` (`await app.state.http.aclose()`). Arranque medido < 1 s. Los servicios con Consul cancelan su registro en el mismo `finally` | ✅ |
| **XI. Registros** | Los registros son un flujo de eventos por salida estándar | `structlog` con `JSONRenderer` y middleware que registra `ruta`, `metodo`, `estado` y `duracion_ms` (`app/main.py`). Ejemplo real: `{"ruta": "/api/v1/autorizaciones", "estado": 503, "duracion_ms": 4.11, "event": "peticion"}` | ✅ |

## 3. Revisión cruzada contra el código

**Regla:** si los diagramas muestran algo que el código no hace, es un defecto del documento. Cuando objetivo e implementación divergen, manda la implementación.

### Estado del código en `main` (revisado el 9 de noviembre de 2026, 19:00)

| Acción | Código en `main` | Contrastado |
|---|---|---|
| A03 `ms-pagos` | ✅ integrado (PR #1) | ✅ diagramas ajustados al código |
| A11 Arquitectura | ⏳ PR #2 abierto; `scripts/verificar_estructura.sh` da `[OK]` | — |
| A01 `ms-catalogo`, A02 `ms-inventario`, A04 `ms-pedidos`, A05 `bff-web`, A06 `ms-confiabilidad` | ❌ sin código (el verificador los marca «Aún no iniciado») | Se contrastan contra su ficha; se revisarán si se integran antes de la entrega |
| A07 `config-repo`, A08 Consul, A09 balanceador, A10 pruebas, A12 E2E | ❌ sin contenido | Ídem |

### Divergencias encontradas

| Id | Divergencia | Dónde | Cómo se cierra | Estado |
|---|---|---|---|---|
| D1 | El primer borrador del C4-2 mostraba a `ms-pagos` registrándose en Consul; el código **no** lo hace y la ficha A03 no lo exige | `C4-2`, `UML-despliegue` | Se corrigieron los diagramas: `ms-pagos` aparece sin registro en Consul | ✅ cerrada |
| D2 | `CONVENCIONES.md` §6 ilustra el `409` con `solicitado: 9999`, pero `ms-inventario` limita la reserva a `reserva_maxima_unidades` (1 a 1000) y `ms-pagos` a `unidades` 1 a 1000: con 9999 la respuesta es **`422`**, no `409`. La verificación 6 del E2E fallaría | A02, A03, A12 | Propuesta para A12: que el E2E pida **101** unidades de `CAF-001` (disponible 100). Evidencia en `servicios/ms-pagos/README.md` §4: `101 → 409` | 🟡 propuesta enviada a A12 · sin respuesta al 9 nov |
| D3 | Si `ms-pedidos` en modo `consul` intenta resolver `ms-pagos` por Consul, no lo encontrará (pagos no se registra) | A03, A04 | Opción a: `ms-pedidos` usa `PEDIDOS_URL_PAGOS` (estático) para pagos y Consul solo para inventario, como dice la ficha A04. Opción b: agregar registro en Consul a `ms-pagos` | 🟡 por acordar con A04 · sin respuesta al 9 nov |
| D4 | `ms-pagos` consulta el disponible con una URL fija (`PAGOS_URL_INVENTARIO`), que apunta a **una** réplica; como cada réplica de inventario tiene su propia memoria, el disponible puede diferir del que vio `ms-pedidos` | A02, A03 | En la saga no afecta: `ms-pedidos` envía `reserva_id` y pagos **omite** la consulta a inventario. Solo aplica a llamadas directas sin `reserva_id`. Solución definitiva: base de datos compartida por las réplicas de inventario (una base **por servicio**, no por réplica) | ✅ mitigada · documentada |
| D5 | Formato del dinero: `ms-pagos` devuelve `total` como **número** JSON (internamente `Decimal`); `bff-web` publica `precio` como **texto**; `ms-catalogo` con Pydantic v2 serializa `Decimal` como texto | A01, A03, A04, A05 | `ms-pagos` acepta precio en número o texto (`Decimal(str(valor))`). A04 debe hacer lo mismo con `total`. Se acuerda: entre servicios se acepta ambos; hacia el canal, texto | 🟡 por confirmar con A04 y A05 · sin respuesta al 9 nov |
| D6 | Si `ms-pedidos` responde `503 "ms-pagos no disponible"`, la regla 6 de A05 podría leerse como «5xx de la dependencia → `502 ms-pedidos respondio mal`», y el cliente perdería el nombre del servicio realmente caído | A05 | Propuesta: `bff-web` **propaga** `503`/`504` de `ms-pedidos` con su `detail`, y solo responde `502`/`503` propios cuando el que falla es `ms-pedidos` mismo. Así quedó dibujado en la secuencia 3 | 🟡 por acordar con A05 · sin respuesta al 9 nov |
| D7 | `servicios/ms-pagos/LEEME-PENDIENTE.md` sigue en `main` aunque el servicio ya tiene `README.md` | A03 | Se elimina en el PR de A11 | ✅ cerrada en este PR |

> **Pendiente para la entrega:** repetir esta revisión cuando los demás servicios lleguen a `main` (puertos, rutas, nombres de variables, códigos de estado) y actualizar esta tabla.
