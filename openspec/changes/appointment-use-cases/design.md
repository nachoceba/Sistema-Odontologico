# Design: appointment-use-cases (C-08)

> **Gobernanza MEDIA.** Las decisiones P-1 a P-12 están **RESUELTAS**: la usuaria confirmó el 2026-11-03 la opción recomendada de cada una (P-3 = B, el resto = A; P-11 = un solo change por grupos; P-12 = las tres recomendaciones de borde). Se registran como DD-62 a DD-67 en `knowledge-base/09_decisiones_y_supuestos.md`. Las specs ya reflejan esas opciones.

## Context

Motivación en `proposal.md`. Estado real del código (verificado el 2026-11-03):

- **Dominio puro** (`app/domain/appointments/`): `validate_appointment` (motivos `INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF`, `OVERLAPS_EXISTING`, en ese orden), `compute_slots`, `validate_status_change` y `validate_reschedule_eligibility` (`TransitionRejection`: `CANCELLED_IS_FINAL`, `ATTENDANCE_ALREADY_RECORDED`, `INVALID_TARGET_STATUS`, `NOT_STARTED_YET`, `ALREADY_STARTED`), `rules.overlaps_scheduled` y `ranges_overlap`. `app/domain/patients/eligibility.check_patient_can_book` (`PATIENT_INACTIVE`). `app/core/timezone.py` (`to_local`, `to_utc`, `local_day_bounds`). Todas reciben `now` como dato (no leen el reloj).
- **Puertos y repositorios**: `AppointmentRepository` (add, get, change_status, reschedule, list_for_professional, list_for_patient), `WorkingHoursRepository`, `TimeOffRepository`, `PatientRepository.get`, `ClinicSettingsRepository.get` (slot, zona, anticipación), `ProfessionalRepository` (list, get_by_id), `UserAccountRepository`. Implementación en memoria (`app/infrastructure/in_memory/`) y PostgreSQL (`app/infrastructure/db/repositories/`); cada método SQL abre **su propia transacción** con `sessionmaker.begin()` (DD-36). El repositorio SQL de turnos ya traduce `23P01` (`ExclusionViolation`) a `SlotTakenError` y bloquea la fila (`FOR UPDATE`) al cambiar estado o reprogramar.
- **Batería de contrato** (`tests/contract/`) parametrizada por fábrica `in_memory` y `postgres` (esta con `-m integration`).
- **Esquema** (C-02): `appointments` con `ex_appointments_no_overlap` (solo `scheduled`, rango `[)`); `email_notifications` con `UNIQUE (appointment_id, kind, appointment_starts_at)`, enums `notification_kind` (`confirmation`, `reminder`) y `notification_status` (`pending`, `sent`, `failed`; **no hay estado "descartada"**); FKs `ON DELETE RESTRICT` (DD-39). Modelo `EmailNotificationModel` existe; **no hay repositorio de notificaciones**. **No hace falta migración.**
- **API** (C-03/C-04): `current_user`, `require_role`, `require_professional_access` (aplica `can_access_professional` al parámetro de ruta `professional_id`), fábricas sobreescribibles (`get_user_repository`), `STATUS_BY_CODE` con default 400, 422 sin eco (`handle_validation_error`), test de inventario de rutas (`test_route_inventory.py`), patrón de test de permisos por rol (`tests/unit/api/test_users_permissions.py`: tabla de endpoints × roles, snapshot "nada cambia", 401 antes que 403) y fixtures con cuentas en memoria (`PROFESSIONAL_A`, `PROFESSIONAL_B`).
- **Hallazgo 1**: al reprogramar, `validate_appointment` recibiría el propio turno entre los existentes y lo rechazaría como superpuesto: el caso de uso debe excluirlo (el repositorio ya lo hace, spec `appointment-repository`).
- **Hallazgo 2**: `minutes_of_day` ignora segundos, así que un inicio 10:00:30 pasaría la grilla y se guardaría 10:00:30–10:30:30 (P-12).
- **Hallazgo 3**: volver a reprogramar a un horario que ya tuvo una confirmación `sent` choca con el `UNIQUE` de notificaciones (P-2).
- La skill `revisor-escenarios-turnos` se aplicó a las specs borrador (resultado en "Revisión de escenarios" al final).

## Goals / Non-Goals

**Goals:**
- Casos de uso finos en `app/application/` que solo orquestan: cargan datos por puertos, llaman a las reglas puras y escriben por la unidad de trabajo.
- Un solo "cargador de contexto de agenda" (tramos, licencias, turnos del día, configuración) compartido por agendar, reprogramar y franjas, para que franja libre y agendar no diverjan.
- Atomicidad turno + notificaciones con una unidad de trabajo, probada en memoria y en PostgreSQL.
- Prueba real de concurrencia contra PostgreSQL.

**Non-Goals:**
- Envío de emails, Celery, Redis, plantillas, `reencolar_pendientes` (C-11); recordatorios y listado global por rango (C-12, P-10).
- Pantallas (C-10) y vistas de agenda (C-09).
- Alta, búsqueda y edición de pacientes (C-06); edición de horarios y licencias y listado de conflictos RN-HO-04 (C-07).
- Excepción de anticipación mínima para urgencias (P-8), sillones, sobreturnos (RN-TU-09, RN-TU-11), auditoría de quién canceló más allá de `cancel_reason`.
- Datos del paciente o profesional embebidos en la respuesta del turno (solo ids; C-09/C-10 pueden ampliarla).

## Decisiones pendientes (P-1 a P-12)

Cada pregunta en lenguaje simple, con opciones, la recomendada y por qué. Todas están resueltas con la opción recomendada (confirmada por la usuaria el 2026-11-03).

### P-1 — Emails: ¿qué deja anotado C-08 cuando se agenda o se reprograma? — RESUELTA (opción A, confirmada 2026-11-03)
Los emails de verdad llegan en C-11. La KB dice que el turno y el "aviso pendiente de enviar" se guardan juntos (`11_recordatorios_email.md`), pero CHANGES.md proponía un "puerto que no hace nada".
- **A (recomendada)**: C-08 ya anota en la base "hay que mandar una confirmación" (fila `pending`) junto con el turno, en el mismo guardado; si una de las dos cosas falla, no queda ninguna. Después llama a un "despachador" que por ahora no hace nada. C-11 solo tiene que enchufar el envío.
- B: C-08 no anota nada; deja solo el "enchufe" vacío. C-11 hace las filas y el guardado conjunto.
- C: ni filas ni enchufe; todo en C-11.
**Por qué A**: cierra el pendiente DD-36 con una prueba real contra PostgreSQL y hace exactamente lo que dice la KB; C-11 queda más chico (emails y Celery). Con B, C-11 tendría que volver a tocar los casos de uso de turnos. Costo: antes de C-11 se acumulan filas "pendientes" que nadie envía (datos ficticios; C-11 decide qué hacer con las viejas).

### P-2 — Al reprogramar o cancelar, ¿qué pasa con los avisos que todavía no salieron? — RESUELTA (opción A, confirmada 2026-11-03)
RN-NO-05 dice que se "descartan", pero la base no tiene un estado "descartado".
- **A (recomendada)**: se borran las filas `pending` de la fecha anterior (las ya enviadas o fallidas se guardan como historial). Si el turno vuelve a un horario que ya tuvo una confirmación enviada, no se crea otra (el paciente ya la recibió) y la reprogramación no falla.
- B: no se borran; quedan `pending` y C-11 las ignora porque la fecha no coincide con la del turno.
- C: agregar un estado `discarded` con una migración.
**Por qué A**: no hace falta migración, el historial real (lo enviado) no se pierde y C-11 no tiene que filtrar filas muertas una y otra vez. B deja basura que `reencolar_pendientes` volvería a tomar cada 10 minutos. C agrega una migración por algo que nadie va a mirar. Consecuencia aceptada de A: quien vuelve a su horario original no recibe una segunda confirmación.

### P-3 — ¿Un paciente puede tener dos turnos a la misma hora con profesionales distintos? (H-2) — RESUELTA (opción B, confirmada 2026-11-03)
Hoy la base y el repositorio lo aceptan; la KB lo deja abierto (`10_preguntas_abiertas.md`, SU-05).
- A: sí, se permite.
- **B (recomendada)**: no; se rechaza con "El paciente ya tiene otro turno en ese horario". Varios turnos el mismo día en horarios distintos siguen permitidos (RN-TU-08).
**Por qué B**: una persona no puede estar en dos sillones a la vez; casi siempre es un error de carga. Es una consulta más por pedido. Límite: lo controla la aplicación, no la base (dos recepcionistas a la vez, en el mismo segundo, podrían colarlo; ver Riesgos).

### P-4 — ¿Quién puede marcar un turno como "atendido" o "ausente"? — RESUELTA (opción A, confirmada 2026-11-03)
US-010 habla del odontólogo; la matriz de permisos confirmada (DD-48) da a recepción y administración permiso de modificar turnos.
- **A (recomendada)**: el odontólogo, solo sus turnos; recepción y administración, cualquier turno.
- B: solo el odontólogo, sus turnos.
- C: el odontólogo (sus turnos) y la administración.
**Por qué A**: sigue la matriz ya confirmada y cubre el caso real de un odontólogo que se olvida de marcar o un paciente que no vino y avisa recepción. Las reglas de tiempo (solo con el turno ya empezado) valen para todos.

### P-5 — ¿Se le pueden dar turnos a un profesional cuya ficha está desactivada? — RESUELTA (opción A, confirmada 2026-11-03)
Desactivar a un odontólogo no toca sus turnos (DD-59).
- **A (recomendada)**: no se le agendan turnos nuevos ni se le reprograman; sí se pueden ver, cancelar y marcar atención de los que ya tiene.
- B: se permite todo igual que con un profesional activo.
**Por qué A**: si se fue del consultorio no tiene sentido darle turnos nuevos; recepción igual puede cancelar los pendientes y avisar al paciente (DD-59 pide justamente eso).

### P-6 — Al reprogramar, ¿se puede cambiar de profesional? — RESUELTA (opción A, confirmada 2026-11-03)
- **A (recomendada)**: no; reprogramar solo cambia día y hora. Para cambiar de profesional se cancela y se agenda uno nuevo.
- B: sí, se puede elegir otro profesional al reprogramar.
**Por qué A**: es lo que describe el Flujo 3 (cambia `starts_at` y `ends_at`) y lo que ya hace el repositorio. B obliga a cambiar el repositorio y suma casos (otro horario, otras licencias, permisos). Con P-5 = A, un turno de un profesional dado de baja se resuelve cancelando y agendando otro.

### P-7 — El motivo de cancelación, ¿es obligatorio? — RESUELTA (opción A, confirmada 2026-11-03)
- **A (recomendada)**: sí, obligatorio, texto libre de 1 a 500 caracteres.
- B: opcional.
**Por qué A**: US-008 dice "cancelar un turno indicando un motivo" y no hay otra auditoría de cancelaciones.

### P-8 — Turnos de urgencia: ¿alguien puede saltarse las 6 horas de anticipación? — RESUELTA (opción A, confirmada 2026-11-03)
Pregunta abierta en `10_preguntas_abiertas.md` (RN-TU-12, DD-14).
- **A (recomendada)**: no en C-08; la regla se aplica a todos. Se puede bajar `min_notice_hours` en la configuración si el consultorio lo necesita.
- B: el administrador puede agendar sin respetar la anticipación.
**Por qué A**: B agrega un permiso especial y más casos de prueba sin que el consultorio lo haya pedido; queda como mejora posterior.

### P-9 — ¿C-08 incluye también las consultas (ver un turno, listar los de un profesional y ver los horarios libres de un día)? — RESUELTA (opción A, confirmada 2026-11-03)
CHANGES.md pone los horarios libres en C-09 (pantalla de agenda).
- **A (recomendada)**: sí, las tres consultas van en C-08; C-09 queda solo con las pantallas y las usa.
- B: ver y listar en C-08; horarios libres en C-09.
- C: solo ver un turno en C-08 (lo mínimo para el test de DD-53).
**Por qué A**: agendar y "mostrar libres" usan exactamente los mismos datos y reglas; hacerlo en un solo lugar evita que la pantalla muestre libre algo que después se rechaza. Además el test obligatorio "un odontólogo no ve turnos ajenos" (DD-53) necesita el listado real. Efecto en el roadmap: C-09 pasa a depender de C-08 (el camino crítico no se alarga, ver Riesgos) y CHANGES.md se actualiza.

### P-10 — El listado de turnos "de todos los profesionales" por rango, ¿va en C-08? — RESUELTA (opción A, confirmada 2026-11-03)
CHANGES.md lo pone en C-08, pero solo lo usan los recordatorios.
- **A (recomendada)**: pasa a C-12, que es quien lo usa.
- B: se hace en C-08 aunque nadie lo use todavía.
**Por qué A**: hacerlo sin su usuario obliga a adivinar qué necesita (filtros, estados); C-12 lo define con su caso de uso.

### P-11 — ¿C-08 se hace de una vez o se parte en dos? — RESUELTA (opción A, confirmada 2026-11-03)
Tamaño: 46 tareas en 11 grupos (similar a C-04, que tuvo 45 y se hizo de una vez), sin frontend.
- **A (recomendada)**: un solo change ejecutado por grupos, con un punto de corte seguro: si se hace largo, se puede archivar después del grupo 7 (casos de uso, API, permisos y concurrencia, con el despachador vacío y sin filas de notificación) y dejar los grupos 8 y 9 (unidad de trabajo y notificaciones) como C-08b con `/opsx:update`.
- B: partir ya en C-08a (casos de uso, API, permisos, concurrencia) y C-08b (unidad de trabajo y notificaciones).
**Por qué A**: las specs ya están completas y coherentes; partir ahora duplica revisión. El punto de corte deja algo usable (C-10 puede empezar) sin romper nada.

### P-12 — Tres bordes de horario — RESUELTA (opción a, b y c recomendadas, confirmada 2026-11-03)
- (a) Reprogramar al mismo horario que ya tiene: **recomendado** rechazarlo con "El turno ya está en ese horario" (alternativa: aceptarlo sin hacer nada). Evita crear un aviso duplicado.
- (b) Un inicio con segundos (10:00:30): **recomendado** rechazarlo como "fuera de la grilla" (alternativa: redondear). Igual que DD-29 para horarios.
- (c) Si el consultorio cambió la duración del turno (por ejemplo de 30 a 20 minutos) y se reprograma un turno viejo: **recomendado** que tome la duración vigente (RN-TU-02: la duración es siempre la de la configuración). Alternativa: conservar la duración original.

## Decisions

Decisiones técnicas (no de dominio). Si una respuesta P-n las afecta, se indica.

### D-1 — Capas
- `app/domain/appointments/`:
  - `errors.py`: además de `SlotTakenError` y `AppointmentNotFoundError`, un error `DomainError` por código nuevo: `PatientNotFoundError`, `ProfessionalNotFoundError`, `PatientInactiveError`, `ProfessionalInactiveError` (P-5), `PatientDoubleBookedError` (P-3), `RescheduleSameTimeError` (P-12a), `AppointmentRuleError` por cada `RejectionReason` salvo la superposición (`InsufficientNoticeError`, `OffGridError`, `OutsideWorkingHoursError`, `ProfessionalTimeOffError`) y uno por cada `TransitionRejection` usada (`CancelledIsFinalError`, `AttendanceAlreadyRecordedError`, `AlreadyStartedError`, `NotStartedYetError`). `DomainError.code` es `ClassVar`, por eso una clase por código. Funciones puras `error_for_rejection(RejectionReason)` y `error_for_transition(TransitionRejection)`; `OVERLAPS_EXISTING` → `SlotTakenError` (mismo código que la carrera, US-007).
  - `rules.py`: `has_sub_minute_precision(instant)` (P-12b) y `patient_has_overlap(patient_id, starts_at, ends_at, existing, *, exclude_id)` (P-3) reusando `overlaps_scheduled`/`ranges_overlap`.
  - `ports.py`: `AgendaUnitOfWork` y `NotificationRepository` (D-2, D-6), `NotificationDispatcher` (D-7). `types.py`: `Notification`, `NotificationKind`, `NotificationStatus` (mismos valores que los enums de la base, con test de paridad como `test_role_parity.py`).
- `app/application/appointments.py`: `book_appointment`, `cancel_appointment`, `reschedule_appointment`, `record_attendance`, `get_appointment`, `list_appointments`, `day_slots`. Reciben un objeto `AgendaDeps` (repositorios de lectura, fábrica de unidad de trabajo, despachador, reloj) y el `Principal`. Sin FastAPI.
- `app/api/appointments.py`: routers `/appointments` y `/professionals/{professional_id}/slots`.
**Alternativa**: lógica en el router. Descartada (igual que C-04).

### D-2 — Unidad de trabajo
Puerto `AgendaUnitOfWork` (context manager) que expone `appointments: AppointmentRepository` y `notifications: NotificationRepository` sobre **una misma transacción**: `__exit__` sin excepción confirma; con excepción revierte. Las lecturas de contexto (pacientes, profesionales, tramos, licencias, configuración) usan los repositorios de siempre, fuera de la unidad: la barrera contra la superposición es la base, no la consistencia de lectura.
- **PostgreSQL**: `SqlAlchemyAgendaUnitOfWork(session_factory)` abre `session_factory.begin()` y entrega repositorios ligados a esa sesión. Para no duplicar código, `SqlAlchemyAppointmentRepository` pasa a obtener la sesión de un "alcance" interno: el de siempre (`sessionmaker.begin()` por operación, DD-36) o el de la unidad (sesión compartida, solo `flush`). Su contrato y la batería no cambian.
- **Memoria**: `InMemoryAgendaUnitOfWork` copia el estado de los dos repositorios al entrar y lo restaura si sale con excepción (sirve para el escenario "falla la notificación → no queda el turno").
**Alternativas**: (a) un método de repositorio `add_with_confirmation` (como el alta cuenta+ficha de C-04): descartada porque cancelar y reprogramar también tocan notificaciones y cada combinación sería un método; (b) unidad de trabajo genérica con todos los repositorios: descartada por más superficie sin necesidad.
**Si P-1 = B o C**: la unidad expone solo `appointments` y los grupos 8 y 9 de tasks se reducen.

### D-3 — Orden de los casos de uso
- **Agendar**: paciente (`get`) → profesional (`get_by_id`) → activo/activo → precisión → contexto (tramos, licencias, turnos del profesional en el día local ±1 día, configuración) → `validate_appointment` → turnos del paciente en el rango → `uow.appointments.add` + `uow.notifications.add_pending_confirmation` → commit → despachador.
- **Reprogramar**: `get` → `validate_reschedule_eligibility` → mismo inicio → paciente y profesional activos → contexto **excluyendo el propio turno** de `existing_appointments` y de la regla del paciente (Hallazgo 1) → `validate_appointment` → en la unidad: `delete_pending(appointment_id, starts_at=anterior)`, `reschedule`, `add_pending_confirmation(nuevo)` → commit → despachador. `ends_at = starts_at + slot_minutes vigente` (P-12c).
- **Cancelar**: `get` → `validate_status_change(…, CANCELLED)` → en la unidad: `change_status(cancelled, motivo)` + `delete_pending(appointment_id)`.
- **Marcar atención**: `get` → alcance (`can_access_professional` con el profesional del turno) → `validate_status_change` → `change_status` (sin notificaciones; puede usar el repositorio directo).
- Lecturas: `get`/`list_for_professional` con alcance; `day_slots` con `local_day_bounds` y el mismo cargador de contexto que agendar.
- El rango de turnos que se carga para validar cubre el día local completo más los bordes (DD-19: un turno que cruza la medianoche).

### D-4 — Reloj inyectable
Dependencia `get_clock() -> Callable[[], datetime]` que devuelve `datetime.now(UTC)`; los tests la sobreescriben con un reloj fijo. Los casos de uso nunca llaman a `datetime.now`.

### D-5 — Contrato HTTP
- `POST /appointments` `{patient_id, professional_id, starts_at}` → 201. `POST /{id}/cancel` `{reason}`; `POST /{id}/reschedule` `{starts_at}`; `POST /{id}/attendance` `{status: "completed"|"no_show"}` → 200. `GET /appointments?professional_id&from&to` (los tres obligatorios; `to - from <= 31 días`, límite técnico contra consultas enormes); `GET /professionals/{professional_id}/slots?date=AAAA-MM-DD`.
- Instantes con Pydantic `AwareDatetime` (rechaza sin zona con 422); salida en UTC. `reason` recortado, 1..500 (P-7). Ids como texto: los mal formados se tratan como "no encontrado" (DD-37) salvo el alcance del odontólogo (403, DD-53).
- Roles: `require_role(ADMIN, RECEPTIONIST)` en agendar/cancelar/reprogramar; `current_user` + alcance en lecturas y atención (P-4). El alcance cuando el profesional sale del turno se chequea en el caso de uso (`ForbiddenError`) **antes** de cualquier otra regla, para no revelar el estado de un turno ajeno; un id de turno inexistente da 404 a todos.
- Respuesta `AppointmentOut`: id, patient_id, professional_id, starts_at, ends_at, status, cancel_reason, created_by. `SlotOut`: starts_at, ends_at, status (`FREE`/`BUSY`/`OUTSIDE_HOURS`).
**Consultado con Context7**: `/websites/fastapi_tiangolo` ya consultado en C-03/C-04 para `HTTPBearer` y el 422; no se consultó de nuevo.

### D-6 — Registro de notificaciones (P-1 = A, P-2 = A)
Puerto `NotificationRepository`: `add_pending_confirmation(appointment_id, starts_at) -> Notification | None` (devuelve `None` si ya existía una con ese turno, tipo y horario), `delete_pending(appointment_id, *, starts_at: datetime | None = None) -> int`, `list_for_appointment(appointment_id) -> list[Notification]`. En PostgreSQL, el "no duplicar" se hace con `INSERT … ON CONFLICT DO NOTHING` sobre `uq_email_notifications_appointment_kind_starts_at`, o con un `SAVEPOINT` (`Session.begin_nested()`) que atrapa la `IntegrityError` sin abortar la transacción externa.
**Consultado con Context7**: `/websites/sqlalchemy_en_20_orm` (2026-11-03): `sessionmaker.begin()` confirma o revierte al salir y cierra la sesión (base de D-2); `Session.begin_nested()` permite atrapar una `IntegrityError` en PostgreSQL sin abortar la transacción externa (alternativa para D-6). Influyó en elegir una sesión compartida por la unidad y en no dejar que el `UNIQUE` aborte una reprogramación.

### D-7 — Despachador posterior al commit
Puerto `NotificationDispatcher.dispatch(notifications: Sequence[Notification]) -> None`; `NoOpNotificationDispatcher` es el de producción en C-08 (C-11 lo reemplaza). El caso de uso lo llama **después** de salir de la unidad sin error, dentro de `try/except Exception` que registra en el log solo ids (RN-NO-04, RN-PR-01). Si la transacción se revirtió, no se llama.

### D-8 — Tabla de errores (`STATUS_BY_CODE`)
404: `PATIENT_NOT_FOUND`, `PROFESSIONAL_NOT_FOUND` (más los existentes). 409: `PATIENT_DOUBLE_BOOKED`, `PATIENT_INACTIVE`, `PROFESSIONAL_INACTIVE`, `CANCELLED_IS_FINAL`, `ATTENDANCE_ALREADY_RECORDED`, `ALREADY_STARTED`, `NOT_STARTED_YET` (más `SLOT_TAKEN`). 400 (por defecto, pero listados explícitamente en un test): `INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF`, `RESCHEDULE_SAME_TIME`. Criterio: 409 = choca con el estado actual de la agenda o de un registro; 400 = el horario pedido no respeta las reglas fijas. Mensajes en castellano pensados para C-10 (por ejemplo `SLOT_TAKEN`: "Ese horario acaba de ocuparse. Elegí otro.").

### D-9 — Test de concurrencia contra PostgreSQL
`tests/integration/db/test_appointment_concurrency.py` (`-m integration`): sesión 1 abre transacción e inserta (flush) el turno de 10:00 sin confirmar; en un hilo, la sesión 2 inserta el mismo horario y queda bloqueada por el constraint; se confirma la sesión 1; la sesión 2 recibe la violación de exclusión, que el repositorio traduce a `SlotTakenError`. `SET lock_timeout` y `join(timeout)` evitan que un fallo cuelgue la suite. Variante a nivel de caso de uso: dos `book_appointment` con unidades de trabajo distintas y un "freno" inyectado entre validar y escribir, para mostrar que las dos validaciones pasan y gana la base. Más el caso reprogramar contra agendar y el de profesionales distintos.

### D-10 — Tests de API sin base
Mismo patrón que C-03/C-04: fábricas sobreescribibles (`get_agenda_deps` o una por repositorio) con repositorios en memoria cargados con los dos profesionales y pacientes de los fixtures; reloj fijo. `tests/unit/api/test_appointments_permissions.py` con la tabla de los siete endpoints × tres roles + sin token + odontólogo sin ficha, y la comprobación "nada cambió". El test de punta a punta de DD-53 corre también en integración contra PostgreSQL con el seed.

### D-11 — Sin variables de entorno, migraciones ni dependencias nuevas
Todo usa `clinic_settings` y la configuración existente. No se toca `.env` ni `.env.example`.

### D-12 — Hallazgos al implementar (2026-11-03)
- **Deadlock en la carrera**: dos inserciones simultáneas del mismo horario no siempre terminan en violación de exclusión (`23P01`); a veces cada una espera a la otra al verificar el constraint y PostgreSQL aborta una por deadlock (`40P01`). Se vio en el test de concurrencia (2 de 3 corridas). `SqlAlchemyAppointmentRepository` traduce también `DeadlockDetected` a `SlotTakenError` (otra escritura se quedó con el horario). El test de concurrencia se repitió 20 veces sin fallos.
- **Mensaje de `SLOT_TAKEN`**: pasó a "Ese horario acaba de ocuparse. Elegí otro." (D-8); los atributos del error se conservan. Se actualizó el test de C-05d que fijaba el texto anterior.
- **Escenario "fuera de horario"**: con `slot_minutes = 30` y tramo desde las 09:00, las 12:45 no están en la grilla (`OFF_GRID` primero); el escenario de la spec ahora usa `slot_minutes = 45` (12:45 en grilla, termina 13:30).
- **Despachador**: un fallo se registra con ids de turno y el nombre de la clase del error, sin traza ni mensaje (podría traer datos del paciente).

## Risks / Trade-offs

- [La regla "un paciente, un turno a la vez" (P-3) no la garantiza la base] → dos pedidos simultáneos para el mismo paciente con profesionales distintos podrían pasar los dos. Se acepta (raro, datos ficticios); una exclusión por paciente en la base sería una migración y otro constraint a mantener. Se documenta.
- [El cargador de contexto lee fuera de la transacción] → un cambio de horario simultáneo (C-07) podría colar un turno fuera del horario nuevo. Se acepta: RN-HO-04 ya trata esos turnos como conflictos que resuelve recepción.
- [Filas `pending` sin envío hasta C-11 (P-1 = A)] → al activar C-11, `reencolar_pendientes` enviaría confirmaciones de turnos viejos a Mailpit. C-11 decide si las limpia; se anota en CHANGES.md.
- [Refactor del repositorio SQL de turnos para usar sesión compartida] → riesgo de romper la batería de contrato. Mitigación: safety net de la batería en memoria y PostgreSQL antes y después; el contrato no cambia.
- [Test de concurrencia inestable] → hilos con timeout y `lock_timeout`; se repite 20 veces en local antes de dar por bueno.
- [P-9 = A cambia el roadmap] → C-09 pasa a depender de C-08; camino C-03→C-08→C-09→C-10→C-13 tiene la misma longitud que el crítico actual, no lo alarga, pero reduce el paralelismo C-08 ∥ C-09.
- [Tamaño del change (~50 tareas)] → ejecución por grupos con punto de corte tras el grupo 7 (P-11).

## Migration Plan

Sin migraciones ni cambios de configuración. Despliegue: reconstruir la imagen del backend. Reversión: quitar el router de turnos de `app/api/router.py`; las filas creadas son datos ficticios.

## Open Questions

Ninguna diferible: P-1 a P-12 quedaron resueltas el 2026-11-03 (ver arriba).

## Revisión de escenarios (skill `revisor-escenarios-turnos`, 2026-11-03)

### Resumen
95 escenarios revisados (81 nuevos), 16 hallazgos (3 ambigüedades, 4 bordes faltantes, 1 regla solapada, 2 preguntas abiertas, 4 sin respaldo, 2 contrato incompleto, 0 contradicciones). Todos los hallazgos ya quedaron cubiertos en las specs con la opción sugerida o como pregunta P-n.

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (confirmada) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Contrato incompleto | Reprogramar solapando su horario anterior | `validate_appointment` contaría el propio turno como superpuesto | RN-TU-06 (`05_reglas_de_negocio.md`); spec `appointment-repository` ("no choca consigo mismo") | Excluir el propio turno de los existentes (técnico, D-3) |
| 2 | Borde faltante | Inicio con segundos | La grilla ignora segundos: 10:00:30 pasaría | Sin respaldo en la KB (análogo a DD-29) | Rechazar con `OFF_GRID` (P-12b) |
| 3 | Regla solapada | Reprogramar sin anticipación | RN-TU-06 cita RN-TU-01 a RN-TU-04, pero RN-TU-04 quedó cubierta por RN-TU-12 | RN-TU-06, RN-TU-12, DD-14 | Aplicar la anticipación mínima al reprogramar (el escenario cita RN-TU-12) |
| 4 | Pregunta abierta | Paciente con dos turnos a la misma hora | H-2 sin responder | `10_preguntas_abiertas.md` (SU-05) | P-3, recomendada rechazar |
| 5 | Pregunta abierta | Agendar con menos de 6 h | Urgencias sin definir | `10_preguntas_abiertas.md` (RN-TU-12, DD-14) | P-8, recomendada no en C-08 |
| 6 | Sin respaldo | Agendar con profesional inactivo | La KB no dice si una ficha inactiva recibe turnos | DD-59 y nota de C-04 en `CHANGES.md` (solo dicen que los turnos quedan intactos) | P-5 |
| 7 | Ambigüedad | Marcar atención por recepción | US-010 habla del odontólogo; la matriz da U a recepción | US-010 (`06_funcionalidades.md`), matriz de `03_actores_y_roles.md`, DD-48 | P-4 |
| 8 | Sin respaldo | Reprogramar con otro profesional | Flujo 3 solo cambia fechas | `07_flujos_principales.md` Flujo 3 | P-6, recomendada no |
| 9 | Sin respaldo | Motivo de cancelación vacío | US-008 pide motivo; largo y obligatoriedad sin definir | US-008 | P-7 |
| 10 | Ambigüedad | Descartar pendientes al reprogramar o cancelar | RN-NO-05 "se descartan" y la base no tiene estado de descarte | RN-NO-05; enum `notification_status` (`04_modelo_de_datos.md`) | P-2, recomendada borrar las `pending` |
| 11 | Borde faltante | Volver a un horario ya confirmado | El `UNIQUE` de notificaciones haría fallar la reprogramación | RN-NO-03; `email_notifications` UNIQUE | No duplicar ni fallar (P-2) |
| 12 | Contrato incompleto | Confirmación pendiente al agendar | CHANGES.md pide un puerto vacío; `11_recordatorios_email.md` pide fila `pending` en la misma transacción | DD-36, `11_recordatorios_email.md` §Envío asincrónico, entrada C-08 de `CHANGES.md` | P-1 |
| 13 | Borde faltante | Reprogramar al mismo horario | Crearía una confirmación duplicada | Sin respaldo en la KB | Rechazar (P-12a) |
| 14 | Ambigüedad | Reprogramar tras cambiar `slot_minutes` | ¿Duración original o vigente? | RN-TU-02 ("siempre `slot_minutes`") | Vigente (P-12c) |
| 15 | Sin respaldo | Franjas en C-08 | CHANGES.md pone las franjas en C-09 | Entradas C-08 y C-09 de `CHANGES.md`; Flujo 2 paso 1 | P-9 |
| 16 | Borde faltante | Turno que cruza la medianoche al validar | El contexto debe incluir turnos del día anterior que terminan en el día pedido | DD-19, DD-31 | Cargar el día local con bordes (técnico, D-3); escenario de listado que cruza el rango |

### Escenarios sin hallazgos
Agendar en slot libre, slot ocupado, fuera de horario, licencia, fuera de grilla, turnos pegados, slot liberado por cancelación, límite exacto de anticipación, cancelar (todos), marcar atención (todos, DD-21 a DD-23), concurrencia (todos), permisos por rol (matriz DD-48 y DD-53), error-model.

Hay escenarios esperados, de error de negocio y de borde en cada requirement. No se inventaron estados ni campos: todo existe en `04_modelo_de_datos.md` (los códigos de error nuevos son de la API, no de la base).

### Decisiones que necesitan a la usuaria
Ninguna: las doce preguntas P-1 a P-12 fueron confirmadas por la usuaria el 2026-11-03 con la opción recomendada.
