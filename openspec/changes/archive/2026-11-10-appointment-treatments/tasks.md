# Tasks: C-17 `appointment-treatments`

> Decisiones resueltas: P-1 a P-10 con la opción A (DD-141 a DD-150) y el seed de ejemplo con 5 tratamientos (DD-151). No quedan pendientes.
> TDD estricto en cada tarea: primero el test que falla (RED), después el mínimo código (GREEN), un segundo caso (TRIANGULATE) y el refactor con los tests en verde. Antes de tocar un archivo existente se corre su suite y se anota la línea de base.
> Skills: `tdd` en todo. `supabase-postgres-best-practices` (solo la parte de PostgreSQL) en el grupo 1. `revisor-escenarios-turnos` al cerrar el grupo 5. `diseno-ui-odontologico` en el grupo 9.
> Regla dura 6: ninguna tarea toca `ex_appointments_no_overlap`, `validate_appointment` ni `compute_slots`.

## 1. Esquema: catálogo, asignación y tratamiento del turno

- [x] 1.1 Línea de base: correr `pytest` por defecto y `pytest -m integration` (con Docker) y anotar la cantidad de tests en verde
- [x] 1.2 RED: tests de integración en `tests/integration/db/test_migration.py`. Cubren: turno con `treatment_id` existente aceptado, FK inexistente rechazada, `name_key` repetido rechazado, CHECK de largo del nombre, par profesional y tratamiento repetido rechazado, borrar un tratamiento usado rechazado por `RESTRICT`, turnos previos con `treatment_id` nulo después de migrar y reversión de `0005` que falla con un turno con tratamiento. Verificar que fallan
- [x] 1.3 GREEN: migración `alembic/versions/0005_treatments.py` y modelos `TreatmentModel`, `ProfessionalTreatmentModel` y `AppointmentModel.treatment_id` con su índice. Verificar 1.2 y `test_models_match_migration.py` en verde
- [x] 1.4 Test de integración: dos turnos `scheduled` superpuestos del mismo profesional con tratamientos distintos quedan rechazados por `ex_appointments_no_overlap`, y el constraint y el tipo `appointment_status` no cambiaron (regla dura 6). Verificar en verde

## 2. Dominio puro (`app/domain/treatments/`)

- [x] 2.1 RED/GREEN: mover la normalización de `same_person_name` a `app/domain/text.py` (`comparable_text`) sin cambiar su comportamiento. Verificar los tests existentes de `same_person_name` en verde y sin cambios
- [x] 2.2 RED/GREEN/TRIANGULATE: `clean_treatment_name` y `treatment_name_key` (espacios, mayúsculas, tildes, vacío, 80 y 81 caracteres). Verificar en verde
- [x] 2.3 RED/GREEN/TRIANGULATE: `check_treatment_for_booking` con aceptado, inexistente, inactivo, no ofrecido y asignado pero inactivo. Verificar en verde
- [x] 2.4 RED/GREEN: tipos `Treatment` y `NewTreatment`, errores con código estable (`TREATMENT_NOT_FOUND`, `TREATMENT_NOT_AVAILABLE`, `TREATMENT_NAME_TAKEN`) y puerto `TreatmentRepository`. Verificar `test_architecture.py` sin imports de framework en `domain/`
- [x] 2.5 `NewAppointment` y `Appointment` con `treatment_id: str | None`; el repositorio en memoria lo guarda y lo devuelve. Verificar `mypy --strict app/` limpio y las suites de turnos sin cambios en sus aserciones

## 3. Repositorios

- [x] 3.1 RED/GREEN: `InMemoryTreatmentRepository` con test de contrato (`tests/contract/test_treatment_repository.py`): alta, nombre repetido por `name_key`, edición, listado por nombre, `get` inexistente. Verificar en verde
- [x] 3.2 RED/GREEN: asignación en el contrato: `replace_for_professional` reemplaza todo y quita repetidos, `list_for_professional` trae activos e inactivos, `offered_ids` y `list_offered` solo activos. Verificar en verde en memoria
- [x] 3.3 GREEN: `SqlAlchemyTreatmentRepository` contra el mismo contrato en PostgreSQL, con la violación del único traducida a `TreatmentNameTakenError`. Verificar en verde
- [x] 3.4 RED/GREEN: `SqlAlchemyAppointmentRepository` guarda y lee `treatment_id` en `add`, `add_pending`, `get`, `list_for_professional` y `reschedule` (lo conserva). Test de contrato en memoria y en PostgreSQL. Verificar en verde

## 4. Casos de uso del catálogo (`app/application/treatments.py`)

- [x] 4.1 RED/GREEN/TRIANGULATE: `list_treatments`, `create_treatment` y `update_treatment` (renombrar, desactivar, mismo nombre con otra mayúscula, nombre de otro tratamiento, inexistente). Tests en `tests/unit/application/test_treatments.py`. Verificar en verde
- [x] 4.2 RED/GREEN/TRIANGULATE: `list_professional_treatments` (odontólogo propio y ajeno con `ForbiddenError`) y `replace_professional_treatments` (profesional inexistente, id inexistente sin cambiar la asignación anterior, lista vacía, repetidos). Verificar en verde
- [x] 4.3 RED/GREEN: desactivar un tratamiento y quitarlo de un profesional no cambia los turnos que lo tienen. Verificar en verde

## 5. Agenda y reserva pública con tratamiento

- [x] 5.1 RED/GREEN/TRIANGULATE: `book_appointment` con `treatment_id`: válido, no ofrecido, inactivo, inexistente y el orden de rechazos (tratamiento antes que horario, después de paciente y profesional activos). Ningún rechazo escribe. Tests en `test_book_appointment.py` sin cambiar las aserciones previas. Verificar en verde
- [x] 5.2 RED/GREEN: `reschedule_appointment` conserva el tratamiento, también con el tratamiento desactivado y en un turno sin tratamiento. Verificar `test_reschedule_appointment.py` en verde
- [x] 5.3 RED/GREEN: `AppointmentView` con `treatment_name` vigente (una lectura por tratamiento distinto, nulo en turnos anteriores, nombre cambiado después de agendar). Verificar en verde
- [x] 5.4 RED/GREEN/TRIANGULATE: `list_public_professionals` y `_require_offered` exigen al menos un tratamiento activo; nuevo `list_public_treatments` (solo activos ofrecidos, ordenados, `PROFESSIONAL_NOT_FOUND` para uno no ofrecido). Verificar `test_public_booking.py` en verde
- [x] 5.5 RED/GREEN/TRIANGULATE: `book_online` con `treatment_id`: válido (respuesta con `treatment_name`, igual para DNI nuevo y existente), inexistente, inactivo y no ofrecido con el mismo `TREATMENT_NOT_AVAILABLE`, sin crear paciente ni turno, y el tratamiento chequeado antes que la franja. Verificar en verde
- [x] 5.6 RED/GREEN: `confirm_online_booking` devuelve `treatment_name` y confirma aunque el tratamiento se haya desactivado; nulo para una reserva sin tratamiento. Verificar en verde
- [x] 5.7 Revisión con `revisor-escenarios-turnos` de los escenarios de los grupos 4 y 5 contra la KB. Sumar solo tests de bordes que falten y llevar las decisiones nuevas al usuario

## 6. Emails

- [x] 6.1 RED/GREEN/TRIANGULATE: `render_email` con la línea `Tratamiento: <nombre>` después de `Profesional:` en confirmación, recordatorio y aviso de vencimiento, y sin la línea si no hay tratamiento. Verificar en verde
- [x] 6.2 RED/GREEN: `render_verification_email` con la línea de tratamiento y sin ella. Verificar en verde
- [x] 6.3 RED/GREEN: `deliver_notification` y `send_verification` leen el nombre vigente del tratamiento (renombrado antes del envío) y no fallan si el turno no tiene. Verificar las suites de notificaciones y verificación en verde

## 7. API

- [x] 7.1 RED: sumar las cinco rutas internas a `MATRIX` con sus roles (lecturas: los tres; escrituras: admin) y la ruta pública a `PUBLIC_ROUTES` y a `MATRIX` como pública. Verificar que `test_route_inventory.py` y `test_permission_matrix.py` fallan
- [x] 7.2 GREEN: `app/api/treatments.py` y las rutas de tratamientos en `app/api/professionals.py`, incluidas en `router.py`, con esquemas `extra="forbid"` y los códigos nuevos en `STATUS_BY_CODE`. Verificar 7.1 en verde
- [x] 7.3 RED/GREEN: `tests/unit/api/test_treatments.py` y `test_treatments_permissions.py` con cada escenario de `treatment-api`: 201, 200, 404, 409, 422 sin eco, campo desconocido, más de 100 ids, 403 de recepción y odontólogo en escrituras antes de validar el cuerpo, odontólogo propio y ajeno en lecturas, 401 sin token. Verificar en verde
- [x] 7.4 RED/GREEN: `POST /api/v1/appointments` exige `treatment_id` (422 sin él), responde `treatment_id`, y el listado y el detalle traen `treatment_name`; `TREATMENT_NOT_AVAILABLE` 409 y `TREATMENT_NOT_FOUND` 404. Reprogramar con `treatment_id` en el cuerpo lo ignora. Tests en `test_appointments.py`. Verificar en verde
- [x] 7.5 RED/GREEN: `GET /api/v1/public/professionals/{id}/treatments` sin token (200 con solo id y nombre, 404 de un profesional no ofrecido, token basura ignorado) y el límite de lecturas compartido (61.ª lectura mezclando profesionales, tratamientos y franjas da 429 con `Retry-After`; otros grupos siguen libres). Verificar en verde
- [x] 7.6 RED/GREEN: `POST /api/v1/public/appointments` con `treatment_id` (422 sin él, 409 `TREATMENT_NOT_AVAILABLE` idéntico en sus tres causas) y `treatment_name` en la reserva y en la confirmación. Verificar `test_public_booking.py` de API en verde

## 8. Seed de demostración

- [x] 8.1 RED/GREEN: tests del seed con exactamente 5 tratamientos activos ("Consulta", "Limpieza dental", "Extracción", "Arreglo de caries" y "Blanqueamiento"), la Dra. Ana Alvarez con los 5, el Dr. Bruno Benitez con 4 (sin "Blanqueamiento"), los dos profesionales ofrecidos online y los tratamientos públicos de cada uno distintos (filtro por profesional). Verificar en verde
- [x] 8.2 RED/GREEN: idempotencia: segunda corrida sin filas nuevas, un tratamiento desactivado o renombrado y una asignación cambiada se conservan, y una base sembrada antes de C-17 recibe los tratamientos sin tocar el resto. Verificar en verde

## 9. Frontend

- [x] 9.1 Línea de base: `npm test`, typecheck y lint en verde. Anotar la cantidad de tests
- [x] 9.2 RED/GREEN: `api/treatments.ts` y `listPublicTreatments` en `api/publicBooking.ts` (sin `Authorization` aunque haya token); tipos `treatment_id` y `treatment_name` en `Appointment`, sin `any`. Verificar en verde
- [x] 9.3 RED/GREEN/TRIANGULATE: `BookingPanel` con el selector "Tratamiento": botón habilitado solo con paciente y tratamiento, `POST` con `treatment_id`, profesional sin tratamientos activos, `TREATMENT_NOT_AVAILABLE` que recarga la lista y conserva el paciente, aviso de éxito con el tratamiento y doble clic con un solo pedido. Los tests previos siguen sin cambios en sus aserciones salvo el pedido nuevo. Verificar en verde
- [x] 9.4 RED/GREEN: fila "Tratamiento" en `AppointmentDetail` ("Sin tratamiento" en turnos anteriores) y en `RescheduleDialog`, sin acción para cambiarlo. Verificar en verde
- [x] 9.5 RED/GREEN: `DayColumn` con " · <tratamiento>" en el día y la semana, igual que antes sin tratamiento, y cortado con puntos suspensivos. Verificar en verde
- [x] 9.6 RED/GREEN/TRIANGULATE: `pages/TreatmentsPage` en `/tratamientos` con `RequireRole roles={['admin']}` y el enlace solo para admin: listado, vacío, error con reintento, alta, nombre repetido, renombrar, desactivar con confirmación, reactivar y doble clic. Verificar en verde
- [x] 9.7 RED/GREEN: `professionals/TreatmentsPanel` en la ficha: casillas y "Guardar tratamientos" para admin, lista de solo lectura para recepción y odontólogo, aviso sin tratamientos activos. Verificar en verde
- [x] 9.8 RED/GREEN/TRIANGULATE: `PublicBookingPage` con el paso "Tratamiento" entre profesional y día: días y franjas recién con tratamiento, cambiar de profesional borra tratamiento y franja, cambiar de tratamiento conserva el día, "Turno elegido" con el tratamiento, `TREATMENT_NOT_AVAILABLE` que recarga la lista y conserva los datos, error con reintento. Verificar en verde
- [x] 9.9 RED/GREEN: "Tratamiento" en la pantalla de turno registrado (texto idéntico para DNI nuevo y existente) y en `ConfirmBookingPage` (sin la fila si es nulo). Verificar en verde
- [ ] 9.10 Revisión con `diseno-ui-odontologico` de `/tratamientos`, la sección de la ficha, el panel de agendar, la grilla con nombres largos y `/turnos` a 375, 768 y 1280 px, con el navegador integrado en `localhost` y datos ficticios: contraste con `contrastRatio`, foco, objetivos de al menos 24 px, sin desplazamiento horizontal y sin pedidos a dominios externos. Anotar las medidas en `docs/skills-mcp/evidencias/appointment-treatments.md` y volver a `preset: "desktop"`
- [x] 9.11 Verificar `npm run build` y `npm run check:bundle` sin hallazgos

## 10. Integración de punta a punta y documentación

- [x] 10.1 Test de integración `tests/integration/test_appointments_api.py`: dos recepcionistas agendan al mismo tiempo el mismo horario con tratamientos distintos; uno queda y el otro recibe 409 `SLOT_TAKEN`. Lo mismo con una reserva online contra una de recepción (regla dura 6). Verificar en verde
- [x] 10.2 Test de integración con Mailpit: la confirmación de un turno de recepción y la verificación de una reserva online llegan con `Tratamiento: <nombre>`. Verificar en verde
- [x] 10.3 Sumar al smoke (`tests/smoke/test_end_to_end.py`) el tratamiento al agendar ("Limpieza dental" con la Dra. Ana Alvarez) y al reservar online ("Consulta" con el Dr. Bruno Benitez), y la línea de tratamiento en el email. Verificar `pytest -m smoke` en verde
- [x] 10.4 Regla dura 4 en `CLAUDE.md` y `AGENTS.md` con el texto exacto de D-10. Verificar que la línea queda igual en los dos archivos
- [x] 10.5 KB según D-11: `01`, `03`, `04`, `05` (RN-TU-10, RN-TU-16, RN-TR-01 y RN-NO-06), `06`, `07`, `10` y `11`. Verificar que ninguna sigue diciendo que no hay catálogo de tratamientos ni que los emails no llevan tratamiento, y que la duración variable sigue fuera de alcance
- [x] 10.6 `09_decisiones_y_supuestos.md`: aclaración de DD-03, DD-90 reemplazada en parte por DD-147 y DD-141 a DD-151 con el texto de la tabla de decisiones del design. `04_modelo_de_datos.md`: seed con los 5 tratamientos. Verificar que los códigos citados existen
- [x] 10.7 `CHANGES.md`: entrada C-17 en "Extensiones" con estado, scope, exclusiones (duración variable), dependencias (C-07, C-08, C-10, C-11, C-15 y C-16), governance y "Leer antes"; árbol y tabla resumen. Actualizar el resumen del roadmap en `CLAUDE.md` y `AGENTS.md`
- [x] 10.8 Verificación final: `pytest`, `pytest -m integration`, `pytest -m smoke`, `mypy --strict app/`, `ruff check`, `npm test`, typecheck, lint y `openspec validate appointment-treatments --strict` en verde. Anotar las cantidades en la entrada de C-17
