# ADR-001 · Monorepo didáctico frente a un repositorio por servicio

- **Estado:** aceptada
- **Fecha:** 8 de noviembre de 2026
- **Autor:** Andrés Camilo Cortés Vela (A11)
- **Factor relacionado:** I (código base)

## Contexto

El factor I pide **un código base por aplicación**: cada microservicio debería vivir en su propio repositorio, con su propio historial, sus permisos y su tubería de integración. La semana 2 pide además que la configuración viva en un **repositorio separado** (`config-repo`).

Restricciones del parcial:

- Seis estudiantes, doce acciones y una semana de plazo.
- El docente califica **un solo repositorio** (`cleangel196809/aplicaciones_nube_noche`) en un commit concreto de `main`.
- Hay que levantar todo con un solo `docker compose up` y pasar un único `scripts/e2e.sh`.
- Las comprobaciones automáticas (`scripts/verificar_estructura.sh`) se ejecutan sobre todos los servicios a la vez.

## Decisión

Usar **un monorepo** con una carpeta por servicio (`servicios/ms-*`, `bff-web`), por pieza de plataforma (`plataforma/*`) y `config-repo/`, **conservando la autonomía de cada servicio dentro de su carpeta**:

- cada servicio tiene su `pyproject.toml`, `uv.lock`, `Dockerfile`, `README.md` y `tests/`;
- ningún servicio importa código de la carpeta de otro (los módulos de A08 y A09 se **copian** a `app/` o se instalan como dependencia local, no se importan por ruta relativa);
- `config-repo/` se trata como si fuera un repositorio aparte: tiene su propio `README` y su propio PR revisado.

## Alternativas consideradas

| Alternativa | A favor | En contra |
|---|---|---|
| **Un repositorio por servicio + uno de configuración (polirepo)** | Cumple el factor I al pie de la letra; permisos e historial independientes; despliegue independiente natural | Ocho repositorios para seis personas en una semana; el docente tendría que calificar en ocho lugares; el E2E necesitaría submódulos o un repositorio orquestador adicional |
| **Monorepo sin reglas** | Lo más simple | Invita a importar código entre servicios y compartir modelos: se convierte en un **monolito distribuido** |
| **Monorepo con autonomía por carpeta** (elegida) | Un solo lugar para calificar e integrar; un PR muestra el cambio completo; el E2E vive junto al código | Hay que imponer la disciplina con reglas y revisión: Git no impide que alguien importe código ajeno |

## Consecuencias

**Lo que se gana**

- Integración y revisión en un solo lugar; el E2E y el `docker-compose.yml` ven todo el código de una vez.
- Las comprobaciones automáticas se aplican por igual a todos los servicios.
- Un cambio de contrato y su consumidor pueden revisarse en el mismo PR.

**Lo que se paga**

- **Se incumple el factor I literalmente.** Lo reconocemos y lo mitigamos con autonomía por carpeta.
- Historial y permisos compartidos: cualquiera puede tocar la carpeta de otro (se mitiga con la regla de `ENTREGA.md`: «no edita las carpetas de otros» y revisión obligatoria de PR).
- La integración continua corre sobre todo el repositorio aunque solo cambie un servicio (se podría filtrar por rutas en el *workflow*).
- El riesgo de **acoplamiento accidental** (compartir un modelo «por comodidad») es mayor que con repositorios separados.

**Cuándo revisar esta decisión:** al pasar a producción o cuando cada servicio tenga un equipo propio, se separa en un repositorio por servicio (con `git subtree split` se conserva el historial de cada carpeta) y `config-repo` en su propio repositorio con permisos restringidos para `prod`.
