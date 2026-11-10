# Design: C-17 `appointment-treatments`

La motivación y el alcance están en `proposal.md`. El comportamiento exigible está en las specs del change:

- Nuevas: `treatment-management`, `treatment-api` y `frontend-treatment-management`.
- Deltas: `database-schema`, `appointment-use-cases`, `appointment-api`, `public-booking`, `public-booking-api`, `access-control`, `email-templates`, `seed-data`, `frontend-appointment-management`, `frontend-agenda` y `frontend-public-booking`.

> **Estado**: P-1 a P-10 están resueltas con la opción A (DD-141 a DD-150) y el seed de ejemplo con DD-151. No quedan decisiones pendientes.

## Context

Esto es lo que ya existe y se reutiliza, observado en el código:

- **Agendar en la recepción** (`app/application/appointments.py`): `book_appointment` busca el paciente, el profesional, chequea que estén activos (`_require_active`), valida el horario con `validated_end` y escribe el turno y su confirmación en `SqlAlchemyAgendaUnitOfWork`, en una transacción. Reprogramar usa `validated_end(..., exclude_id=...)` y no recibe más datos que el inicio.
- **Reserva pública** (`app/application/public_booking.py`): `_require_offered` define qué profesional se ofrece (activo y con horario), `book_online` valida el horario antes de abrir la transacción y busca o crea al paciente adentro. `confirm_online_booking` confirma por hash con `FOR UPDATE`. Las respuestas son `OnlineBooking` y `OnlineConfirmation`.
- **Turno en el dominio** (`app/domain/appointments/types.py`): `NewAppointment` y `Appointment` sin tratamiento. `AppointmentView` suma los nombres del paciente con una lectura por paciente distinto.
- **Emails**: `render_email` (confirmación, recordatorio y vencimiento) recibe `EmailData`; `render_verification_email` recibe `VerificationEmailData`. Los arman `deliver_notification` y `send_verification` con los datos vigentes al enviar (DD-73). Hoy la KB y la spec del aviso de vencimiento dicen que no llevan tratamiento.
- **Normalización de nombres**: `same_person_name` en `app/domain/patients/rules.py` ya compara sin mayúsculas, tildes ni espacios repetidos.
- **Permisos**: `require_role` en la ruta y `can_access_professional` en el caso de uso; `test_route_inventory.py` (`PUBLIC_ROUTES`) y `test_permission_matrix.py` (`MATRIX`) obligan a declarar cada ruta.
- **Límite de pedidos público**: `rate_limited("read", 60, 60)` ya cubre profesionales y franjas.
- **Seed**: `scripts/seed.py` carga por nombre o documento y solo lo que falta; los tramos se cargan solo si el profesional no tiene ninguno.
- **Frontend**: `BookingPanel` (paciente y "Agendar turno"), `AppointmentDetail`, `DayColumn` (línea del turno con etiquetas), `PublicBookingPage` (profesional → día → franja → datos), `ProfessionalsPage` (ficha, horario, licencias) y `RequireRole` para `/usuarios`.
- **Última migración**: `0004_booking_expired_kind`. Última decisión registrada: DD-140.

## Goals / Non-Goals

**Goals:**
- El tratamiento es un dato más del turno: no toca la grilla, las franjas, `validate_appointment`, `compute_slots` ni `ex_appointments_no_overlap` (regla dura 6 intacta y probada de nuevo con tratamientos).
- Una sola regla pura decide si un tratamiento sirve para un turno nuevo, y la usan la recepción y la reserva pública.
- Ningún dato nuevo de pacientes en la API pública; el endpoint nuevo devuelve solo id y nombre de tratamientos.
- Ninguna dependencia ni variable de entorno nueva.

**Non-Goals:**
- Duración variable por tratamiento (DD-03 y RN-TU-10 siguen). Queda como mejora futura: con este catálogo armado, sumar `duration_slots` al tratamiento y que la validación pida N franjas seguidas sería el siguiente paso, y es un change aparte porque toca `compute_slots` y la regla de superposición.
- Precios, presupuestos, historia clínica, odontograma.
- Cambiar el tratamiento de un turno ya creado (DD-144).
- Que el paciente elija el tratamiento sin elegir antes el profesional.

## Decisions

### D-1 — Dominio nuevo `app/domain/treatments/`

- `types.py`: `Treatment(id, name, active)` y `NewTreatment(name)`.
- `rules.py`:
  - `clean_treatment_name(raw) -> str` (recorta, un solo espacio, de 1 a 80 caracteres; si no, `InvalidTreatmentNameError`).
  - `treatment_name_key(name) -> str`: la misma normalización que `same_person_name` (NFKD, sin diacríticos, mayúsculas, espacios simples). Para no duplicarla, la función de comparación de pacientes y esta usan un helper común `comparable_text` que se mueve a `app/domain/text.py` sin cambiar el comportamiento de `same_person_name` (sus tests siguen igual).
  - `check_treatment_for_booking(treatment: Treatment | None, offered_ids: frozenset[str]) -> TreatmentCheck`: devuelve aceptado o el motivo `NOT_FOUND`, `INACTIVE` o `NOT_OFFERED`. Es pura y la llaman la recepción y la reserva pública.
- `ports.py`: `TreatmentRepository` con `list_all`, `get`, `add`, `update`, `list_for_professional`, `offered_ids(professional_id)` (asignados y activos), `list_offered(professional_id)` y `replace_for_professional(professional_id, ids)`.
- `errors.py`: `TreatmentNotFoundError` (404), `TreatmentNotAvailableError` (409), `TreatmentNameTakenError` (409), con código estable como el resto.

Sin FastAPI, SQLAlchemy, Celery ni Redis (regla dura 2; `test_architecture.py` lo sigue chequeando).

### D-2 — Esquema: `name_key` en lugar de índice con `unaccent`

Migración `0005_treatments`:

- `treatments(id, name, name_key UNIQUE, active, created_at)` con CHECK de largo.
- `professional_treatments(professional_id, treatment_id)` con PK compuesta e índice en `treatment_id` (la primera columna de la PK cubre `professional_id`).
- `appointments.treatment_id` nulo, FK `RESTRICT` e índice `ix_appointments_treatment_id`.

Alternativa descartada: índice único sobre `unaccent(lower(name))`. `unaccent` es una extensión más y no es `IMMUTABLE`, así que hace falta una función envoltorio. Guardar `name_key` calculado por el dominio es más simple, se prueba con pytest y deja la regla en un solo lugar. El repositorio traduce la violación del único a `TreatmentNameTakenError`, como hace `DocumentTakenError` con el documento.

La reversión revisa `SELECT 1 FROM appointments WHERE treatment_id IS NOT NULL` y falla con un mensaje claro si hay alguno, igual que `0003` con los turnos online.

### D-3 — Obligatorio en la aplicación, nulo en la base

`treatment_id` queda nulo en la base porque los turnos anteriores no tienen tratamiento (DD-148). Lo obligatorio para turnos nuevos lo garantizan los esquemas de la API (`treatment_id` requerido) y los casos de uso (`treatment_id: str`, no opcional). Alternativa descartada: un CHECK atado a `created_at` posterior a la migración; ensucia el esquema y complica los tests de integración con fechas.

### D-4 — Nombre vigente, sin copia en el turno (DD-150)

El turno guarda solo `treatment_id`. El nombre que se muestra en la agenda, el detalle, las pantallas públicas y los emails es el vigente al leer o al enviar, igual que el nombre del paciente y del profesional (DD-73, DD-79). Como un tratamiento nunca se borra (FK `RESTRICT`, solo se desactiva), el turno siempre encuentra su nombre. Alternativa descartada: copiar `treatment_name` en el turno; protege el historial de un cambio de nombre, pero agrega una columna, una regla de sincronización y dos fuentes del mismo dato.

### D-5 — Orden de chequeos y dónde se valida

- **Recepción** (`book_appointment`): paciente existe → profesional existe → los dos activos → **tratamiento** (`check_treatment_for_booking` con `treatments.get` y `treatments.offered_ids`) → `validated_end` → transacción. Inexistente da `TREATMENT_NOT_FOUND`; inactivo o no ofrecido, `TREATMENT_NOT_AVAILABLE`.
- **Público** (`book_online`): `_require_offered` → **tratamiento** (los tres motivos dan `TREATMENT_NOT_AVAILABLE`, sin distinguir) → `_validated_online_end` → transacción con la búsqueda del documento. El rechazo del tratamiento no depende del paciente, así que no cambia lo que DD-129 cuida.
- **Reprogramar y confirmar**: no validan el tratamiento. Desactivar o quitar un tratamiento no toca turnos ya creados, incluidos los pendientes.
- `_require_offered` y `list_public_professionals` suman "al menos un tratamiento activo asignado": así el endpoint de franjas y el de tratamientos públicos responden igual (`PROFESSIONAL_NOT_FOUND`) para un profesional que no se puede reservar.

`AgendaDeps` y `PublicBookingDeps` (a través de `agenda`) suman `treatments: TreatmentRepository`. El chequeo se hace con lecturas fuera de la transacción, igual que `validated_end` (ver Riesgos).

### D-6 — Casos de uso del catálogo (`app/application/treatments.py`)

`list_treatments`, `create_treatment`, `update_treatment` (nombre, activo o los dos; un nombre igual con otra mayúscula sobre el mismo tratamiento se acepta), `list_professional_treatments` (con `_require_access` del odontólogo) y `replace_professional_treatments` (verifica que el profesional exista y que cada id exista; quita repetidos; reemplaza en una transacción). El rol admin se exige en la ruta con `require_role`, como en profesionales.

### D-7 — API

- `app/api/treatments.py`: router `/treatments` (GET, POST 201, PATCH) con esquemas `extra="forbid"`.
- `app/api/professionals.py`: `GET` y `PUT /{professional_id}/treatments`. `PUT` recibe `{treatment_ids: list[EntityId]}` con `max_length=100`.
- `app/api/appointments.py`: `BookRequest.treatment_id: EntityId` requerido; `AppointmentOut.treatment_id: str | None`; `AppointmentViewOut.treatment_name: str | None`. `AppointmentView` suma `treatment_name`, resuelto con una lectura por tratamiento distinto, como los pacientes.
- `app/api/public.py`: `GET /professionals/{professional_id}/treatments` con `_read_limit` y salida `PublicTreatmentOut(id, name)`; `BookingRequest.treatment_id`; `BookingOut` y `ConfirmationOut` suman `treatment_name`.
- `STATUS_BY_CODE`: `TREATMENT_NOT_FOUND` 404, `TREATMENT_NOT_AVAILABLE` 409 y `TREATMENT_NAME_TAKEN` 409.
- Matriz: las cinco rutas internas con sus roles (lecturas: los tres; escrituras: admin) y la ruta pública en `PUBLIC_ROUTES` y en `MATRIX` como `None`.

### D-8 — Emails

`EmailData` y `VerificationEmailData` suman `treatment_name: str | None = None`. Las plantillas agregan `Tratamiento: <nombre>` justo después de `Profesional:` solo si hay nombre. `deliver_notification` y `send_verification` leen el tratamiento vigente por id con un `TreatmentRepository` en sus dependencias (`NotificationDeps`, `VerificationDeps`) y nunca fallan por un tratamiento ausente: sin tratamiento, la línea no va. No cambian el registro, la idempotencia ni los reintentos.

### D-9 — Frontend

- `api/treatments.ts`: tipos `Treatment {id, name, active}` y funciones para las cinco rutas internas; `api/publicBooking.ts` suma `listPublicTreatments` (siempre `{ auth: false }`).
- `Appointment` suma `treatment_id: string | null` y `treatment_name: string | null` (sin `any`).
- `BookingPanel`: estado `treatment` y lista de activos ofrecidos del profesional; el botón exige paciente y tratamiento.
- `AppointmentDetail` y `RescheduleDialog`: fila "Tratamiento".
- `DayColumn`: ` · <tratamiento>` dentro de `appointment-text`, con `text-overflow: ellipsis` en la clase nueva `appointment-treatment` y el nombre completo en el texto accesible.
- `pages/TreatmentsPage.tsx` en `/tratamientos` dentro de `RequireRole roles={['admin']}`; enlace en `AppNav` solo para admin; diálogo de confirmación con `ui/Dialog`.
- `professionals/TreatmentsPanel.tsx` en la ficha: casillas para admin, lista para los demás.
- `PublicBookingPage`: paso nuevo entre profesional y día; `RegisteredNotice` y `ConfirmBookingPage` con la fila "Tratamiento".
- Revisión con `diseno-ui-odontologico` (C-1 a C-6, C-8, C-9) a 375, 768 y 1280 px con el navegador integrado en `localhost`.

### D-10 — Texto nuevo de la regla dura 4 (`CLAUDE.md` y `AGENTS.md`)

> 4. Todo endpoint exige JWT y chequeo de rol (`require_role`), salvo el login, el chequeo de salud público (`GET /api/v1/health`, que solo responde `{"status": "ok"}` sin datos) y los cinco endpoints de turnos online bajo `/api/v1/public/` (C-15 y C-17: profesionales, tratamientos de un profesional, franjas, reservar y confirmar), que no usan sesión pero llevan límite de pedidos por IP, validación estricta y campo trampa en la reserva, nunca devuelven datos de pacientes y nunca modifican una ficha existente; cada endpoint protegido lleva su test de permisos por rol y cada endpoint público, su test de acceso sin token y de límite de pedidos.

### D-11 — Textos propuestos para la KB

- **01**: el alcance v1.0 suma "Tratamiento del turno elegido de un catálogo, por la recepción y por el paciente online (C-17)". "Turnos de duración variable por tipo de tratamiento" sigue fuera de alcance.
- **03**: fila nueva de la matriz "Catálogo de tratamientos y asignación por profesional: Administrador CRU (sin borrar), Recepción R, Odontólogo R (propio en la asignación)". Rutas públicas: suma `GET /professionals/{id}/treatments`.
- **04**: tablas `treatments` y `professional_treatments`, columna `appointments.treatment_id`, ERD y seed (5 tratamientos de ejemplo, DD-151).
- **05**: RN-TU-10 pasa a "Hay un catálogo de tratamientos, pero no define duración: todo turno dura `slot_minutes`. Un tratamiento más largo se agenda con turnos consecutivos (DD-03). La duración por tratamiento queda para una etapa posterior." Nuevas: **RN-TU-16** "Todo turno nuevo lleva un tratamiento activo que el profesional ofrece; reprogramar lo conserva y desactivar o quitar un tratamiento no cambia los turnos existentes." y **RN-TR-01** "Un tratamiento no se borra: se desactiva; su nombre es único sin distinguir mayúsculas ni tildes." RN-NO-06 quita "ni datos de tratamiento".
- **06**: US-007 y US-012 suman el paso del tratamiento; US-014 "Mantener el catálogo de tratamientos".
- **07**: Flujo 2 (agendar) y Flujo 6 (reserva online) suman la elección del tratamiento.
- **09**: DD-03 aclara que el catálogo existe sin duración; DD-90 (contenido de los emails de C-11) se marca "reemplazada en parte" por DD-147; se agregan DD-141 a DD-151.
- **10**: la pregunta media de duración por prestación queda abierta y apunta a este catálogo.
- **11**: los cuatro emails llevan la línea de tratamiento.

## Decisiones resueltas (DD-141 a DD-151)

El usuario eligió la opción A en P-1 a P-10 y pidió un seed de ejemplo más chico. No quedan decisiones pendientes. Se registran en `09_decisiones_y_supuestos.md` así:

| DD | P | Decisión | Alternativas descartadas |
|---|---|---|---|
| DD-141 | P-1 | Catálogo global y, además, qué tratamientos ofrece cada profesional (`professional_treatments`). Un profesional sin tratamientos activos no se ofrece online ni se le agendan turnos nuevos | Solo catálogo global: elegir primero al profesional no filtraría nada |
| DD-142 | P-2 | El tratamiento es obligatorio en todo turno nuevo, de recepción y online | Obligatorio solo online; opcional en los dos |
| DD-143 | P-3 | Solo el administrador crea, renombra, activa o desactiva tratamientos y cambia la asignación; recepción y odontólogo leen | Administrador y recepción |
| DD-144 | P-4 | Un turno creado no cambia de tratamiento: la recepción cancela y agenda otro. Reprogramar y confirmar conservan el tratamiento sin volver a validarlo | Endpoint y acción para cambiarlo |
| DD-145 | P-5 | El tratamiento tiene solo nombre (único sin mayúsculas ni tildes) y estado; no hay descripción | Descripción interna o visible al paciente |
| DD-146 | P-6 | En la grilla, el nombre va después del paciente, separado por " · " y cortado con puntos suspensivos | Solo en el detalle; abreviatura |
| DD-147 | P-7 | La línea "Tratamiento: <nombre>" va en la confirmación, el recordatorio, la verificación y el aviso de vencimiento. Reemplaza en parte DD-90 | Solo confirmación y recordatorio; ninguno |
| DD-148 | P-8 | Los turnos anteriores quedan sin tratamiento y se muestran "Sin tratamiento"; la migración no completa datos | Completarlos con "Consulta" |
| DD-149 | P-9 | Un solo change C-17, sin partir | Catálogo y turnos por separado; backend y frontend por separado |
| DD-150 | P-10 | El turno guarda solo `treatment_id` y se muestra el nombre vigente, sin copia | Columna `treatment_name` en el turno |
| DD-151 | — | El seed trae exactamente 5 tratamientos de ejemplo: "Consulta" (solo consulta, sin procedimiento), "Limpieza dental", "Extracción", "Arreglo de caries" y "Blanqueamiento". La Dra. Ana Alvarez ofrece los 5 y el Dr. Bruno Benitez todos menos "Blanqueamiento", para que la demo muestre el filtro por profesional | 7 tratamientos con conducto y ortodoncia |

Total del plan: 53 tasks.

## Revisión de escenarios (`revisor-escenarios-turnos`)

24 escenarios revisados de `treatment-management`, `appointment-use-cases`, `public-booking`, `public-booking-api` y `database-schema`. 7 hallazgos:

| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|---|---|---|---|---|
| 1 | Reglas reemplazadas | Todos los de catálogo | RN-TU-10 dice "no hay catálogo de prestaciones" y DD-03 se justifica "sin catálogo de prestaciones" | `RN-TU-10` (05), `DD-03` (09) | Reescribir RN-TU-10 como en D-11 y aclarar DD-03; la duración sigue fija |
| 2 | Reglas reemplazadas | Emails de confirmación y vencimiento | DD-90 dice "ni tratamiento (el sistema no lo guarda)" y RN-NO-06 dice "sin … datos de tratamiento" | `DD-90` (09), `RN-NO-06` (05) | Resuelto: DD-147 la reemplaza en parte |
| 3 | Ambigüedad (corregida) | Reserva pública con tratamiento inválido y franja no reservable | No estaba definido si gana `TREATMENT_NOT_AVAILABLE` o `SLOT_UNAVAILABLE` | sin respaldo en la KB | Ya agregado a la spec: el tratamiento se chequea antes, igual que en la recepción |
| 4 | Borde faltante (corregido) | Confirmar una reserva cuyo tratamiento se desactivó | No estaba cubierto | `RN-TU-13` (05) | Resuelto: se confirma igual (DD-144) |
| 5 | Sin respaldo | Profesional sin tratamientos activos no se ofrece online ni se le agenda | Nueva regla de dominio | sin respaldo en la KB | Resuelto: DD-141 y DD-142 |
| 6 | Sin respaldo | Reprogramar no revalida el tratamiento | Nueva regla de dominio | sin respaldo en la KB (relacionada con `DD-25`, que sí revalida al paciente) | Resuelto: DD-144 |
| 7 | Borde faltante | El administrador quita un tratamiento mientras alguien agenda con él | La validación lee fuera de la transacción | `RN-TU-01` no aplica (no es superposición) | Aceptar: el turno queda con el tratamiento, igual que un turno anterior a la baja (ver Riesgos) |

Escenarios sin hallazgos: alta y nombre repetido, asignación y reemplazo, tratamiento de otro profesional, inexistente, orden de rechazos en la recepción, dos recepcionistas con distinto tratamiento (regla dura 6), reprogramar conserva, turnos anteriores, reversión de la migración. Hay escenarios esperados, de error de negocio y de borde en cada spec revisada.

Decisiones que necesitan al usuario: ninguna; los hallazgos 2, 4, 5 y 6 quedaron resueltos con DD-141 a DD-150.

## Tamaño

| | C-17 | C-15 (referencia) | C-16 (referencia) |
|---|---|---|---|
| Tasks | 53 | 54 | 18 |
| Specs (nuevas + deltas) | 3 + 11 | 3 + 11 | 1 + 4 |
| Migraciones | `0005` (2 tablas, 1 columna, 2 índices) | `0003` | `0004` |
| Endpoints nuevos | 6 (5 internos y 1 público) | 4 públicos | 0 |
| Pruebas de concurrencia | 2 (dos recepcionistas con distinto tratamiento; online contra recepción) | 3 | 3 |

## Risks / Trade-offs

- **[Carrera entre quitar o desactivar un tratamiento y agendar con él]** → la validación lee fuera de la transacción, como `validated_end`. En el peor caso el turno queda con un tratamiento que se dio de baja un instante antes, que es exactamente lo que pasa con cualquier turno anterior a la baja. No rompe ninguna regla dura. Bloquear la asignación con `FOR SHARE` sumaría complejidad sin beneficio.
- **[Romper la regla dura 6]** → el constraint, `validate_appointment` y `compute_slots` no cambian. Se suman dos tests de integración de carrera con tratamientos distintos.
- **[El frontend y la API cambian el contrato de agendar]** → `treatment_id` requerido rompe a un cliente viejo; el frontend se actualiza en el mismo change y el smoke se ajusta.
- **[Profesional sin tratamientos deja de aparecer online]** → la ficha y el panel de agendar muestran el aviso; el seed asigna tratamientos a los dos profesionales.
- **[El nombre vigente cambia el historial]** → un cambio de nombre se ve también en turnos viejos (DD-150). Se acepta como con pacientes y profesionales.
- **[Un endpoint público más]** → solo lectura, sin datos de pacientes, dentro del grupo de lecturas del límite de pedidos, con su test de acceso sin token y de 429.

## Migration Plan

1. Migración `0005_treatments`, aplicada por el servicio `migrate`. No completa datos. Rollback: `alembic downgrade 0004` funciona si ningún turno tiene tratamiento; si hay, falla a propósito.
2. El seed agrega los 5 tratamientos y la asignación en bases nuevas y en bases ya sembradas (idempotente).
3. Sin variables de entorno nuevas: `.env.example` no cambia.
4. Las reservas pendientes que existan al migrar quedan sin tratamiento y se confirman o vencen como siempre.

## Open Questions

- Ninguna.
