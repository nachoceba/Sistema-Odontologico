# Proposal: deploy-and-hardening (C-13)

> **Gobernanza MEDIA** (empaquetado del sistema, revisión de permisos y configuración de seguridad; sin cambios en reglas de agenda ni en el esquema). Las decisiones P-1 a P-12 de `design.md` están **CONFIRMADAS por el usuario** (opción A) y se registran como DD-104 a DD-115.

## Why

Los changes C-01 a C-12 dejaron el sistema completo en desarrollo, pero para usarlo hace falta conocer los comandos internos: las migraciones y el seed se aplican a mano, el frontend solo corre con el servidor de desarrollo de Vite, no hay una prueba que recorra el flujo completo de punta a punta y el README todavía describe el primer change. Además quedaron anotados para la salida (C-13): revisar que ninguna ruta quede sin permisos (R-6), que ningún secreto llegue al navegador (RN-PR-03), el registro de accesos con la búsqueda de pacientes en la dirección (DD-77), el límite de intentos de login (DD-47), dónde vive el token (DD-46) y la contraseña del seed (DD-40). También falta el riesgo de adopción de la recepción (R-8). Todo sigue **local**, con Docker Compose y Mailpit; no se planifica un despliegue en la nube ni una cuenta SMTP real.

## What Changes

- **Migraciones y seed al iniciar** (P-1): `docker compose up` aplica `alembic upgrade head` y el seed ficticio antes de que arranquen `api` y `worker`, con un paso de preparación de una sola vez; si falta `SEED_DEMO_PASSWORD`, el arranque se detiene con un mensaje que nombra la variable.
- **Imagen del frontend multi-stage** (P-3): etapa de desarrollo (servidor de Vite, la de hoy), etapa de build con `VITE_API_URL` como build-arg y etapa final con nginx que sirve los archivos estáticos con vuelta a `index.html` para las rutas de la SPA.
- **Modo demo** (P-2): un archivo de Compose adicional que, sobre el de desarrollo, sirve el frontend con nginx, saca `--reload` y los montajes del código; Mailpit sigue siendo el servidor SMTP (DD-87). Desarrollo sigue con Vite y recarga.
- **CORS más estricto**: solo los orígenes de `CORS_ORIGINS`, solo los métodos y encabezados que usa el frontend y sin aceptar `*` como origen.
- **Matriz de permisos única** (P-7): una tabla de ruta × rol que debe coincidir exactamente con las rutas registradas; un test recorre cada ruta con cada rol y sin token.
- **Ningún secreto en el bundle** (P-8): chequeo del build del frontend que falla si aparece un nombre o patrón de secreto, y test de que el código solo lee `VITE_API_URL`.
- **Registro de accesos sin la consulta** (P-4): el registro de accesos de la API deja de escribir la parte `?…` de la dirección (la búsqueda `q` de pacientes, DD-77).
- **Smoke test de punta a punta** (P-5, P-6): login por rol → agendar → confirmación en Mailpit → cancelar → agendar otro → reprogramar → pasada de recordatorios forzada → recordatorio en Mailpit; corre contra el entorno levantado con un comando documentado.
- **Sesión y login** (P-9): se recomienda mantener `sessionStorage` y no agregar límite de intentos en v1 local, y dejarlo como decisión abierta para datos reales.
- **README** con requisitos, setup, comandos de desarrollo y demo, servicios, variables (sin valores), chequeos, smoke test y decisiones abiertas; **checklist de adopción para recepción** en un documento aparte enlazado (P-11).
- **Sin migraciones, sin endpoints nuevos y sin cambios en reglas de agenda.** Sin dependencias de Python o npm nuevas (nginx es una imagen base del contenedor).
- **Fuera de alcance**: despliegue en la nube, dominio público, HTTPS, proveedor SMTP de producción (SU-02 sigue abierto), imagen de backend de producción separada (P-2), refresh token, cookie httpOnly y límite de intentos (P-9), auditoría de accesos (DD-07) y revisión legal (R-10).

## Capabilities

### New Capabilities
- `demo-packaging`: imagen del frontend servida por nginx con la URL de la API fijada en el build, modo demo con Compose sobre el entorno de desarrollo y bundle sin secretos.
- `access-logging`: el registro de accesos de la API no guarda la parte de consulta de la dirección ni datos de pacientes.
- `end-to-end-smoke`: prueba de humo que recorre el flujo principal contra el entorno levantado, con emails verificados en Mailpit y la pasada de recordatorios forzada.

### Modified Capabilities
- `local-environment`: el comando único aplica migraciones y seed antes de arrancar `api` y `worker`; el arranque falla nombrando la variable si falta `SEED_DEMO_PASSWORD`.
- `api-health`: CORS limitado además a los métodos y encabezados que usa el frontend.
- `runtime-configuration`: `CORS_ORIGINS` rechaza `*`; el ejemplo de variables declara el origen del modo demo; el chequeo de "ningún secreto llega al frontend" cubre también el bundle construido.
- `access-control`: matriz única de ruta × rol, igual al inventario de rutas, con test por rol y sin token.

## Impact

- **Código**: `backend/app/main.py` (CORS), `backend/app/core/config.py` (`CORS_ORIGINS`), un filtro de registros en `backend/app/core/` aplicado al registro de accesos; sin cambios en `domain/`, `application/` ni repositorios.
- **Contenedores**: `frontend/Dockerfile` (multi-stage), `frontend/nginx.conf` (nuevo), `docker-compose.yml` (paso `migrate`, `target` de desarrollo del frontend), `docker-compose.demo.yml` (nuevo); `backend/Dockerfile` sin cambios de imagen.
- **Tests**: matriz de permisos (`tests/unit/api/`), CORS, filtro de registros, configuración (`CORS_ORIGINS`, `.env.example`), Vitest del uso de `import.meta.env`, chequeo del bundle, smoke test con marcador propio fuera de la batería por defecto.
- **Configuración**: `.env.example` suma el origen de la demo en `CORS_ORIGINS` y deja `SEED_DEMO_PASSWORD` vacía con la indicación de completarla en el `.env` local; ningún valor secreto en el repositorio.
- **Reglas duras**: la no superposición no se toca (el smoke test incluye un intento de agendar un horario ocupado que da `SLOT_TAKEN`); todo endpoint sigue con JWT y rol (regla 4, ahora con matriz única); secretos solo en el `.env` local (regla 5).
- **Documentación** (al archivar): `README.md`, `docs/adopcion-recepcion.md` (nuevo), `knowledge-base/08_arquitectura_propuesta.md` (§Seguridad, §Variables de entorno), `09_decisiones_y_supuestos.md` (DD-104 en adelante; DD-40, DD-46, DD-47 y DD-77 actualizadas), `10_preguntas_abiertas.md`, `11_recordatorios_email.md` (§Límites y riesgos), `CHANGES.md`, `CLAUDE.md` y `AGENTS.md`.
