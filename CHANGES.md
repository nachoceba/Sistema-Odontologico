# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto Sistema Odontológico (agenda de turnos + recordatorios por email).
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

Stack: Next.js + Supabase (Postgres/Auth) + Resend, en Vercel free tier. Prioridad de calidad: mantenibilidad (capas domain / application / infrastructure). Todo gratuito, datos de pacientes ficticios.

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
  → C-10 appointment-management-ui         [Agente B — si C-08 ✓, C-09 ✓, C-06 ✓]

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
| 6 | C-12 | C-10 | — |
| 7 | C-13 | — | — |

---

## FASE 0 — Fundación

### [C-01] `foundation-setup`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Proyecto Next.js (App Router, TypeScript) con estructura `src/app`, `src/domain`, `src/application`, `src/infrastructure/{supabase,email}`, `src/shared`, `supabase/`, `tests/`
  - Vitest configurado (tests unitarios de dominio + carpeta de integración); lint y format
  - `.env.example` con las 7 variables de `08_arquitectura_propuesta.md` (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `RESEND_API_KEY`, `EMAIL_FROM`, `CRON_SECRET`, `CLINIC_TIMEZONE`); validación de env en servidor
  - Proyecto Supabase creado y Supabase CLI enlazado (`supabase/migrations/`, `supabase/seed.sql` vacíos)
  - `src/shared/errors.ts` (errores de dominio tipados)
  - Riesgo a registrar: verificar límites vigentes del plan gratuito de Supabase/Vercel (SU-02, SU-03)
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Variables de entorno
  - `knowledge-base/09_decisiones_y_supuestos.md`
  - `knowledge-base/01_vision_y_objetivos.md`

---

## FASE 1 — Datos y acceso

### [C-02] `db-schema-and-seed`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Migración 001: extensión `btree_gist`; enums `user_role`, `appointment_status`, `notification_kind`, `notification_status`
  - Migración 002: tablas `profiles`, `professionals`, `working_hours`, `time_off`, `patients`, `appointments`, `email_notifications`, `clinic_settings` con todos los CHECK/UNIQUE/FK del modelo
  - `appointments`: `EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&) WHERE (status = 'scheduled')`; índices `(professional_id, starts_at)` y `(starts_at)`
  - `email_notifications`: `UNIQUE (appointment_id, kind)`
  - `supabase/seed.sql`: 1 admin, 1 recepción, 2 profesionales con `working_hours` L-V, `clinic_settings` (30 min, `America/Argentina/Buenos_Aires`, hora 9), 10 pacientes ficticios con emails de prueba controlados por el equipo
  - Tests de integración: constraint de exclusión rechaza solapamiento `scheduled`, permite solapar con `cancelled`; UNIQUE de notificaciones; CHECK de horarios
  - Tipos TS generados desde el esquema
- **Dependencias**: `C-01`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` (completo, §appointments y §email_notifications)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU, §RN-NO-03, §RN-GL-01
  - `knowledge-base/10_preguntas_abiertas.md` (zona horaria SU-01, slot real)

### [C-03] `auth-login-rbac`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Supabase Auth con sesión por cookie en servidor (`@supabase/ssr`); clientes browser/server/service en `src/infrastructure/supabase`
  - `/login` (email + contraseña), error genérico en credenciales inválidas, rechazo de `profiles.active = false` (US-001, RN-AU-03)
  - Middleware: toda ruta salvo `/login` exige sesión (RN-AU-01); redirección a `/agenda` según rol
  - Helper de autorización `requireRole()` / `currentUser()` en application (matriz RBAC de `03_actores_y_roles.md`); odontólogo restringido a lo propio (RN-AU-04)
  - Migración 003: RLS por rol en todas las tablas (defensa en profundidad, RN-PR-02)
  - Tests: login válido/inválido/inactivo, acceso por rol, RLS (dentist no lee turnos ajenos)
- **Dependencias**: `C-02`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU, §RN-PR
  - `knowledge-base/07_flujos_principales.md` §Flujo 1
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/10_preguntas_abiertas.md` (quién edita horarios, SU-06: la matriz asume solo admin)

### [C-04] `user-management`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - US-002: pantalla `/usuarios` (solo admin): crear, editar rol, desactivar usuarios
  - Server Actions con Zod; creación vía Supabase Admin API (service role solo en servidor, RN-PR-03)
  - Al crear un usuario `dentist` se crea su fila `professionals` asociada en la misma operación
  - Caso de uso `gestionarUsuarios` con chequeo `requireRole('admin')`
  - Tests: solo admin accede; alta de dentist crea professional; desactivar bloquea login
- **Dependencias**: `C-03`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/06_funcionalidades.md` §US-002
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-02, §RN-AU-03
  - `knowledge-base/04_modelo_de_datos.md` §profiles, §professionals

---

## FASE 2 — Dominio y catálogos

> C-05 no depende de la base de datos: corre en paralelo con C-02/C-03 (GATE 0).

### [C-05] `domain-scheduling-core`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `src/shared/datetime`: conversión UTC <-> zona del consultorio (RN-GL-01), inicio/fin de día local
  - `src/domain/schedules`: validación de tramos (`start < end`, sin superposición, RN-HO-02); `isDateInTimeOff`
  - `src/domain/appointments`: `computeSlots(workingHours, timeOff, appointments, slotMinutes, date)` (libre / ocupado / fuera de horario); `validateAppointment` (RN-TU-01 a RN-TU-04: grilla, dentro de tramo, fuera de licencia, no pasado, sin solape); transiciones de estado (RN-TU-05, RN-TU-07)
  - `src/domain/patients`: regla de paciente inactivo (RN-PA-04)
  - Puertos (interfaces) de repositorios + repos en memoria para tests
  - Tests Vitest exhaustivos (puros, sin red): bordes de tramos, cambio de día por zona horaria, licencias, turnos pegados
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
  - US-003: `/pacientes` (listado, búsqueda por apellido y documento, alta, edición, desactivación)
  - `PatientRepository` (Supabase) + casos de uso con validación Zod: nombre, apellido, documento y email obligatorios; documento único (RN-PA-01/02); desactivar en lugar de borrar (RN-PA-03)
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
  - `AppointmentRepository` (Supabase) que traduce el error del constraint de exclusión a "el slot acaba de ocuparse"
  - Casos de uso en `src/application`: `agendarTurno`, `cancelarTurno` (con `cancel_reason`), `reprogramarTurno` (atómico: si falla no cambia el original, RN-TU-06), `marcarAtencion` (`completed`/`no_show`, solo propio, `scheduled` e iniciado)
  - Lectura mínima de paciente activo para RN-PA-04 (sin depender de la UI de C-06)
  - Puerto `NotificationPort` (no-op por defecto) invocado tras agendar/reprogramar/cancelar; C-11 lo implementa (RN-NO-04: nunca bloquea)
  - Server Actions con Zod y chequeo de rol
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
  - Slots libres, ocupados y fuera de horario diferenciados (usa `computeSlots` de C-05 y horarios/licencias de C-07)
  - Consulta de solo lectura de los turnos del rango visible (query propia, sin depender de los casos de uso de C-08)
  - Selector de profesional para admin/recepción; odontólogo ve solo la propia (RN-AU-04)
  - Pantalla de inicio por rol tras el login
  - Componentes de UI reutilizables (grilla de slots, navegación de fechas); fechas mostradas en zona del consultorio
  - Tests: componente de grilla, filtro por rol, cambio de semana
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
  - **Primer paso (spike)**: verificar límites reales del plan gratuito de Resend sin dominio propio (SU-02) y documentar el resultado en `09_decisiones_y_supuestos.md`; NO se resuelve aquí la duda del KB, solo se valida
  - `EmailSender` (puerto) + adaptador Resend en `src/infrastructure/email`; plantillas de `confirmation` y `reminder` (paciente, profesional, fecha/hora, dirección del consultorio)
  - `NotificationRepository` sobre `email_notifications`; implementación de `NotificationPort` (C-08): crear fila `pending` -> enviar -> `sent`/`failed` con `error`
  - Confirmación al agendar y reprogramar; reprogramar reemplaza el recordatorio pendiente (RN-NO-05); cancelar no genera recordatorio
  - Fallos de envío nunca rompen la operación de turno (RN-NO-04)
  - Tests con `EmailSender` falso: éxito, fallo registrado, idempotencia por UNIQUE
- **Dependencias**: `C-08`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/11_recordatorios_email.md` §Tipos de email, §Idempotencia y errores, §Límites y riesgos
  - `knowledge-base/05_reglas_de_negocio.md` §RN-NO
  - `knowledge-base/07_flujos_principales.md` §Flujo 2
  - `knowledge-base/10_preguntas_abiertas.md` (límites de Resend SU-02, contenido de la plantilla)

### [C-12] `reminders-cron`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `GET/POST /api/cron/reminders` con `Authorization: Bearer $CRON_SECRET` (401 si falta o es inválido); responde `{ processed, sent, failed }`
  - Caso de uso `enviarRecordatorios`: turnos `scheduled` del día siguiente (zona del consultorio) sin `reminder`; un fallo se registra y el lote continúa (US-011)
  - Programación diaria a `clinic_settings.reminder_send_hour` vía Vercel Cron (`vercel.json`) o `pg_cron` según lo que permita el plan gratuito (SU-03: validar frecuencia antes de fijar la opción; no se resuelve en este documento)
  - Reintento opcional de `failed` del mismo día (decisión a confirmar)
  - Tests: sin secreto -> 401, doble ejecución no reenvía, cancelado excluido, fallo parcial no corta el lote, borde de zona horaria
- **Dependencias**: `C-11`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/11_recordatorios_email.md` §Programación del recordatorio, §Endpoint
  - `knowledge-base/07_flujos_principales.md` §Flujo 4
  - `knowledge-base/10_preguntas_abiertas.md` (IN-01, frecuencia de cron gratuito SU-03, zona horaria)
  - `knowledge-base/06_funcionalidades.md` §US-011

---

## FASE 5 — Salida a producción

### [C-13] `deploy-and-hardening`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Deploy en Vercel; variables de entorno de producción (secrets solo en servidor, RN-PR-03); proyecto Supabase con migraciones y seed ficticio aplicados
  - Verificación del cron en producción y de que Resend envía a los emails de prueba controlados
  - Revisión de RLS y de rutas: ninguna ruta pública salvo `/login`; ningún secreto en el bundle del cliente
  - Smoke test end-to-end: login por rol -> agendar -> email de confirmación -> cancelar -> reprogramar -> ejecución del cron
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
| Registro de auditoría de accesos | **No cubierta** | — | DD-07: fuera de v1. RLS restringe accesos pero no los registra; no hay log de accesos |
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
| R-1 | Límites del plan gratuito de Resend (sin dominio propio solo envía a la cuenta dueña) | C-11, C-12 | Spike al inicio de C-11; probar con buzones controlados (SU-02) |
| R-2 | El cron gratuito puede limitarse a una ejecución diaria; el aviso saldría el día anterior | C-12 | Validar Vercel Cron o pg_cron antes de fijar la opción (SU-03, IN-01) |
| R-3 | Límites vigentes de Supabase y Vercel (plan gratuito) | C-01, C-13 | Verificarlos en C-01 y registrarlos |
| R-4 | Errores de zona horaria en turnos y recordatorios | C-02, C-05, C-12 | Fechas en UTC y zona del consultorio en configuración (RN-GL-01); tests de borde |
| R-5 | Concurrencia: dos recepcionistas agendan el mismo slot | C-02, C-08 | Constraint de exclusión en la base (DD-04) |
| R-6 | Módulos de gobernanza CRÍTICA (auth, esquema, RLS) | C-02, C-03 | Análisis y aprobación humana antes de escribir código |
| R-7 | Sin recordatorios por WhatsApp el producto queda por debajo del estándar del mercado | C-11, C-12 | DD-09; evaluar enlace `wa.me` manual tras v1 |
| R-8 | Adopción: la recepción puede seguir usando planilla y WhatsApp | C-13 | Checklist de adopción; probar con una recepcionista real |
| R-9 | El informe se basa solo en páginas comerciales y sin demos | Todo el roadmap | Validar prioridades con odontólogos reales antes de construir funciones grandes |
| R-10 | Tratamiento legal de datos personales sin revisar (Ley 25.326; Ley 27.706 si se agrega ficha clínica) | C-02, C-06, C-13 | v1 usa solo datos ficticios; no declarar cumplimiento; revisión legal antes de usar datos reales (`10_preguntas_abiertas.md`) |
| R-11 | Migrar luego a sillón o duración variable (DD-08) exige cambiar el constraint EXCLUDE y `computeSlots` | C-02, C-05 | Encapsular la duración en un único punto del dominio y documentar el punto de extensión |

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
