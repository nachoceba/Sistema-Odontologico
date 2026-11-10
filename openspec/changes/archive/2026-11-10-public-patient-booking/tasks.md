# Tasks: C-15 `public-patient-booking`

> Las Q-1 a Q-6 están resueltas con la opción A (DD-134 a DD-139). El vencimiento automático y el email de cancelación por falta de confirmación están en C-16 `online-booking-expiry`, que depende de este change. Hasta C-16, un pendiente vencido no se puede confirmar, sigue ocupando la franja hasta que la recepción lo cancela y no recibe ningún email de cancelación.
> TDD estricto en cada tarea: primero el test que falla (RED), después el mínimo código (GREEN), un segundo caso (TRIANGULATE) y el refactor con los tests en verde. Antes de tocar un archivo existente se corre su suite y se anota la línea de base.
> Skills: `tdd` en todo. `supabase-postgres-best-practices` (solo la parte de PostgreSQL) en el grupo 1. `revisor-escenarios-turnos` al cerrar el grupo 4. `diseno-ui-odontologico` en el grupo 8.

## 1. Esquema: turno online y reserva pendiente

- [x] 1.1 Línea de base: correr `pytest` por defecto y `pytest -m integration` (con Docker) y anotar la cantidad de tests en verde
- [x] 1.2 RED: tests de integración en `tests/integration/db/test_migration.py`. Cubren: el turno con `created_by` nulo se acepta, los CHECK de `pending_until` y `confirmation_token_hash` (las dos o ninguna; pendiente solo sin creador), el hash único y que la reversión de `0003` falla con turnos online. Verificar que fallan
- [x] 1.3 GREEN: migración `alembic/versions/0003_online_appointments.py` y `AppointmentModel` (`created_by` opcional, dos columnas, CHECK e índices parciales). Verificar 1.2 y `test_models_match_migration.py` en verde
- [x] 1.4 Test de integración: un pendiente superpuesto con un confirmado del mismo profesional queda rechazado por `ex_appointments_no_overlap`, y el constraint y el tipo `appointment_status` no cambiaron (regla dura 6). Verificar en verde
- [x] 1.5 Variables `ONLINE_BOOKING_HOLD_MINUTES` y `PUBLIC_APP_URL` en `app/core/config.py` y `.env.example`, con tests de valores por defecto, rango y barra final en `tests/unit/core/`. Verificar `test_env_example.py` en verde

## 2. Dominio puro

- [x] 2.1 RED/GREEN/TRIANGULATE: `same_person_name(a, b)` en `app/domain/patients/rules.py` (mayúsculas, tildes, espacios repetidos, nombres distintos, "María José" contra "Maria"). Verificar en verde
- [x] 2.2 RED/GREEN: `pending_until_for(now, starts_at, hold_minutes)` (el menor entre `now + hold` y `starts_at`) y `can_confirm(appointment, now)` (`scheduled`, pendiente, `now < pending_until` y `now < starts_at`), con los bordes exactos. Verificar en verde
- [x] 2.3 RED/GREEN: errores nuevos con código estable (`SlotUnavailableError`, `BookingNotPossibleError`, `ConfirmationLinkInvalidError`, `PendingConfirmationError`, `BookingRejectedError` y `TooManyRequestsError`). Verificar en verde
- [x] 2.4 RED/GREEN: puerto `RateLimiter` e `InMemoryRateLimiter` (tope, ventana nueva con reloj inyectado, grupos independientes). Verificar en verde y que `test_architecture.py` sigue sin imports de framework en `domain/`
- [x] 2.5 `Appointment` y `NewAppointment` con `created_by: str | None` y `pending_until: datetime | None`. Test del repositorio en memoria. Verificar `mypy --strict app/` limpio
- [x] 2.6 RED/GREEN: generador de token y hash en `app/core/security.py` (largo, dos tokens distintos, el hash es SHA-256 hexadecimal y el token no se deduce del hash). Verificar en verde

## 3. Repositorios y unidad de trabajo

- [x] 3.1 RED/GREEN: `PatientRepository.get_by_document` con test de contrato en memoria y en PostgreSQL. Verificar en verde en los dos
- [x] 3.2 RED/GREEN: `AgendaUnitOfWork.patients` sobre la misma sesión. Test de contrato: el paciente y el turno se confirman juntos y, si el turno choca, el paciente no queda. Verificar en verde
- [x] 3.3 RED/GREEN: `AppointmentRepository.add_pending(new, token_hash, pending_until)` y `confirm_by_token_hash(hash, now)` (con `FOR UPDATE`). Tests de contrato: confirmar limpia las columnas, un hash desconocido devuelve "no encontrado" y el hash nunca sale en el `Appointment`. Verificar en verde
- [x] 3.4 `change_status` a `cancelled` limpia `pending_until` y el hash. Test de contrato. Verificar en verde
- [x] 3.5 Exponer `validated_end` (hoy `_validated_end`) sin cambiar su comportamiento. Verificar `test_book_appointment.py` y `test_reschedule_appointment.py` en verde y sin cambios

## 4. Casos de uso públicos (`app/application/public_booking.py`)

- [x] 4.1 RED/GREEN/TRIANGULATE: `list_public_professionals` (activos con horario, solo id y nombre visible, ordenados). Tests en `tests/unit/application/test_public_booking.py`. Verificar en verde
- [x] 4.2 RED/GREEN/TRIANGULATE: `public_day_slots` con los escenarios de la spec: franjas libres, pendiente que ocupa, cancelado que libera, anticipación exacta, licencia, horizonte y día local contra UTC. Más un test de coherencia: cada franja pública es `FREE` en `day_slots`. Verificar en verde
- [x] 4.3 RED/GREEN/TRIANGULATE: `book_online` con DNI nuevo (crea la ficha y el turno pendiente sin creador, no registra confirmación y encola la verificación después del commit) y con DNI existente y nombre coincidente (vincula sin modificar la ficha). Las dos respuestas son iguales. Verificar en verde
- [x] 4.4 RED/GREEN: rechazos de `book_online`. Nombre distinto, inactivo, superpuesto y carrera de DNI dan el mismo `BOOKING_NOT_POSSIBLE`. `SLOT_TAKEN` no deja un paciente sin turno. `SLOT_UNAVAILABLE` cubre grilla, horario, licencia, anticipación y horizonte. También `PROFESSIONAL_NOT_FOUND`, y un fallo al encolar no pierde el turno. Verificar en verde
- [x] 4.5 RED/GREEN/TRIANGULATE: `confirm_online_booking`: a tiempo confirma, registra la confirmación de C-11 y despacha después del commit. Un token usado, vencido, cancelado, de un turno ya empezado, desconocido o igual al hash da `CONFIRMATION_LINK_INVALID`. Verificar en verde
- [x] 4.6 RED/GREEN: `reschedule_appointment` y `record_attendance` rechazan un pendiente con `PENDING_CONFIRMATION`; `cancel_appointment` lo cancela y el token deja de servir. Tests en las suites existentes, sin cambiar las aserciones previas. Verificar en verde
- [x] 4.7 RED/GREEN: la pasada de recordatorios (C-12) excluye los pendientes, en la consulta y en el registro (`FOR SHARE`), e incluye a los online confirmados. Tests en `test_send_reminders.py` y en el contrato del repositorio. Verificar en verde
- [x] 4.8 Revisión con `revisor-escenarios-turnos` de los escenarios de los grupos 3 y 4 contra la KB. Sumar solo tests de bordes que falten y llevar las decisiones nuevas al usuario

## 5. Email de verificación

- [x] 5.1 RED/GREEN: plantilla de verificación en `app/infrastructure/email/templates.py`. Tests de asunto, profesional, fecha local, enlace con el token en el fragmento, hora límite, consultorio, línea de `EMAIL_REDIRECT_TO` y que no contiene el documento. Verificar en verde
- [x] 5.2 RED/GREEN: tarea `enviar_verificacion_reserva(appointment_id, token)`. Envía solo si el hash coincide y el turno sigue pendiente. Reintenta fallos temporales. El log no tiene el token ni el email. `reencolar_pendientes` no la toma. Verificar en verde
- [x] 5.3 Despachador de la verificación después del commit, sin depender de Redis (`apply_async(retry=False)` en `try/except`), con un test de Redis caído. Verificar en verde

## 6. Límite de pedidos sobre Redis

- [x] 6.1 Consultar con Context7 la API de tubería (`INCR` + `EXPIRE`) del cliente `redis` de Python, sin enviar código ni datos. Anotar lo consultado en `docs/skills-mcp/evidencias/public-patient-booking.md`
- [x] 6.2 RED/GREEN: `RedisRateLimiter` con test de integración contra el Redis de Compose (tope, `Retry-After`, ventana nueva y una clave sin documento ni token). Test unitario de falla abierta, con un aviso en el log sin IP. Verificar en verde

## 7. API pública y API interna

- [x] 7.1 RED: agregar las cuatro rutas a `PUBLIC_ROUTES` (`test_route_inventory.py`) y a `MATRIX` como públicas (`test_permission_matrix.py`). Chequear que sin token no responden 401 ni 403 y que las rutas internas de turnos siguen en 401. Verificar que fallan
- [x] 7.2 GREEN: `app/api/public.py` (esquemas `extra="forbid"`, salidas mínimas), incluido en `router.py`, con los códigos nuevos en `STATUS_BY_CODE` (410, y 429 con `Retry-After`). Verificar 7.1 en verde
- [x] 7.3 RED/GREEN: `tests/unit/api/test_public_booking.py` con cada escenario de `public-booking-api`. Cubre: 202 sin token y respuesta igual para DNI nuevo y existente, token de sesión basura ignorado, 404, 422 sin eco, campo desconocido, `BOOKING_NOT_POSSIBLE` idéntico en sus cuatro causas, 410 y respuestas sin datos de paciente. Verificar en verde
- [x] 7.4 RED/GREEN: límite por grupo con `InMemoryRateLimiter`: sexta reserva 429, undécima confirmación 429, grupos independientes y `X-Forwarded-For` ignorado. Campo trampa: 400 sin escribir. Verificar en verde
- [x] 7.5 RED/GREEN: `origin`, `created_by` opcional y `pending_until` en `AppointmentOut` y `AppointmentViewOut`, y `PENDING_CONFIRMATION` 409 al reprogramar un pendiente. Tests en `tests/unit/api/test_appointments.py`. Verificar la suite de API completa en verde
- [x] 7.6 Test en `test_access_log.py`: la confirmación y la reserva no dejan en el registro ni el token ni el documento. Verificar en verde

## 8. Frontend

- [x] 8.1 Línea de base: `npm test`, typecheck y lint en verde. Anotar la cantidad de tests
- [x] 8.2 RED/GREEN: `api/publicBooking.ts`. Tests: ningún pedido lleva `Authorization` aunque haya un token guardado, y un 401 no cierra la sesión. Verificar en verde
- [x] 8.3 RED/GREEN: tipos `origin`, `pending_until` y `created_by: string | null`. Etiquetas "Pendiente de confirmación" y "Online" en la grilla, la semana y el detalle. Los tests previos de agenda y gestión siguen sin cambios. Verificar en verde
- [x] 8.4 RED/GREEN: en el detalle de un pendiente, "Pendiente de confirmación hasta las HH:MM" y solo "Cancelar". Mensaje para `PENDING_CONFIRMATION`. El odontólogo no ve acciones. Verificar en verde
- [x] 8.5 RED/GREEN: rutas `/turnos` y `/turnos/confirmar` en `App.tsx`, fuera de `RequireAuth` y del "cargando" de la sesión. Tests en `App.test.tsx`. Verificar en verde
- [x] 8.6 RED/GREEN/TRIANGULATE: `public/PublicBookingPage` con los escenarios de la spec: profesionales, días limitados, franjas, día sin franjas ("Pruebe con otro."), error con reintento, formulario completo sin consulta previa de DNI, campo trampa fuera del Tab, "Verifique sus datos ingresados.", `SLOT_TAKEN` que recarga las franjas ("Elija otro."), 429 y doble clic con un solo pedido. Verificar en verde
- [x] 8.7 RED/GREEN/TRIANGULATE: pantalla de turno registrado. Muestra "Turno registrado exitosamente", "Está pendiente de confirmación. Revise su email: tiene que confirmarlo con el enlace que le enviamos antes de las HH:MM." con la hora local de `confirm_before`, y el profesional, el día y la hora elegidos. No muestra email, nombre ni documento. El foco queda en el título. Un test renderiza las dos respuestas (DNI nuevo y existente) y compara que el texto sea idéntico. Verificar en verde
- [x] 8.8 RED/GREEN: `public/ConfirmBookingPage`. Al abrirse no hace pedidos y el `POST` sale solo con el botón "Confirmar mi turno". Casos: éxito ("Turno confirmado" y "Su turno quedó confirmado. Le enviamos la confirmación por email.", con profesional, día y hora, y el fragmento borrado), 410 y sin token ("Enlace no válido", el texto de la spec y el enlace "Reservar un turno"), 429 y 500 (con el botón todavía disponible). Verificar en verde
- [x] 8.9 Revisión con `diseno-ui-odontologico` de `/turnos` (formulario y turno registrado) y `/turnos/confirmar` (confirmar, confirmado y enlace no válido) a 375, 768 y 1280 px, con el navegador integrado en `localhost` y datos ficticios. Medir el contraste con `contrastRatio`, el foco, los objetivos de al menos 24 px, que no haya desplazamiento horizontal y que no salga ningún pedido a dominios externos. Anotar las medidas en la evidencia del change y volver a `preset: "desktop"`
- [x] 8.10 Verificar `npm run build` y `npm run check:bundle` sin hallazgos, y que las páginas solo leen `VITE_API_URL`

## 9. Integración de punta a punta y documentación

- [x] 9.1 Test de integración `tests/integration/test_public_booking_api.py`: dos reservas simultáneas de la misma franja con DNIs distintos dejan un turno; la otra recibe 409 `SLOT_TAKEN` y su paciente no queda. Lo mismo con una reserva online contra una de recepción (regla dura 6). Verificar en verde
- [x] 9.2 Test de integración: dos reservas simultáneas con el mismo DNI nuevo dejan un solo paciente y la perdedora recibe `BOOKING_NOT_POSSIBLE`. Verificar en verde
- [x] 9.3 Test de integración con Mailpit. Una reserva con DNI existente manda la verificación al email de la ficha y no al escrito. Al confirmar llega la confirmación normal. Un pendiente no recibe recordatorio con la pasada forzada. Verificar en verde
- [x] 9.4 Sumar al smoke (`tests/smoke/test_end_to_end.py`) la reserva online, la lectura del enlace desde Mailpit, la confirmación y el email de confirmación. Verificar `pytest -m smoke` en verde
- [x] 9.5 Regla dura 4 en `CLAUDE.md` y `AGENTS.md`, con el texto exacto de D-10. Verificar que la línea queda igual en los dos archivos
- [x] 9.6 KB según D-11: `01`, `03`, `04`, `05` (RN-AU-01, RN-PR-02, RN-PA-05, RN-TU-13, RN-TU-15 y RN-NO-06; RN-TU-14, el vencimiento automático, la agrega C-16), `06`, `07`, `08` y `11`. Verificar que ninguna sigue diciendo que los turnos online están fuera de alcance
- [x] 9.7 `09_decisiones_y_supuestos.md`: DD-128 (reemplazada), DD-129 a DD-133 y DD-134 a DD-139 (Q-1 a Q-6). DD-140 la registra C-16. `10_preguntas_abiertas.md`: la pregunta del DNI ocupado. Verificar que los códigos citados existen
- [x] 9.8 `CHANGES.md`: entradas C-15 y C-16 (C-16 como pendiente y dependiente de C-15) en una fase nueva "Extensiones", con estado, scope, exclusiones, dependencias (C-08, C-09, C-11, C-12, C-13 y C-14), governance y "Leer antes". Actualizar el resumen del roadmap en `CLAUDE.md` y `AGENTS.md`
- [x] 9.9 Verificación final: `pytest`, `pytest -m integration`, `pytest -m smoke`, `mypy --strict app/`, `ruff check`, `npm test`, typecheck, lint y `openspec validate public-patient-booking --strict` en verde. Anotar las cantidades en la entrada de C-15
