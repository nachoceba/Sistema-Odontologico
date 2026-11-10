# Design: C-15 `public-patient-booking`

La motivación y el alcance están en `proposal.md`. El comportamiento exigible está en las specs del change:

- Nuevas: `public-booking`, `public-booking-api` y `frontend-public-booking`.
- Deltas: `access-control`, `database-schema`, `appointment-api`, `appointment-use-cases`, `reminder-scheduling`, `notification-tasks`, `email-templates`, `runtime-configuration`, `frontend-auth`, `frontend-agenda` y `frontend-appointment-management`.

## Context

Esto es lo que ya existe y se reutiliza, observado en el código:

- **Agendar en la recepción** (`app/application/appointments.py`): `book_appointment` valida con `_validated_end`. Esa función revisa la grilla, el horario, las licencias y la anticipación mínima con `validate_appointment`, y que el paciente no tenga otro turno superpuesto con `_require_patient_free`. Después escribe el turno y la confirmación `pending` en `SqlAlchemyAgendaUnitOfWork`, en una sola transacción, y despacha después del commit. `day_slots` usa `load_context` + `compute_slots`. Solo `scheduled` ocupa una franja (DD-16).
- **`created_by`**: es `NOT NULL` y FK a `users.id`.
- **Errores del repositorio**: `SqlAlchemyAppointmentRepository.add` traduce el 23P01 de `ex_appointments_no_overlap` a `SlotTakenError`, y el repositorio de pacientes traduce el único de documento a `DocumentTakenError`.
- **Envío de emails**: `deliver_notification` toma el destinatario de la ficha al enviar (`patient.email`). La tarea de recordatorios registra con `INSERT … SELECT … FOR SHARE ON CONFLICT DO NOTHING` (DD-103). El reclamo de notificaciones usa `FOR UPDATE SKIP LOCKED` (DD-94).
- **Inventario de rutas**: `test_route_inventory.py` (`PUBLIC_ROUTES`) y `test_permission_matrix.py` (`MATRIX`, donde `None` es pública) obligan a declarar cada ruta pública.
- **Redis**: corre en Compose y el paquete `redis` llega con `celery[redis]`.
- **Frontend**: `App.tsx` envuelve todo en `AuthProvider` y muestra "cargando" hasta resolver la sesión. `apiFetch(..., { auth: false })` evita mandar el token y cerrar la sesión.

## Goals / Non-Goals

**Goals:**
- La reserva pública usa las mismas reglas puras y el mismo constraint que la recepción (regla dura 6), con carreras probadas.
- Ninguna respuesta pública revela si un DNI existe con un nombre dado, más allá del rechazo genérico. Ninguna escritura pública modifica una ficha existente.
- Ninguna reserva queda confirmada sin que lo apruebe el dueño del email de la ficha.
- Ninguna dependencia ni servicio externo nuevo.

**Non-Goals:**
- Login o portal del paciente; cancelar o reprogramar por el paciente (P-9).
- CAPTCHA externo.
- Confirmación manual por la recepción (Q-3 A).
- Código numérico de confirmación (Q-4 A).
- Vencimiento automático y email de cancelación por falta de confirmación: van en C-16 `online-booking-expiry`.

## Decisiones resueltas

### DD-128 — Paso "¿Es usted J*** P***?" — REEMPLAZADA por DD-129

Quedó elegida en la ronda anterior y el usuario la reemplazó. No se implementa ni la consulta de documento ni el nombre enmascarado. En `09_decisiones_y_supuestos.md` se registra como reemplazada, solo para trazabilidad.

### DD-129 — Identificación por DNI y nombre, con rechazo genérico

- El formulario siempre pide DNI, nombre, apellido y email; el teléfono es opcional.
- Si el DNI existe, se compara nombre y apellido con la ficha usando la función pura `same_person_name(a, b)` en `app/domain/patients/rules.py`: NFKD, se quitan los diacríticos, se pasa a mayúsculas y se reducen los espacios.
- Si coinciden, el turno se vincula a la ficha. El email y el teléfono escritos se ignoran.
- Si no coinciden, la respuesta es `BOOKING_NOT_POSSIBLE` ("Verifique sus datos ingresados."). Es el mismo código, mensaje y forma que el paciente inactivo, el turno superpuesto y la carrera de DNI.
- El DNI nuevo crea la ficha.
- Para que el tiempo de respuesta sea parecido, el rechazo se decide después de cargar el contexto de agenda, igual que una reserva válida.

**Riesgo conocido.** Un DNI inexistente siempre "funciona" y uno existente con nombre equivocado da el rechazo. Así, quien prueba DNIs con un nombre cualquiera puede saber cuáles existen. No obtiene ningún dato de la ficha, y el tope de 5 reservas por hora por IP vuelve la prueba muy lenta. La alternativa que lo evita (responder "Te enviamos un email" también al nombre equivocado, sin crear nada) contradice el mensaje que pidió el usuario y deja sin aviso a quien se equivocó al tipear. Queda anotada para que el usuario la considere.

### DD-130 — Reserva pendiente: `scheduled` + `pending_until`, sin estado nuevo

Opciones evaluadas para "Pendiente de confirmación":

| Opción | Migración | Qué más cambia |
|---|---|---|
| **(elegida) `status = scheduled` + columna `pending_until`** | `0003`: 2 columnas nulas, 2 CHECK y 2 índices parciales | Nada en el constraint de exclusión, `compute_slots`, la superposición del paciente ni las transiciones. Solo hay que excluir los pendientes de los recordatorios y bloquear reprogramar y marcar atención. |
| Estado nuevo `pending_confirmation` | `ALTER TYPE … ADD VALUE` (no se puede usar en la misma transacción), recrear `ex_appointments_no_overlap` con `WHERE status IN (...)` y revisar CHECKs | Tocar la regla DD-16 (solo `scheduled` ocupa), `compute_slots`, `patient_has_overlap`, `validate_status_change`, los listados, los tipos del frontend y los textos de estado. El riesgo de romper la regla dura 6 es mayor. |
| Tabla aparte de "reservas" que se pasa a turno al confirmar | Tabla nueva con su propio constraint de exclusión, o retención sin garantía de la base | Dos fuentes de ocupación: la superposición se valida en dos lugares. |

Columnas nuevas en `appointments`:

- `pending_until timestamptz NULL`. Se calcula como `min(reserva + ONLINE_BOOKING_HOLD_MINUTES, starts_at)`.
- `confirmation_token_hash text NULL`.

Constraints:

- CHECK: `(pending_until IS NULL) = (confirmation_token_hash IS NULL)`.
- CHECK: `pending_until IS NULL OR created_by IS NULL`.
- Índice único parcial sobre `confirmation_token_hash`.
- Índice parcial sobre `pending_until`.

La misma migración vuelve opcional `created_by`. La reversión falla si hay turnos online.

En el dominio, `Appointment` suma `pending_until: datetime | None`. El hash no sube al dominio: lo maneja el repositorio.

### DD-131 — Token de un solo uso con hash, enlace con fragmento y POST

- **Token y hash**: el token es `secrets.token_urlsafe(32)`. En la base se guarda `sha256(token)` en hexadecimal. Un hash rápido alcanza, porque el token tiene 256 bits de entropía.
- **Generación**: va en `app/core/security.py`, junto a la de contraseñas. El dominio recibe un generador inyectado para poder probarlo.
- **Enlace**: `PUBLIC_APP_URL/turnos/confirmar#token=…`. Con el fragmento, el token no llega a nginx, a los logs ni al `Referer`.
- **Página**: hace `POST /api/v1/public/appointment-confirmations` solo cuando se toca el botón. Así, un previsualizador de email no puede confirmar el turno.
- **Confirmación**: en una transacción, `SELECT … WHERE confirmation_token_hash = :h FOR UPDATE`. Se valida que el turno esté `scheduled`, que `pending_until > now` y que `now < starts_at`. Después se pone `pending_until = NULL` y `confirmation_token_hash = NULL`, se llama a `notifications.add_pending_confirmation` y se despacha después del commit (C-11 sin cambios).
- **Rechazos**: todos son `CONFIRMATION_LINK_INVALID` (410).
- **Cancelación por la recepción**: si cancela un pendiente, `cancel_appointment` también limpia las dos columnas.

### DD-132: Plazo de la reserva en C-15 y vencimiento automático en C-16

- **En C-15**: `pending_until` se calcula al reservar con `ONLINE_BOOKING_HOLD_MINUTES`, que va de 5 a 1440 y vale 60 por defecto (DD-134). La confirmación ya rechaza un pendiente vencido.
- **En C-16** (`online-booking-expiry`, que depende de este change): la tarea de Beat cada 5 minutos que cancela los vencidos con `FOR UPDATE SKIP LOCKED`, los tests de la carrera entre confirmar y vencer, y el email de cancelación por falta de confirmación (DD-140).
- **Hasta C-16**: un pendiente vencido sigue ocupando su franja hasta que la recepción lo cancela, y no se envía ningún email de cancelación.

### DD-133 — Lo que ve la recepción

- La API agrega `origin` y `pending_until`.
- La grilla, la semana y el detalle muestran "Pendiente de confirmación" (con "hasta las HH:MM" en el detalle) u "Online".
- Sobre un pendiente solo se puede "Cancelar". `reschedule_appointment` y `record_attendance` rechazan `PENDING_CONFIRMATION` (409).

### D-6 — Caso de uso público y transacción

`app/application/public_booking.py` tiene `list_public_professionals`, `public_day_slots`, `book_online`, `confirm_online_booking` y `expire_pending_bookings`.

- **Reglas compartidas**: `_validated_end` pasa a llamarse `validated_end`, sin cambiar su comportamiento, y lo comparten la recepción y la reserva pública.
- **Unidad de trabajo**: `AgendaUnitOfWork` suma `patients`, con `get_by_document` y `add` sobre la misma sesión.
- **`book_online`**: con la transacción abierta, busca el documento y crea el paciente si no existe. Después hace `appointments.add_pending(...)`, con el hash y `pending_until`. Por último, después del commit, encola la verificación con el token en claro.
- **Traducción de rechazos**:
  - `DocumentTakenError` (carrera de DNI) → `BOOKING_NOT_POSSIBLE`.
  - `PatientInactiveError` y `PatientDoubleBookedError` → `BOOKING_NOT_POSSIBLE`.
  - Los motivos de horario → `SLOT_UNAVAILABLE`.
  - `SlotTakenError` se mantiene.

### D-7 — Email de verificación fuera de `email_notifications`

El token en claro no se guarda. Por eso la tarea `enviar_verificacion_reserva(appointment_id, token)` lo recibe por la cola de Redis, y antes de enviar comprueba que el hash coincida y que el turno siga pendiente. Reusa el `EmailSender` SMTP, `EMAIL_REDIRECT_TO` y el formato de las plantillas de C-11, con una plantilla nueva. El destinatario es siempre el email de la ficha: en un DNI nuevo es el que se escribió y en uno existente es el guardado.

Si Redis falla al encolar, no hay email y el turno queda pendiente hasta vencer (C-16 lo cancela solo). Se acepta, porque el paciente puede volver a reservar. La alternativa de guardar el token cifrado en la base, para reencolar, agrega una clave nueva y más superficie.

### D-8 — Límite de pedidos y campo trampa

- **Puerto**: `RateLimiter` en `app/domain/`.
- **Adaptadores**: `RedisRateLimiter`, con `INCR` + `EXPIRE` en una tubería sobre la clave `rl:{grupo}:{ip}:{ventana}`, y `InMemoryRateLimiter` para los tests.
- **IP**: sale de `request.client.host`. Nunca se usa `X-Forwarded-For`: la API no está detrás de un proxy (DD-106).
- **Si Redis falla**: falla abierta, con un aviso en el log.
- **Topes**: lecturas 60 por minuto, reservas 5 por hora, confirmaciones 10 por hora. Son constantes en `app/api/public.py`.
- **Campo trampa**: `website` en la reserva.
- **Context7**: al implementar, confirmar la API de tubería del cliente `redis`, sin enviar código ni datos.

### D-9 — Endpoints y frontend

- **Backend**:
  - `app/api/public.py` tiene el router `/public` con esquemas `extra="forbid"` y modelos de salida mínimos.
  - Códigos nuevos en `STATUS_BY_CODE`: `SLOT_UNAVAILABLE` 409, `BOOKING_NOT_POSSIBLE` 409, `CONFIRMATION_LINK_INVALID` 410, `PENDING_CONFIRMATION` 409, `BOOKING_REJECTED` 400 y `TOO_MANY_REQUESTS` 429 con `Retry-After`.
- **Frontend**:
  - `/turnos` y `/turnos/confirmar` se resuelven antes de `RequireAuth` y del "cargando" de la sesión, sin `AppLayout`.
  - `api/publicBooking.ts` siempre usa `{ auth: false }`.
  - Componentes en `frontend/src/public/`, revisados con `diseno-ui-odontologico`.
  - `Appointment` suma `origin` y `pending_until`, y `created_by` pasa a `string | null`.

### D-10 — Excepción a la regla dura 4 (texto exacto para `CLAUDE.md` y `AGENTS.md`)

> 4. Todo endpoint exige JWT y chequeo de rol (`require_role`), salvo el login, el chequeo de salud público (`GET /api/v1/health`, que solo responde `{"status": "ok"}` sin datos) y los cuatro endpoints de turnos online bajo `/api/v1/public/` (C-15: profesionales, franjas, reservar y confirmar), que no usan sesión pero llevan límite de pedidos por IP, validación estricta y campo trampa en la reserva, nunca devuelven datos de pacientes y nunca modifican una ficha existente; cada endpoint protegido lleva su test de permisos por rol y cada endpoint público, su test de acceso sin token y de límite de pedidos.

También se actualizan `knowledge-base/03`, `05`, `08` y `09`, y la spec `access-control` (delta de este change).

### D-11 — Textos propuestos para la KB

- **`01_vision_y_objetivos.md`**:
  - Alcance v1.0 suma "Turnos online para pacientes sin login, con confirmación por email (C-15)".
  - Fuera de alcance: "Turnos online y login para pacientes" pasa a "Login y cuentas de pacientes; cancelar o reprogramar por el paciente".
  - El objetivo del Paciente pasa a "Reservar su turno online y recibir confirmación y recordatorio".
- **`03_actores_y_roles.md`**:
  - Paciente: "No inicia sesión; reserva desde `/turnos`, confirma desde el enlace del email y recibe emails".
  - "Rutas públicas" suma `/turnos`, `/turnos/confirmar` y los cuatro endpoints.
  - La matriz RBAC suma la fila "Turnos pendientes: Recepción y Administrador solo cancelan".
- **`04_modelo_de_datos.md`**: `created_by` NULL significa online. Se agregan `pending_until` y `confirmation_token_hash` con sus CHECK e índices.
- **`05_reglas_de_negocio.md`**:
  - RN-AU-01 pasa a ser: "Todo endpoint salvo `POST /api/v1/auth/login`, `GET /api/v1/health` y los de `/api/v1/public/` requiere un JWT válido; en el frontend toda pantalla salvo `/login`, `/turnos` y `/turnos/confirmar` exige sesión."
  - RN-PR-02 suma: "La reserva pública nunca muestra datos de una ficha."
  - **RN-PA-05**: "El paciente se identifica por DNI; en una reserva online con DNI existente, nombre y apellido deben coincidir con la ficha (sin distinguir mayúsculas, tildes ni espacios) y la reserva nunca modifica la ficha."
  - **RN-TU-13**: "Una reserva online queda pendiente de confirmación y ocupa su franja como un turno `scheduled`; no recibe confirmación ni recordatorio hasta que se confirma desde el enlace enviado al email de la ficha."
  - **RN-TU-14** (la agrega C-16): "Una reserva pendiente que no se confirma dentro de `ONLINE_BOOKING_HOLD_MINUTES` (o antes de su inicio) se cancela sola con el motivo 'Reserva online no confirmada', libera la franja y genera un único aviso por email."
  - **RN-TU-15**: "Un turno pendiente solo se puede cancelar: no se reprograma ni se marca atendido o ausente."
  - **RN-NO-06**: "La reserva online envía un email de verificación con un enlace de un solo uso; el enlace vence con la reserva."
- **`06_funcionalidades.md`**: US-012 "Reservar un turno online" y US-013 "Confirmar la reserva desde el email". El backlog ya no lista "turnos online".
- **`07_flujos_principales.md`**: Flujo 6 "Reserva online" (reservar, verificar, confirmar o vencer).
- **`08_arquitectura_propuesta.md`**: en Seguridad, el límite de pedidos, el campo trampa y el token con hash. En las variables de entorno, `ONLINE_BOOKING_HOLD_MINUTES` y `PUBLIC_APP_URL`.
- **`09_decisiones_y_supuestos.md`**: DD-128 (reemplazada), DD-129 a DD-133 y DD-134 a DD-139. DD-140 la registra C-16.
- **`10_preguntas_abiertas.md`**: una pregunta nueva de prioridad media. ¿Cómo se evita que alguien registre primero el DNI de otra persona con datos inventados? Ver Q-5.
- **`11_recordatorios_email.md`**: tipos de email y tareas. Se suma la verificación (C-16 suma `vencer_reservas_pendientes` y el aviso de vencimiento), y se aclara que los recordatorios son solo de turnos confirmados.

## Estado de las decisiones anteriores (P-1 a P-10)

| P | Estado |
|---|---|
| P-1 email de la confirmación | **Reemplazada** por DD-130/D-7: la verificación y la confirmación van siempre al email de la ficha (si el DNI es nuevo, la ficha tiene el email escrito) |
| P-2 DNI existente con datos distintos | **Reemplazada** por DD-129: el nombre debe coincidir y la ficha nunca se modifica |
| P-3 campos | Opción A, ajustada: DNI, nombre, apellido y email siempre obligatorios; teléfono opcional |
| P-4 profesionales y horizonte | Opción A |
| P-5 límite y trampa | Opción A, ajustada: se quita la consulta de DNI y se suma la confirmación (10 por hora) |
| P-6 origen | **Reemplazada** por DD-130/DD-133 (`created_by` nulo + `pending_until`, etiquetas "Pendiente de confirmación" y "Online") |
| P-7 inactivo o superpuesto | **Reemplazada** por DD-129 (el mismo rechazo genérico que el nombre que no coincide) |
| P-8 ruta | Opción A: `/turnos` y `/turnos/confirmar` |
| P-9 autogestión | Opción A: no |
| P-10 tope por DNI | Opción A: sin tope |

## Decisiones Q-1 a Q-6: RESUELTAS (opción A, elegidas por el usuario)

- **DD-134 (Q-1)**: plazo de 60 minutos, configurable con `ONLINE_BOOKING_HOLD_MINUTES`.
- **DD-135 (Q-2)**: toda reserva online pasa por la confirmación por email, también con DNI nuevo.
- **DD-136 (Q-3)**: la recepción no confirma a mano un pendiente. Solo lo cancela; si el paciente llama, cancela el pendiente y agenda como siempre.
- **DD-137 (Q-4)**: confirmación por enlace con el token en el fragmento y un botón en `/turnos/confirmar`. Tiene pantallas propias para "Turno registrado exitosamente", "Turno confirmado" y "Enlace no válido".
  - El texto de "Turno registrado exitosamente" es idéntico para un DNI nuevo y uno existente, y solo muestra lo que eligió el paciente (profesional, día y hora) y el plazo.
  - El aspecto se revisa con `diseno-ui-odontologico` (C-1 a C-10). Los avisos usan los componentes `Notices` de C-14, y el diente solo aparece en la carga.
  - Las páginas públicas hablan de usted, con los textos que pidió el usuario.
- **DD-138 (Q-5)**: la ficha que creó una reserva que vence queda guardada, y la recepción la corrige o el administrador la borra. El riesgo del DNI ocupado queda en `10_preguntas_abiertas.md`.
- **DD-139 (Q-6)**: el change se parte.
  - C-15 trae la reserva pública, la confirmación y las etiquetas.
  - C-16 `online-booking-expiry` trae el vencimiento automático y el email de cancelación por falta de confirmación.

No quedan decisiones pendientes en C-15.

## Tamaño después de la división

| | C-15 | C-16 | C-11 (referencia) |
|---|---|---|---|
| Tasks | 54 | 18 | 54 |
| Specs (nuevas + deltas) | 14 | 5 | 9 |
| Migraciones | `0003` (3 columnas, 2 CHECK, 2 índices) | `0004` (valor nuevo de `notification_kind`) | 1 |
| Tareas de Celery nuevas | 1 (verificación) | 1 (vencimiento) | 3 |
| Pruebas de concurrencia | 3 (franja, recepción contra online, DNI) | 3 (confirmar contra vencer en los dos órdenes, dos pasadas) | 1 |

Con la división, C-15 queda del tamaño de C-11 y C-16 es chico. El riesgo de la división ya está aceptado: entre los dos, un pendiente vencido ocupa la franja hasta que la recepción lo cancela, así que no conviene una demo pública sin C-16.

## Risks / Trade-offs

- **[Se puede saber qué DNIs existen con el rechazo genérico (DD-129)]** → mensaje y código únicos, 5 reservas por hora por IP y ningún dato de la ficha. Rotar IPs lo saltea; se acepta con datos ficticios.
- **[DNI ajeno ocupado por una reserva falsa sin confirmar (Q-5)]** → la recepción ve el pendiente y la ficha nueva. Q-5 B lo cierra.
- **[Reservas falsas que retienen franjas]** → solo durante el plazo (60 minutos, y hasta que la recepción las cancele mientras no esté C-16), con el tope de 5 por hora por IP y el campo trampa.
- **[El token viaja en el mensaje de Redis]** → Redis es interno a Compose y sin puerto público. El mensaje se consume y se descarta, y el token vence con la reserva.
- **[Previsualizadores de email que abren enlaces]** → el enlace no tiene efectos: confirmar exige el `POST` del botón.
- **[Redis caído]** → sin límite de pedidos (falla abierta, con aviso) y sin email de verificación (el turno vence, y C-16 lo cancela).
- **[`created_by` nulo y `pending_until` cambian el contrato de la API]** → los tipos y tests del frontend se ajustan en el mismo grupo.
- **[Romper la regla dura 6]** → no se toca el constraint ni DD-16. Hay tests de integración de pendiente contra confirmado, online contra recepción y dos reservas.

## Migration Plan

1. Migración `0003`, aplicada por el servicio `migrate`. Rollback: `alembic downgrade 0002` funciona si no hay turnos online; si los hay, falla a propósito.
2. Agregar `ONLINE_BOOKING_HOLD_MINUTES` y `PUBLIC_APP_URL` a `.env.example`. Tienen valores por defecto, así que un `.env` existente sigue arrancando.
3. El vencimiento automático llega con C-16.

## Open Questions

- Ninguna.
