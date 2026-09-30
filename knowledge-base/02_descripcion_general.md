# Descripción General

## Stack tecnológico

Stack definido por la cátedra (Metodología I). Las elecciones marcadas como "propuesta" son decisiones del equipo dentro de ese stack (ver `09_decisiones_y_supuestos.md`).

| Capa | Tecnología | Nota |
|---|---|---|
| Backend | Python + FastAPI | API REST; endpoints documentados con OpenAPI |
| Validación | Pydantic (incluido en FastAPI) | Esquemas de entrada y salida |
| ORM | SQLAlchemy 2.0 (síncrono) + Alembic | Modelos y migraciones versionadas (propuesta: Alembic) |
| Base de datos | PostgreSQL | Constraint de exclusión para superposición; extensión `btree_gist` |
| Autenticación | JWT | Login con email y contraseña; hash seguro de contraseñas; token de acceso de vida corta |
| Autorización | Chequeo de rol en la capa de aplicación | Dependencia `require_role` de FastAPI; no hay RLS (ver DD-02) |
| Tareas asincrónicas | Redis + Celery (propuesta) + Celery Beat | Envío de emails y recordatorio programado |
| Email | SMTP | Mailpit en desarrollo; proveedor SMTP gratuito a definir (ver SU-02) |
| Frontend | React + TypeScript + Vite | SPA que consume la API REST |
| Contenedores | Docker / Docker Compose | Un comando levanta todos los servicios |
| Tests | pytest (backend) y Vitest (frontend) | Foco en la capa de dominio |

**Restricción**: todo gratuito, con datos de pacientes ficticios.

## Arquitectura general

```
Navegador (recepción / odontólogo / admin)
        │  HTTPS
        ▼
Frontend React + Vite ──── REST + JWT ────► FastAPI (api)
                                              ├─ api/            routers, dependencias, esquemas Pydantic
                                              ├─ application/    casos de uso (agendar, cancelar, reprogramar...)
                                              ├─ domain/         reglas puras: disponibilidad, superposición, slots
                                              └─ infrastructure/ repositorios SQLAlchemy, SMTP, Celery
                                                  │                     │
                                                  ▼                     ▼
                                             PostgreSQL              Redis (broker)
                                                                        │
                                                          Celery worker │ Celery Beat (programación diaria)
                                                                        ▼
                                                                  Servidor SMTP (Mailpit en desarrollo)
```

Todos los servicios se levantan con Docker Compose: `db`, `redis`, `api`, `worker`, `beat`, `frontend` y `mailpit`.

Decisión de fondo: las reglas de negocio viven en `domain/` como funciones puras y testeables. La base de datos las refuerza con constraints, pero no es la única que las conoce.

## Integraciones externas

| Servicio | Propósito | Tipo |
|---|---|---|
| PostgreSQL | Persistencia | SQLAlchemy |
| Redis | Broker de tareas asincrónicas | Celery |
| Servidor SMTP | Envío de emails de confirmación y recordatorio | SMTP (Mailpit en desarrollo) |

Google Calendar queda como integración opcional posterior a v1.

## API

API REST bajo `/api/v1`. No hay endpoint de cron: el recordatorio lo dispara Celery Beat dentro del servicio `beat`, sin exponer ninguna ruta HTTP.

| Grupo | Ejemplos | Notas |
|---|---|---|
| Autenticación | `POST /api/v1/auth/login`, `GET /api/v1/auth/me` | El login devuelve un JWT de acceso |
| Usuarios | `/api/v1/users` | Solo administrador |
| Pacientes | `/api/v1/patients` | Según la matriz RBAC |
| Profesionales y horarios | `/api/v1/professionals`, `/working-hours`, `/time-off` | Escritura solo administrador (SU-06) |
| Turnos | `/api/v1/appointments`, `/appointments/{id}/cancel`, `/reschedule`, `/status` | Valida reglas de dominio |
| Disponibilidad | `GET /api/v1/professionals/{id}/availability` | Devuelve slots libres y ocupados |
