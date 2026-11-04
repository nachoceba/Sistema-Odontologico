# Tasks: appointment-use-cases (C-08)

> **Gobernanza MEDIA.** El grupo 0 (confirmaciones P-1 a P-12) quedó resuelto el 2026-11-03 con las opciones recomendadas. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso (TRIANGULATE) y refactor con los tests en verde (REFACTOR). Los tests de integración corren en el contenedor (`pytest -m integration`). No editar `.env` ni `.env.example`. `domain/` sin imports de FastAPI, SQLAlchemy, Celery ni Redis; type hints en todo. Todo cambio en la agenda lleva su test de no superposición (regla dura 6). Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`.

## 0. Confirmaciones de la usuaria (RESUELTO 2026-11-03)

- [x] 0.1 Obtener respuesta a P-1 (qué anota C-08 de los emails) y P-2 (qué pasa con los avisos pendientes al reprogramar o cancelar) y marcarlas CONFIRMADAS en `design.md`; si P-1 ≠ A, reducir los grupos 8 y 9 con `/opsx:update`
- [x] 0.2 Obtener respuesta a P-3 (paciente con dos turnos a la misma hora, H-2) y marcarla CONFIRMADA; si es A, quitar el requirement "Un paciente no tiene dos turnos superpuestos" y `PATIENT_DOUBLE_BOOKED`
- [x] 0.3 Obtener respuestas a P-4 (quién marca atención), P-5 (profesional inactivo) y P-6 (reprogramar con otro profesional) y marcarlas CONFIRMADAS
- [x] 0.4 Obtener respuestas a P-7 (motivo obligatorio), P-8 (urgencias) y P-12 (tres bordes de horario) y marcarlas CONFIRMADAS
- [x] 0.5 Obtener respuestas a P-9 (consultas y franjas en C-08), P-10 (listado global a C-12) y P-11 (un change o dos) y marcarlas CONFIRMADAS; si P-11 = B, partir con `/opsx:update` entre los grupos 7 y 8
- [x] 0.6 Si alguna respuesta difiere de la recomendación, ajustar specs, design y tasks; registrar las decisiones como DD-62 en adelante en `knowledge-base/09_decisiones_y_supuestos.md`, cerrar H-2 en `10_preguntas_abiertas.md`; verificar `openspec validate appointment-use-cases --strict` en verde

## 1. Preparación y línea base

- [x] 1.1 Safety net: correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/` y `ruff check`; anotar los números en verde (C-04 dejó 605 por defecto y 193 de integración); si algo falla, frenar y reportarlo como falla previa

## 2. Errores y reglas puras — specs appointment-use-cases y error-model

- [x] 2.1 RED: `tests/unit/domain/appointments/test_use_case_errors.py`: cada error nuevo de D-1 es `DomainError` con su código; `error_for_rejection` mapea cada `RejectionReason` (y `OVERLAPS_EXISTING` → `SlotTakenError`) y `error_for_transition` cada `TransitionRejection` usada; ver que falla
- [x] 2.2 GREEN → TRIANGULATE → REFACTOR: `app/domain/appointments/errors.py`; verificar en verde y `tests/unit/test_architecture.py` en verde
- [x] 2.3 RED: tests de `has_sub_minute_precision` (10:00 no; 10:00:30 sí; 10:00:00.5 sí) y de `patient_has_overlap` (mismo horario otro profesional → sí; otro horario el mismo día → no; cancelado → no; pegado → no; excluye el propio turno al reprogramar) en `tests/unit/domain/appointments/test_rules_use_cases.py`; ver que falla
- [x] 2.4 GREEN → TRIANGULATE → REFACTOR: funciones en `app/domain/appointments/rules.py` reusando `ranges_overlap`/`overlaps_scheduled`; verificar en verde con los tests archivados de C-05a a C-05d

## 3. Casos de uso de agendar y consultar (memoria) — spec appointment-use-cases

- [x] 3.1 RED: `tests/unit/application/test_book_appointment.py` con repositorios en memoria y reloj fijo: los 15 escenarios de "Agendar un turno" (incluidos `slot_minutes = 20` desde la configuración, límite exacto de anticipación, segundos, orden fijo con paciente inexistente) y los 3 de "Un paciente no tiene dos turnos superpuestos"; verificar que un rechazo no escribe nada; ver que fallan
- [x] 3.2 GREEN: `app/application/appointments.py` con `AgendaDeps`, cargador de contexto (día local con bordes, DD-19) y `book_appointment` escribiendo directo en el repositorio (la unidad de trabajo llega en el grupo 8); verificar en verde
- [x] 3.3 TRIANGULATE → REFACTOR: segundo caso por motivo de rechazo con otro profesional y otra zona de entrada; extraer el cargador de contexto; verificar en verde
- [x] 3.4 RED → GREEN: `get_appointment`, `list_appointments` y `day_slots` (3 + 3 escenarios de la spec, alcance del odontólogo con `can_access_professional`, coherencia franja libre ↔ agendar con el mismo cargador); verificar en verde

## 4. Casos de uso de cancelar, reprogramar y marcar atención (memoria) — spec appointment-use-cases

- [x] 4.1 RED: `tests/unit/application/test_cancel_appointment.py` (5 escenarios; el slot cancelado se puede volver a agendar: test de no superposición); ver que falla
- [x] 4.2 GREEN → TRIANGULATE → REFACTOR: `cancel_appointment` con motivo ya validado; verificar en verde
- [x] 4.3 RED: `tests/unit/application/test_reschedule_appointment.py` (7 escenarios; el propio turno no cuenta como ocupación, Hallazgo 1; si falla, el turno original no cambia; nuevo slot ocupado → `SLOT_TAKEN`); ver que falla
- [x] 4.4 GREEN → TRIANGULATE → REFACTOR: `reschedule_appointment` con duración vigente (P-12c); verificar en verde
- [x] 4.5 RED → GREEN → TRIANGULATE: `tests/unit/application/test_record_attendance.py` (5 escenarios, inicio exacto DD-23, turno ajeno `FORBIDDEN` antes que cualquier otra regla, ficha inactiva permitida); `record_attendance`; verificar en verde

## 5. API de turnos — specs appointment-api y error-model

- [x] 5.1 RED: `tests/unit/api/test_error_handlers.py` para los códigos nuevos de D-8 (404, 409, 400 explícitos); ver que falla
- [x] 5.2 GREEN: ampliar `STATUS_BY_CODE` en `app/api/errors.py`; verificar en verde junto con los escenarios archivados de error-model
- [x] 5.3 RED: `tests/unit/api/test_appointments_permissions.py`: tabla de los siete endpoints × admin, recepción, odontólogo propio, odontólogo ajeno, odontólogo sin ficha y sin token (401 antes que 403), con la comprobación "nada cambió" en cada 403 (patrón de `test_users_permissions.py`); ver que falla
- [x] 5.4 RED: `tests/unit/api/test_appointments.py`: escenarios de "Endpoints de turnos", "Formato de fechas y validación de entrada" (zona `+03:00`, sin zona 422, 32 días 422, motivo vacío 422 sin eco) y "Rechazos de negocio" (409 `SLOT_TAKEN`, 400 `OUTSIDE_WORKING_HOURS`, `PATIENT_DOUBLE_BOOKED` sin datos de otro paciente), `DELETE` → 405; ver que fallan
- [x] 5.5 GREEN: `app/api/appointments.py` (esquemas Pydantic de D-5 con `AwareDatetime`, `require_role`, alcance), fábricas sobreescribibles y `get_clock` en `app/api/dependencies.py`, inclusión en `app/api/router.py`; verificar 5.3, 5.4 y `tests/unit/api/test_route_inventory.py` en verde
- [x] 5.6 REFACTOR: validadores compartidos (recorte de texto) y conversión a `AppointmentOut`; todo en verde
- [x] 5.7 Verificar que `/openapi.json` lista las siete operaciones con el esquema `HTTPBearer`; `mypy --strict app/` y `ruff check` en verde

## 6. Integración contra PostgreSQL — specs appointment-api y access-control

- [x] 6.1 RED → GREEN: `tests/integration/test_appointments_api.py` con el seed: agendar real (turno en UTC en la base), choque de slot 409, cancelar y volver a agendar el mismo horario, reprogramar, marcar atención con reloj fijo; verificar con `pytest -m integration`
- [x] 6.2 RED → GREEN: test de punta a punta de DD-53 (spec access-control): la Dra. A del seed recibe 403 en detalle y listado de turnos del Dr. B y al marcar atención de un turno del Dr. B por id; verificar con `pytest -m integration`

## 7. Concurrencia real — spec appointment-unit-of-work (punto de corte seguro, P-11)

- [x] 7.1 RED: `tests/integration/db/test_appointment_concurrency.py` (D-9): dos sesiones simultáneas agendan el mismo slot → una se guarda y la otra `SLOT_TAKEN`, un solo turno `scheduled`; con `lock_timeout` y `join(timeout)`. Es un test de caracterización (el constraint ya existe desde C-02): para probar que no pasa en vacío, correrlo una vez contra una tabla temporal sin el constraint o con el `status` de un turno en `cancelled` y verlo fallar, y anotarlo
- [x] 7.2 GREEN → TRIANGULATE: casos "reprogramar compite con agendar" y "profesionales distintos se guardan los dos"; variante a nivel de caso de uso con un freno inyectado entre validar y escribir; repetir 20 veces en local sin fallos; verificar con `pytest -m integration`
- [x] 7.3 Checkpoint: suite completa en verde (por defecto, integración, mypy, ruff). Si P-11 lo pide, aquí se puede archivar C-08a con el despachador vacío y sin filas de notificación

## 8. Unidad de trabajo y registro de notificaciones — specs appointment-unit-of-work y notification-registration

- [x] 8.1 RED: tipos `Notification`, `NotificationKind`, `NotificationStatus` y test de paridad con los enums de la base (como `test_role_parity.py`); ver que falla
- [x] 8.2 GREEN: `app/domain/appointments/types.py` y puertos `NotificationRepository`, `AgendaUnitOfWork`, `NotificationDispatcher` en `ports.py`; verificar en verde y `mypy --strict app/`
- [x] 8.3 RED: `tests/contract/test_notification_repository.py` (registrar `pending`, listar, borrar `pending` todas o de un horario sin tocar `sent`/`failed`, no duplicar) con la fábrica `in_memory`; ver que falla
- [x] 8.4 GREEN: `app/infrastructure/in_memory/notifications.py`; verificar en verde
- [x] 8.5 RED → GREEN: fábrica `postgres` y `app/infrastructure/db/repositories/notifications.py` (`ON CONFLICT DO NOTHING` o `SAVEPOINT`, D-6); batería en verde con ambas fábricas y `tests/contract/test_import_order.py` en verde
- [x] 8.6 Safety net del refactor: correr la batería de contrato de turnos con ambas fábricas y anotar el número; RED: tests de `SqlAlchemyAgendaUnitOfWork` e `InMemoryAgendaUnitOfWork` (todo junto; falla de la notificación revierte el turno; falla al reprogramar tras borrar pendientes conserva todo); ver que fallan
- [x] 8.7 GREEN → REFACTOR: alcance de sesión interno en `SqlAlchemyAppointmentRepository` (D-2) sin cambiar su contrato; unidades de trabajo en memoria y PostgreSQL; verificar la batería de turnos con el mismo número que en 8.6 y los tests nuevos en verde con `pytest -m integration`

## 9. Casos de uso con unidad de trabajo y despachador — spec notification-registration

- [x] 9.1 RED: ampliar los tests de casos de uso: agendar registra una confirmación `pending`; rechazado no registra nada; reprogramar borra las `pending` anteriores, conserva `sent`, agrega la nueva y no duplica al volver a un horario ya confirmado; reprogramar al mismo horario no registra nada; cancelar borra las `pending` y no crea nada; marcar atención no toca notificaciones; ver que fallan
- [x] 9.2 GREEN: `book`, `reschedule` y `cancel` escriben por la unidad de trabajo (D-3); verificar en verde junto con los grupos 3 y 4
- [x] 9.3 RED → GREEN: despachador (D-7): recibe exactamente la confirmación tras el commit; no se llama si se rechaza; si lanza error la API responde 201 y el turno y la `pending` quedan guardados, y el log no contiene datos del paciente; `NoOpNotificationDispatcher` conectado por defecto; verificar en verde
- [x] 9.4 Integración: repetir 7.1 verificando una sola confirmación `pending` en la base; agendar real con falla forzada de la notificación no deja el turno; verificar con `pytest -m integration`

## 10. Cierre

- [x] 10.1 Prueba manual con Docker: seed, entrar como recepción, agendar, ver franjas, reprogramar, cancelar; entrar como la Dra. A, marcar atención de un turno propio iniciado (con un turno cargado para ese momento) y comprobar 403 sobre uno del Dr. B; revisar las filas de `email_notifications`
- [x] 10.2 Suite completa en verde (backend por defecto e integración, mypy, ruff; frontend sin cambios: `npm test` igual que antes); anotar números finales
- [x] 10.3 Actualizar `CHANGES.md` (estado de C-08; notas para C-09 si P-9 = A, para C-11 sobre el despachador y las `pending` viejas, para C-12 si P-10 = A) y la KB con las DD confirmadas; verificar `openspec validate appointment-use-cases --strict`
