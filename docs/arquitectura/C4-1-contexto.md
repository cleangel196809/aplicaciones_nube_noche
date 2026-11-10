# C4 · Nivel 1 · Contexto del sistema

**Pregunta que responde:** ¿qué es MercadoAndino, quién lo usa y con qué otros sistemas habla?
**Audiencia:** el cliente, la gerencia y cualquier persona no técnica. No muestra tecnologías ni puertos.

```mermaid
flowchart TB
    %% Personas
    cliente_web(["👤 Cliente web<br/><i>Persona</i><br/>Consulta el catálogo y compra desde el navegador"])
    cliente_movil(["👤 Cliente de la app móvil<br/><i>Persona</i><br/>Compra en un solo paso desde el teléfono"])
    operador(["👤 Operador de MercadoAndino<br/><i>Persona</i><br/>Administra productos y existencias, y vigila la disponibilidad"])

    %% Sistema en alcance
    sistema["<b>MercadoAndino</b><br/><i>Sistema de software (en alcance)</i><br/>Plataforma de microservicios que muestra el catálogo con disponibilidad real,<br/>reserva inventario antes de confirmar, autoriza el pago y confirma el pedido"]

    %% Sistemas externos
    git[("GitHub<br/><i>Sistema externo</i><br/>Aloja el código y el repositorio de configuración (config-repo)")]
    pasarela["Pasarela de pagos<br/><i>Sistema externo · FUERA DEL CORTE 1</i><br/>Hoy ms-pagos la simula con la regla PAGOS_MONTO_MAXIMO"]

    cliente_web -->|"Consulta fichas y compra<br/>(HTTPS/JSON)"| sistema
    cliente_movil -->|"Compra en un solo paso<br/>(HTTPS/JSON)"| sistema
    operador -->|"Registra productos, ajusta existencias<br/>y consulta la confiabilidad"| sistema
    sistema -->|"Lee la configuración por perfil<br/>(default, dev, test, prod)"| git
    sistema -.->|"Autorizaría cobros<br/>(trabajo futuro)"| pasarela

    classDef persona fill:#08427b,stroke:#052e56,color:#fff
    classDef enAlcance fill:#1168bd,stroke:#0b4884,color:#fff
    classDef externo fill:#999999,stroke:#6b6b6b,color:#fff
    classDef futuro fill:#ffffff,stroke:#999999,color:#666,stroke-dasharray:5 5
    class cliente_web,cliente_movil,operador persona
    class sistema enAlcance
    class git externo
    class pasarela futuro
```

**Leyenda:** azul oscuro = persona · azul = sistema en alcance · gris = sistema externo · borde punteado = no se construye en este corte.

## Notas

- El **cliente web** y el de la **app móvil** usan el mismo canal (`bff-web`); el BFF existe porque la app «no debe hacer seis llamadas» (requerimiento 3).
- El **operador** no usa el BFF: llama directamente a las API administrativas de `ms-catalogo` (`POST/PUT/DELETE /api/v1/productos`) y `ms-inventario` (`POST/PUT /api/v1/existencias`), y a `ms-confiabilidad` para el requerimiento 5.
- La **pasarela de pagos** aparece punteada a propósito: el código de `ms-pagos` **no** llama a ningún sistema externo (autoriza por regla interna). Dibujarla como real sería un defecto del documento (regla 3 de la ficha A11).
