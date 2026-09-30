# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto Sistema Odontológico (agenda de turnos + recordatorios por email).
> Stack definido por la cátedra: Python + FastAPI, JWT, SQLAlchemy, PostgreSQL, Redis y Docker en el backend; React + TypeScript + Vite en el frontend.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

Stack: FastAPI + SQLAlchemy + PostgreSQL + Redis (Celery) + Docker Compose; React + TypeScript + Vite. Prioridad de calidad: mantenibilidad (capas domain / application / infrastructure). Todo gratuito, datos de pacientes ficticios.

---

## Cómo usar este documento

1. Identificá el próximo change con `Estado: [ ]` cuyas dependencias estén todas en `[x]` (usá los GATES de abajo).
2. Leé los archivos de la sección **Leer antes** del change (y su Scope) antes de proponer.
3. Ejecutá `/opsx:propose C-NN-nombre` y luego `/opsx:apply`.
4. Al terminar y validar, ejecutá `/opsx:archive C-NN-nombre`.
5. Marcá el checkbox `[x]` en el **Estado** del change en este archivo.

---

## Árbol de dependencias

```
C-01 foundation-setup
 ├── C-02 db-schema-and-seed
 │    └── C-03 auth-login-rbac
 │         ├── C-04 user-management
 │         ├── C-06 patients-crud
 │         ├── C-07 professional-schedules      (+ C-05)
 │         │    └── C-09 agenda-views           (+ C-05)
 │         └── C-08 appointment-use-cases       (+ C-05)
 │              ├── C-11 email-confirmation-infra
 │              │    └── C-12 reminders-cron
 │              └── C-10 appointment-management-ui   (+ C-06, C-09)
 └── C-05 domain-scheduling-core   (funciones puras, no requiere BD)

C-13 deploy-and-hardening  ← C-04, C-10, C-12
```

### Paralelismo por fase

```
GATE 0: C-01 ✓                                  ← FORK
  → C-02 db-schema-and-seed                [Agente A]
  → C-05 domain-scheduling-core            [Agente B]  (puro, sin BD)

GATE 1: C-02 ✓
  → C-03 auth-login-rbac                   [Agente A]
  → (C-05 continúa)                        [Agente B]

GATE 2: C-03 ✓ y C-05 ✓                         ← FORK
  → C-08 appointment-use-cases             [Agente A]
  → C-07 professional-schedules            [Agente B]
  → C-06 patients-crud                     [Agente C]

GATE 3: C-07 ✓ (y C-08 ✓ en curso)              ← FORK
  → C-11 email-confirmation-infra          [Agente A — si C-08 ✓]
  → C-09 agenda-views                      [Agente B — si C-07 ✓]
  → C-04 user-management                   [Agente C — si C-03 ✓]

GATE 4: C-11 ✓, C-09 ✓, C-06 ✓
  → C-12 reminders-cron                    [Agente A]
  → C-10 appointment-management-ui         [Agente C — si C-08 ✓, C-09 ✓, C-06 ✓]

GATE 5: C-04 ✓, C-10 ✓, C-12 ✓
  → C-13 deploy-and-hardening              [Agente A]
```

### Camino crítico (7 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-08 → C-11 → C-12 → C-13*
C-01 → C-02 → C-03 → C-07 → C-09 → C-10 → C-13*   (cadena de igual longitud)
```

`*` C-13 es el último de ambas cadenas. Quedan fuera del camino crítico C-04 (gestión de usuarios: se puede sembrar por seed) y C-06 (ABM de pacientes se ejecuta en paralelo con C-07/C-08).

### Plan óptimo con 3 agentes

| Paso | Agente A (Backend Core) | Agente B (Backend Aux / Dominio) | Agente C (Frontend) |
|------|-------------------------|----------------------------------|---------------------|
| 1 | C-01 | — | — |
| 2 | C-02 | C-05 | — |
| 3 | C-03 | (cierra C-05 si falta) | — |
| 4 | C-08 | C-07 | C-06 |
| 5 | C-11 | C-09 | C-04 |
| 6 | C-12 | — | C-10 |
| 7 | C-13 | — | — |

---

## FASE 0 — Fundación

### [C-01] `foundation-setup`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Estructura del repositorio: `backend/` (FastAPI con `app/{api,domain,application,infrastructure,core}`, `alembic/`, `scripts/`, `tests/`) y `frontend/` (React + TypeScript + Vite)
  - `docker-compose.yml` con los servicios `db` (PostgreSQL), `redis`, `api`, `worker`, `beat`, `frontend` y `mailpit`; Dockerfiles de backend y frontend; un comando levanta todo
  - pytest configurado (unit de dominio + carpeta de integración) y Vitest en el frontend; lint y format (ruff y eslint)
  - `.env.example` con todas las variables de la tabla de `08_arquitectura_propuesta.md` §Variables de entorno; configuración validada con Pydantic Settings; `.env` ignorado por git
  - `app/core/errors.py` (errores de dominio tipados) y endpoint de salud `GET /api/v1/health`
  - Riesgo a registrar: elegir el proveedor SMTP gratuito de demo y verificar su cupo (SU-02); confirmar Celery con la cátedra (DD-10)
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §Stack
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Variables de entorno
  - `knowledge-base/09_decisiones_y_supuestos.md` (DD-01, DD-10 a DD-13)
  - `knowledge-base/01_vision_y_objetivos.md`
---

## FASE 1 — Datos y acceso

### [C-02] `db-schema-and-seed`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Modelos SQLAlchemy 2.0 y migraciones Alembic: extensión `btree_gist`; enums `user_role`, `appointment_status`, `notification_kind`, `notification_status`
  - Migración inicial escrita a mano: `CREATE EXTENSION IF NOT EXISTS btree_gist` antes de crear `appointments`; `downgrade` elimina constraint, tablas y tipos enum; revisar siempre el autogenerate (no genera bien `ExcludeConstraint` con `tstzrange` y `WHERE`)
  - Tablas `users`, `professionals`, `working_hours`, `time_off`, `patients`, `appointments`, `email_notifications`, `clinic_settings` con todos los CHECK/UNIQUE/FK del modelo
  - `appointments`: `ExcludeConstraint` equivalente a `EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&) WHERE (status = 'scheduled')`; índices `(professional_id, starts_at)` y `(starts_at)`
  - `email_notifications`: `UNIQUE (appointment_id, kind, appointment_starts_at)`
  - `backend/scripts/seed.py` (idempotente): 1 admin, 1 recepción, 2 profesionales con `working_hours` L-V, `clinic_settings` (nombre, dirección y teléfono ficticios, 30 min, `America/Argentina/Buenos_Aires`, hora 9), 10 pacientes ficticios con emails `@example.com`; contraseñas de prueba ficticias
  - Tests de integración contra PostgreSQL real (contenedor): el constraint de exclusión rechaza solapamiento `scheduled`, permite solapar con `cancelled` y permite turnos pegados (rango `[)`); UNIQUE de notificaciones; CHECK de horarios
- **Dependencias**: `C-01`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` (completo, §appointments y §email_notifications)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU, §RN-NO-03, §RN-GL-01
  - `knowledge-base/10_preguntas_abiertas.md` (zona horaria SU-01, slot real)
  - `.claude/skills/supabase-postgres-best-practices/` (solo lo de PostgreSQL general; ignorar lo específico de Supabase y de RLS)
### [C-03] `auth-login-rbac`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `POST /api/v1/auth/login` (email + contraseña): verifica el hash, rechaza `users.active = false` y devuelve un JWT de acceso con el rol (US-001, RN-AU-03); error genérico en credenciales inválidas
  - `GET /api/v1/auth/me`; seguridad en `app/core/security.py` (hash argon2 o bcrypt, firma y verificación de JWT, expiración corta)
  - Dependencias de FastAPI `current_user()` y `require_role(...)`: todo endpoint salvo el login exige JWT válido (RN-AU-01); `current_user()` recarga el usuario desde la base en cada request y rechaza `active = false` y cambios de rol (el token no es la fuente de verdad del rol); matriz RBAC de `03_actores_y_roles.md`; odontólogo restringido a lo propio (RN-AU-04)
  - Librerías mantenidas: PyJWT y argon2-cffi (evitar python-jose y passlib, sin mantenimiento)
  - Frontend: pantalla `/login`, guardado del token en memoria o sessionStorage (riesgo de XSS aceptado y documentado), rutas protegidas y redirección a `/agenda` según rol
  - Sin RLS: la autorización vive solo en la aplicación (DD-02), por eso cada endpoint lleva su test de permisos
  - Tests: login válido/inválido/inactivo, token vencido, acceso por rol, dentist no lee turnos ajenos
- **Dependencias**: `C-02`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU, §RN-PR
  - `knowledge-base/07_flujos_principales.md` §Flujo 1
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/10_preguntas_abiertas.md` (quién edita horarios, SU-06; refresh token, SU-07)
### [C-04] `user-management`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - US-002: endpoints `/api/v1/users` (solo admin) y pantalla `/usuarios`: crear, editar rol, desactivar usuarios
  - Validación con Pydantic; contraseña inicial con hash, nunca expuesta en respuestas (RN-PR-03)
  - Al crear un usuario `dentist` se crea su fila `professionals` asociada en la misma operación
  - Caso de uso `gestionar_usuarios` con chequeo `require_role('admin')`
  - Tests: solo admin accede; alta de dentist crea professional; desactivar bloquea login
- **Dependencias**: `C-03`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/06_funcionalidades.md` §US-002
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-02, §RN-AU-03
  - `knowledge-base/04_modelo_de_datos.md` §users, §professionals
---

## FASE 2 — Dominio y catálogos

> C-05 no depende de la base de datos: corre en paralelo con C-02/C-03 (GATE 0).

### [C-05] `domain-scheduling-core`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `app/core/timezone.py`: conversión UTC <-> zona del consultorio (RN-GL-01), inicio/fin de día local
  - `app/domain/schedules`: validación de tramos (`start < end`, sin superposición, RN-HO-02); `is_date_in_time_off`
  - `app/domain/appointments`: `compute_slots(working_hours, time_off, appointments, slot_minutes, date)` (libre / ocupado / fuera de horario); `validate_appointment` (RN-TU-01 a RN-TU-04: grilla, dentro de tramo, fuera de licencia, no pasado, sin solape); transiciones de estado (RN-TU-05, RN-TU-07)
  - `app/domain/patients`: regla de paciente inactivo (RN-PA-04)
  - Puertos (interfaces) de repositorios + repos en memoria para tests
  - Tests pytest exhaustivos (puros, sin base ni red): bordes de tramos, cambio de día por zona horaria, licencias, turnos pegados
- **Dependencias**: `C-01`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-HO, §RN-TU, §RN-GL-01
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados
  - `knowledge-base/07_flujos_principales.md` §Flujo 2, §Flujo 5
  - `knowledge-base/10_preguntas_abiertas.md` (duración fija de slot, varios turnos por día SU-05, zona horaria SU-01)

### [C-06] `patients-crud`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - US-003: pantalla `/pacientes` en React (listado, búsqueda por apellido y documento, alta, edición, desactivación)
  - API `/api/v1/patients`, `PatientRepository` (SQLAlchemy) y casos de uso con validación Pydantic: nombre, apellido, documento y email obligatorios; documento único (RN-PA-01/02); desactivar en lugar de borrar (RN-PA-03)
  - Permisos: admin CRUD, recepción CRU, odontólogo solo lectura
  - Tests: duplicado de documento, búsqueda, desactivación, permisos por rol
- **Dependencias**: `C-03`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-003
  - `knowledge-base/04_modelo_de_datos.md` §patients
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PA
  - `knowledge-base/03_actores_y_roles.md` §RBAC

### [C-07] `professional-schedules`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - US-004 y US-005: `/profesionales` con listado, edición de `working_hours` (varios tramos por día) y carga de `time_off`
  - Repositorios `WorkingHoursRepository`, `TimeOffRepository`; validación con `domain/schedules` (C-05)
  - Detección de conflictos (RN-HO-04): al cambiar horarios o cargar licencia, listar turnos `scheduled` afectados sin cancelarlos
  - Permisos según matriz: solo admin edita (decisión abierta SU-06: dejar la política en un único punto para cambiarla fácil); recepción y dentist (propio) solo leen
  - Tests: tramos superpuestos rechazados, conflictos listados, licencia bloquea disponibilidad
- **Dependencias**: `C-03`, `C-05`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-004, §US-005
  - `knowledge-base/07_flujos_principales.md` §Flujo 5
  - `knowledge-base/05_reglas_de_negocio.md` §RN-HO
  - `knowledge-base/10_preguntas_abiertas.md` (quién edita horarios; aviso al paciente si hay conflicto)

---

## FASE 3 — Agenda de turnos (MVP)

### [C-08] `appointment-use-cases`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `AppointmentRepository` (SQLAlchemy) que traduce el error del constraint de exclusión a "el slot acaba de ocuparse"
  - Casos de uso en `app/application`: `agendar_turno`, `cancelar_turno` (con `cancel_reason`), `reprogramar_turno` (atómico: si falla no cambia el original, RN-TU-06), `marcar_atencion` (`completed`/`no_show`, solo propio, `scheduled` e iniciado)
  - Lectura mínima de paciente activo para RN-PA-04 (sin depender de la UI de C-06)
  - Puerto `NotificationPort` (no-op por defecto) invocado tras agendar/reprogramar/cancelar; C-11 lo implementa (RN-NO-04: nunca bloquea)
  - Endpoints `/api/v1/appointments` con esquemas Pydantic y chequeo de rol
  - Tests: happy path, slot ocupado, fuera de horario, pasado, concurrencia (dos inserciones simultáneas, una falla), reprogramación fallida no muta, permisos
- **Dependencias**: `C-03`, `C-05`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 2, §Flujo 3
  - `knowledge-base/06_funcionalidades.md` §US-007 a §US-010
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU, §RN-NO-04, §RN-NO-05
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados

### [C-09] `agenda-views`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - US-006: `/agenda` con vista diaria y semanal por profesional
  - Slots libres, ocupados y fuera de horario diferenciados (usa `compute_slots` de C-05 y horarios/licencias de C-07)
  - Consulta de solo lectura de los turnos del rango visible (query propia, sin depender de los casos de uso de C-08)
  - Selector de profesional para admin/recepción; odontólogo ve solo la propia (RN-AU-04)
  - Pantalla de inicio por rol tras el login
  - Componentes React reutilizables (grilla de slots, navegación de fechas); datos con un cliente de API; fechas mostradas en zona del consultorio
  - Tests con Vitest: componente de grilla, filtro por rol, cambio de semana
- **Dependencias**: `C-05`, `C-07`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-006
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-04, §RN-GL-01

### [C-10] `appointment-management-ui`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - UI para agendar desde un slot libre (buscar/crear paciente inline con C-06), cancelar con motivo, reprogramar y marcar atendido/ausente, conectada a los casos de uso de C-08
  - Mensajes de error claros (slot ocupado, fuera de horario, pasado, paciente inactivo)
  - Indicador de conflictos por cambio de horario/licencia (RN-HO-04) con acceso directo a reprogramar/cancelar
  - Tests de UI/flujo: agendar, choque de slot, cancelar libera slot, reprogramar
- **Dependencias**: `C-06`, `C-08`, `C-09`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-007 a §US-010
  - `knowledge-base/07_flujos_principales.md` §Flujo 2, §Flujo 3, §Flujo 5
  - `knowledge-base/01_vision_y_objetivos.md` (riesgo de adopción de recepción)
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios

---

## FASE 4 — Notificaciones por email

### [C-11] `email-confirmation-infra`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - **Primer paso (spike)**: elegir el proveedor SMTP gratuito de demo y verificar su cupo (SU-02); en desarrollo se usa Mailpit. Documentar el resultado en `09_decisiones_y_supuestos.md`
  - Aplicación Celery con Redis como broker (`app/infrastructure/tasks`); servicio `worker` en Docker Compose
  - `EmailSender` (puerto) + adaptador SMTP en `app/infrastructure/email`; plantillas de `confirmation` y `reminder` (paciente, profesional, fecha/hora, dirección del consultorio)
  - Encolado después del commit con `apply_async(retry=False)` y timeout corto; tarea de Beat `reencolar_pendientes` (cada 10 minutos) para las `pending` antiguas
  - `NotificationRepository` sobre `email_notifications`; implementación de `NotificationPort` (C-08): crear fila `pending`, encolar `enviar_email`, el worker envía y marca `sent`/`failed` con `error`
  - Confirmación al agendar y reprogramar; reprogramar reemplaza el recordatorio pendiente (RN-NO-05); cancelar no genera recordatorio
  - Fallos de envío y Redis caído nunca rompen la operación de turno (RN-NO-04)
  - Tests con `EmailSender` falso y Celery en modo inmediato: éxito, fallo registrado, idempotencia por UNIQUE
- **Dependencias**: `C-08`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/11_recordatorios_email.md` §Tipos de email, §Envío asincrónico, §Idempotencia y errores, §Límites y riesgos
  - `knowledge-base/05_reglas_de_negocio.md` §RN-NO
  - `knowledge-base/07_flujos_principales.md` §Flujo 2
  - `knowledge-base/10_preguntas_abiertas.md` (proveedor SMTP SU-02, Celery DD-10, contenido de la plantilla)
### [C-12] `reminders-cron` (Celery Beat)
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Tarea Celery `enviar_recordatorios` y servicio `beat` (Celery Beat) que la dispara cada hora; la tarea solo actúa cuando la hora local del consultorio es `clinic_settings.reminder_send_hour`; app Celery con `timezone` del consultorio y `enable_utc = True`; no hay endpoint HTTP
  - Caso de uso `enviar_recordatorios`: turnos `scheduled` del día siguiente (zona del consultorio) sin `reminder`; un fallo se registra y el lote continúa (US-011); registra `{ processed, sent, failed }` en el log
  - Reintento opcional de `failed` del mismo día (decisión a confirmar)
  - Tests: doble ejecución no reenvía, cancelado excluido, fallo parcial no corta el lote, borde de zona horaria, la tarea solo actúa a la hora configurada
- **Dependencias**: `C-11`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/11_recordatorios_email.md` §Programación del recordatorio, §Tareas
  - `knowledge-base/07_flujos_principales.md` §Flujo 4
  - `knowledge-base/10_preguntas_abiertas.md` (IN-01, zona horaria)
  - `knowledge-base/06_funcionalidades.md` §US-011
---

## FASE 5 — Salida a producción

### [C-13] `deploy-and-hardening`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Dockerfile del frontend multi-stage (build con `VITE_API_URL` como build-arg, servido con nginx); en desarrollo, servidor de Vite; Mailpit solo en desarrollo
  - Empaquetado final con Docker Compose: un comando levanta `db`, `redis`, `api`, `worker`, `beat`, `frontend` y `mailpit`; migraciones y seed ficticio aplicados al iniciar
  - Variables de entorno de producción o demo (secretos solo en el servidor y fuera del repositorio, RN-PR-03); CORS limitado al frontend
  - Revisión de permisos: matriz de tests por endpoint y rol; ninguna ruta sin JWT salvo el login; ningún secreto en el bundle del frontend
  - Smoke test end-to-end: login por rol -> agendar -> email de confirmación visible en Mailpit -> cancelar -> reprogramar -> ejecución de la tarea de recordatorios
  - README con setup, comandos, variables y decisiones abiertas pendientes
  - Checklist de adopción para recepción (riesgo de negocio)
- **Dependencias**: `C-04`, `C-10`, `C-12`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad, §Variables de entorno
  - `knowledge-base/11_recordatorios_email.md` §Límites y riesgos
  - `knowledge-base/01_vision_y_objetivos.md`
  - `knowledge-base/10_preguntas_abiertas.md`
---

## Alineación con el informe de Discovery (sección D.3)

El informe `docs/discovery/informe-discovery.md` recomienda un MVP en tres niveles. Esta tabla muestra qué cubre este roadmap y qué queda afuera, con el motivo (decisiones DD-07, DD-08 y DD-09 de `knowledge-base/09_decisiones_y_supuestos.md`).

### Imprescindible según el informe

| Recomendación del informe (D.3, Imprescindible) | Cobertura | Change | Justificación si no se cubre |
|---|---|---|---|
| Agenda multi-profesional con prevención de solapamientos | Cubierta | C-02, C-05, C-07, C-08, C-09, C-10 | — |
| Agenda multi-sillón/box con duración por prestación y bloqueos | **Parcial**: solo bloqueos por día completo (licencias) y slot fijo; sin bloqueos horarios, sin sillón/box y sin duración por prestación | C-05, C-07 | DD-03 y DD-08 (RN-TU-09, RN-TU-10): cambia el esquema y el algoritmo; primera mejora posterior |
| Reserva online por enlace, con confirmación, cancelación y reprogramación por el paciente | **No cubierta** (la recepción sí cancela y reprograma: C-08, C-10) | — | DD-07; `01_vision_y_objetivos.md` §Fuera de alcance: turnos online y login para pacientes |
| Recordatorios y confirmaciones por WhatsApp | **Parcial, sustituida por email**: recordatorio y aviso informativo; el paciente no puede confirmar ni cancelar (DD-06) | C-11, C-12 | DD-09: la API de WhatsApp Business cobra; restricción de costo cero |
| Ficha del paciente con anamnesis, odontograma, evolución y adjuntos (radiografías) | **No cubierta**: C-06 solo da el ABM de datos de contacto, base para la ficha futura | C-06 (base) | DD-07: historia clínica fuera de v1 |
| Roles y permisos básicos | Cubierta (roles fijos) | C-03, C-04 | — |
| Registro de auditoría de accesos | **No cubierta** | — | DD-07: fuera de v1. El chequeo de rol restringe accesos pero no los registra; no hay log de accesos |
| Exportación de datos | **No cubierta** | — | DD-07: fuera de v1 por alcance. El informe la marca como vacío del mercado y oportunidad de diferenciación (C.4, C.5); candidata prioritaria tras v1 |

### Diferenciadores y etapas posteriores (D.3)

Ninguno de estos 14 ítems está en el roadmap. Es coherente con el alcance v1 (DD-07) y queda registrado en `06_funcionalidades.md`.

| Nivel | Ítem del informe | Cobertura | Motivo |
|---|---|---|---|
| Diferenciador | Lista de espera con oferta de huecos liberados | No cubierta | Fuera de v1 (DD-07) |
| Diferenciador | Sobreturnos controlados | No cubierta | RN-TU-11: no se permiten en v1 |
| Diferenciador | Seña con Mercado Pago atada al turno | No cubierta | Fuera de v1 y de costo cero (DD-07) |
| Diferenciador | Panel de ausentismo y ocupación de sillón | No cubierta | Reportes excluidos en `01_vision_y_objetivos.md` §Fuera de alcance; C-08 registra `no_show` como base |
| Etapa posterior | Presupuestos y planes de tratamiento | No cubierta | Fuera de alcance (cobros y presupuestos) |
| Etapa posterior | Periodontograma | No cubierta | Depende de la ficha clínica, fuera de v1 |
| Etapa posterior | Facturación electrónica ARCA | No cubierta | Fuera de v1 |
| Etapa posterior | Obras sociales y prepagas | No cubierta | Fuera de v1 |
| Etapa posterior | Receta electrónica | No cubierta | Fuera de v1 |
| Etapa posterior | Multi-sucursal | No cubierta | SU-04: un solo consultorio |
| Etapa posterior | Reportes avanzados | No cubierta | Reportes excluidos de v1 |
| Etapa posterior | Reactivación de pacientes y campañas | No cubierta | Fuera de v1 |
| Etapa posterior | Asistente conversacional con IA | No cubierta | Fuera de v1 |
| Etapa posterior | Consentimientos con firma digital | No cubierta | Fuera de v1 |

### Changes del roadmap que el informe no pide

Ninguno agrega funcionalidades que el informe desaconseje o que el MVP excluya (historia clínica, cobros, turnos online, WhatsApp, reportes). Los 13 changes salen de funciones del MVP recomendado o de trabajo técnico necesario (C-01 fundación, C-02 base de datos, C-13 despliegue). Se apartan del informe: C-11 y C-12 usan email en lugar de WhatsApp (DD-09), y C-08 registra `no_show`, lo que deja la base para un futuro panel de ausentismo.

---

## Riesgos del roadmap

| # | Riesgo | Change afectado | Mitigación |
|---|---|---|---|
| R-1 | Sin proveedor SMTP gratuito definido para la demo | C-11, C-12 | Spike al inicio de C-11; desarrollo con Mailpit (SU-02) |
| R-2 | Redis o el worker de Celery caídos: no salen emails ni recordatorios | C-11, C-12 | La operación de turno nunca depende del envío (RN-NO-04); `reencolar_pendientes` recoge las notificaciones `pending` |
| R-3 | La cátedra puede preferir otra herramienta distinta de Celery sobre Redis | C-01, C-11, C-12 | Confirmar con el profesor en C-01 (DD-10) |
| R-4 | Errores de zona horaria en turnos y recordatorios | C-02, C-05, C-12 | Fechas en UTC y zona del consultorio en configuración (RN-GL-01); tests de borde |
| R-5 | Concurrencia: dos recepcionistas agendan el mismo slot | C-02, C-08 | Constraint de exclusión en la base (DD-04) |
| R-6 | Módulos de gobernanza CRÍTICA (auth, esquema) y autorización solo en la aplicación, sin RLS | C-02, C-03 | Análisis y aprobación humana antes de escribir código; test de permisos por cada endpoint |
| R-7 | Sin recordatorios por WhatsApp el producto queda por debajo del estándar del mercado | C-11, C-12 | DD-09; evaluar enlace `wa.me` manual tras v1 |
| R-8 | Adopción: la recepción puede seguir usando planilla y WhatsApp | C-13 | Checklist de adopción; probar con una recepcionista real |
| R-9 | El informe se basa solo en páginas comerciales y sin demos | Todo el roadmap | Validar prioridades con odontólogos reales antes de construir funciones grandes |
| R-10 | Tratamiento legal de datos personales sin revisar (Ley 25.326; Ley 27.706 si se agrega ficha clínica) | C-02, C-06, C-13 | v1 usa solo datos ficticios; no declarar cumplimiento; revisión legal antes de usar datos reales (`10_preguntas_abiertas.md`) |
| R-11 | Migrar luego a sillón o duración variable (DD-08) exige cambiar el constraint EXCLUDE y `compute_slots` | C-02, C-05 | Encapsular la duración en un único punto del dominio y documentar el punto de extensión |

---

## Tabla resumen

| ID | Change | Fase | Deps | Governance |
|----|--------|------|------|------------|
| C-01 | foundation-setup | 0 | — | BAJO |
| C-02 | db-schema-and-seed | 1 | C-01 | CRITICO |
| C-03 | auth-login-rbac | 1 | C-02 | CRITICO |
| C-04 | user-management | 1 | C-03 | ALTO |
| C-05 | domain-scheduling-core | 2 | C-01 | MEDIO |
| C-06 | patients-crud | 2 | C-03 | BAJO |
| C-07 | professional-schedules | 2 | C-03, C-05 | MEDIO |
| C-08 | appointment-use-cases | 3 | C-03, C-05 | MEDIO |
| C-09 | agenda-views | 3 | C-05, C-07 | BAJO |
| C-10 | appointment-management-ui | 3 | C-06, C-08, C-09 | MEDIO |
| C-11 | email-confirmation-infra | 4 | C-08 | ALTO |
| C-12 | reminders-cron | 4 | C-11 | ALTO |
| C-13 | deploy-and-hardening | 5 | C-04, C-10, C-12 | MEDIO |

**Primer change recomendado**: `C-01` (foundation-setup). Para arrancar: `/opsx:propose C-01-foundation-setup`
