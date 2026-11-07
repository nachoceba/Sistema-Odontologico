# Tasks: reminders-cron (C-12)

> **Gobernanza ALTA.** El grupo 0 (confirmaciones P-1 a P-7 de `design.md`, todas con la opción A) se cerró antes de escribir código. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso de entradas distintas (TRIANGULATE) y refactor con los tests en verde después de cada paso (REFACTOR). Antes de tocar un archivo existente se corren sus tests y se anota el número (safety net); si algo falla, se frena y se reporta como falla previa. Los tests de integración corren en el contenedor (`pytest -m integration`). Sin migraciones, dependencias ni variables de entorno nuevas; no editar `.env`. `domain/` sin imports de FastAPI, SQLAlchemy, Celery ni Redis; type hints en todo y `mypy --strict` limpio. Ningún dato de paciente en registros, errores guardados ni mensajes de la cola. Emails solo a Mailpit; datos ficticios. Sin endpoints nuevos (no hay chequeo de rol nuevo). Todo cambio que toque la agenda conserva su test de no superposición (regla dura 6). Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`. Cada task indica **Verifica:** cómo se comprueba.

## 0. Confirmaciones del usuario

- [x] 0.1 Obtener respuesta a P-1 (envío en la pasada o en la cola) y P-2 (segunda pasada de `failed`) y marcarlas CONFIRMADAS en `design.md`; si P-1 = B, reescribir los requirements "Fallo parcial no corta el lote" y "Registro de la pasada sin datos personales" de `reminder-scheduling`, el delta de `notification-sending` y D-5; si P-2 ≠ A, sumar al delta de `notification-registration` la operación de volver una `failed` a `pending` y su task en el grupo 4. **Verifica:** `design.md` sin "PENDIENTE" en P-1 y P-2
- [x] 0.2 Obtener respuesta a P-3 (hora perdida), P-4 (zona horaria) y P-5 (qué turnos) y marcarlas CONFIRMADAS; si P-3 = B, cambiar el requirement "La pasada solo actúa a la hora configurada" y los escenarios de hora; si P-5 = B, sumar el filtro de profesionales inactivos y conflictos al grupo 5. **Verifica:** `design.md` sin "PENDIENTE" en P-3 a P-5
- [x] 0.3 Obtener respuesta a P-6 (disparo manual) y P-7 (un change o dos); si P-6 ≠ A, quitar el requirement "Disparo manual fuera de la hora" y ajustar el escenario "Recordatorio visible en Mailpit"; si P-7 = B, partir con `/opsx:update` entre los grupos 5 y 6. **Verifica:** `design.md` sin "PENDIENTE" en P-6 y P-7
- [x] 0.4 Quitar las marcas "pendiente de confirmación (P-n)" de las specs y ajustar specs, design y tasks a las respuestas. **Verifica:** `openspec validate reminders-cron --strict` en verde

## 1. Línea base

- [x] 1.1 Safety net general: correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/` y `ruff check`; anotar los números (C-11 dejó 1475 por defecto y 306 de integración). **Verifica:** todo en verde; si algo falla, frenar y reportarlo como falla previa

## 2. Regla pura de la pasada — spec reminder-scheduling

- [x] 2.1 RED: `tests/unit/domain/notifications/test_reminder_rules.py`: con `America/Argentina/Buenos_Aires` y `send_hour = 9`, `reminder_target_day` devuelve el lunes 09/11/2026 para el domingo 08/11 a las 09:00 locales (12:00 UTC); ver que falla. **Verifica:** el test falla por falta de la función
- [x] 2.2 GREEN: `app/domain/notifications/reminders.py` con el mínimo para pasar. **Verifica:** test en verde
- [x] 2.3 TRIANGULATE: 09:59:59 → actúa; 08:59:59 y 10:00:00 → `None`; 09:00 UTC (06:00 local) → `None`; `send_hour` 0 y 23; 31/12/2026 a la hora → 01/01/2027; `force` a las 15:00 → día siguiente; instante sin zona → `ValueError`. **Verifica:** tests en verde
- [x] 2.4 REFACTOR: `ReminderRunSummary` con `processed`, `sent`, `failed`, `pending` y su texto de log sin datos personales; exportar desde `app/domain/notifications/__init__.py`. **Verifica:** tests en verde después de cada paso y `tests/unit/test_architecture.py` en verde

## 3. Listado global de turnos — spec appointment-repository

- [x] 3.1 Safety net: correr `tests/contract/test_appointment_repository.py` (memoria y PostgreSQL con `-m integration`) y anotar el número. **Verifica:** en verde antes de tocar nada
- [x] 3.2 RED: sumar a la batería de contrato los escenarios de "Listar los turnos agendados de todos los profesionales que empiezan en un rango" (día de todos los profesionales, solo cuenta el inicio, límite superior, estados que no cuentan, mismo inicio con profesionales distintos, rango inválido); ver que fallan. **Verifica:** fallan en memoria y en PostgreSQL
- [x] 3.3 GREEN: `list_scheduled_starting_between` en el puerto `AppointmentRepository` y en `InMemoryAppointmentRepository`. **Verifica:** batería de memoria en verde
- [x] 3.4 TRIANGULATE → GREEN: implementación en `SqlAlchemyAppointmentRepository` (D-3). **Verifica:** batería en verde con `-m integration`
- [x] 3.5 REFACTOR: compartir la validación de rango con `require_query_range` sin cambiar los listados existentes; revisar con `explain_query` del MCP `postgres-odonto` que la consulta usa el índice `(starts_at)`. **Verifica:** batería completa del repositorio de turnos en verde (número de 3.1 más los nuevos) y plan revisado
- [x] 3.6 Regla dura 6: correr `tests/integration/db/test_appointment_exclusion.py` y los tests de no superposición del repositorio. **Verifica:** en verde y sin cambios

## 4. Alta condicionada del recordatorio — spec notification-registration

- [x] 4.1 Safety net: correr `tests/contract/test_notification_repository.py` y `tests/contract/test_agenda_unit_of_work.py` (memoria y PostgreSQL). **Verifica:** en verde y número anotado
- [x] 4.2 RED: escenarios "Registrar un recordatorio", "Recordatorio ya existente en cualquier estado" y "Recordatorio de un turno que ya no está vigente con ese horario"; ver que fallan. **Verifica:** fallan en ambas implementaciones
- [x] 4.3 GREEN: `add_pending_reminder` en el puerto `NotificationRepository` y en memoria, comprobando estado y horario del turno dentro de la unidad de trabajo (D-4). **Verifica:** batería de memoria en verde
- [x] 4.4 TRIANGULATE → GREEN: implementación PostgreSQL con `INSERT … SELECT … FOR SHARE ON CONFLICT DO NOTHING RETURNING` (D-4). **Verifica:** batería en verde con `-m integration`
- [x] 4.5 RED → GREEN: test de integración con dos sesiones (`tests/integration/db/`): una reprograma el turno de 10:00 a 11:00 sin confirmar, otra registra el `reminder` de 10:00; al confirmar la primera no queda ningún `reminder` de 10:00. **Verifica:** test en verde con `-m integration`
- [x] 4.6 REFACTOR: `add_pending_confirmation` y `add_pending_reminder` comparten la parte común sin cambiar su comportamiento. **Verifica:** baterías de notificaciones y de unidad de trabajo en verde (número de 4.1 más los nuevos)

## 5. Caso de uso de la pasada (memoria) — specs reminder-scheduling y notification-sending

- [x] 5.1 Safety net: correr `tests/unit/application/test_deliver_notification.py` y `test_requeue_pending.py`. **Verifica:** en verde y número anotado
- [x] 5.2 RED: `tests/unit/application/test_send_reminders.py` con repositorios en memoria, reloj fijo y `FakeEmailSender`: a las 09:00 locales con dos turnos `scheduled` del lunes (Dra. A y Dr. B) salen dos recordatorios y las notificaciones quedan `sent`; ver que falla. **Verifica:** el test falla por falta del módulo
- [x] 5.3 GREEN: `app/application/reminders.py` con `ReminderDeps` y `send_reminders` (D-5). **Verifica:** test en verde
- [x] 5.4 TRIANGULATE: fuera de hora no lee turnos ni registra nada; cancelado excluido; borde de zona (domingo 23:30 local = lunes 02:30 UTC fuera, lunes 00:00 local dentro, martes 00:00 fuera); turno que cruza la medianoche fuera; paciente inactivo incluido; sin turnos → cantidades en cero; cambio de `reminder_send_hour` entre pasadas. **Verifica:** tests en verde
- [x] 5.5 RED → GREEN: idempotencia: doble ejecución en la misma hora no registra ni envía nada nuevo; turno ya con `reminder` `failed` no recibe otro; turno cancelado o movido entre el listado y el alta no recibe recordatorio con el horario viejo; turno agendado antes de la pasada recibe confirmación y recordatorio. **Verifica:** tests en verde y `FakeEmailSender` con la cantidad exacta de mensajes
- [x] 5.6 RED → GREEN: fallo parcial: el segundo de tres falla con 550 → `sent`, `failed` (`SMTP_PERMANENT 550`), `sent` y los tres turnos siguen `scheduled`; fallo temporal → queda `pending` y la pasada sigue; error inesperado en un turno → se registra id y clase y sigue; una `failed` no se reintenta en pasadas siguientes. **Verifica:** tests en verde
- [x] 5.7 RED → GREEN: log de la pasada con `caplog`: `processed=4 sent=3 failed=1 pending=0`; "fuera de la hora configurada" cuando no actúa; ningún registro contiene el email ni el apellido del paciente. **Verifica:** tests en verde
- [x] 5.8 RED → GREEN: `force=True` a las 15:00 actúa con las mismas reglas; forzar dos veces no reenvía. **Verifica:** tests en verde
- [x] 5.9 REFACTOR: separar en `send_reminders` el procesamiento de un turno en una función privada; sin cambiar comportamiento. **Verifica:** tests del grupo y de 5.1 en verde después de cada paso
- [x] 5.10 **Punto de corte seguro (P-7)**: correr `pytest`, `pytest -m integration`, `mypy --strict app/` y `ruff check`. **Verifica:** todo en verde

## 6. Tarea Celery, Beat y entorno — specs notification-tasks, local-environment y reminder-scheduling

- [x] 6.1 Safety net: correr `tests/unit/infrastructure/test_celery_app.py`, `test_notification_tasks.py` y `test_dispatcher.py`. **Verifica:** en verde y número anotado
- [x] 6.2 RED: actualizar `test_celery_app.py`: las tareas propias son exactamente `enviar_email`, `reencolar_pendientes` y `enviar_recordatorios` (reemplaza `test_the_reminder_task_does_not_exist_yet`); `beat_schedule` tiene dos entradas propias, `reencolar-pendientes` cada 600 s y `enviar-recordatorios` con `crontab(minute=0)` sin argumentos; zona del consultorio y `enable_utc`; ver que falla. **Verifica:** el test falla por falta de la tarea y de la entrada
- [x] 6.3 GREEN: tarea `enviar_recordatorios(forzar: bool = False)` en `app/infrastructure/tasks/notifications.py`, `build_reminder_deps()` en `wiring.py` y entrada de Beat en `celery_app.py`; actualizar el docstring del módulo. **Verifica:** tests en verde
- [x] 6.4 TRIANGULATE: en modo inmediato (`task_always_eager`) con el remitente falso y reloj a las 09:00 locales, la tarea envía el recordatorio y la fila queda `sent`; a las 14:00 no envía nada; con la base que falla al empezar, la tarea termina con el error registrado, sin reintentar y sin datos del paciente. **Verifica:** tests en verde
- [x] 6.5 Regla dura 4: correr `tests/unit/api/test_route_inventory.py` y todos los `*_permissions.py`; buscar en el OpenAPI que no haya rutas de recordatorios ni tareas. **Verifica:** sin cambios y en verde
- [x] 6.6 Regla dura 6: test de agenda con la tarea registrada: agendar dos veces el mismo horario sigue dando `SLOT_TAKEN` y la pasada no cambia ningún turno. **Verifica:** test en verde
- [x] 6.7 Integración en el contenedor (`-m integration`, `tests/integration/test_reminders_end_to_end.py`): con PostgreSQL, Redis, worker y Mailpit, un turno del seed para mañana y la pasada forzada → el recordatorio aparece en la API HTTP de Mailpit con el asunto `Recordatorio de turno: …` y la fila `reminder` queda `sent`; una segunda pasada forzada no agrega mensajes. **Verifica:** test en verde en el contenedor
- [x] 6.8 `docker compose up`: el log de `worker` lista `enviar_email`, `reencolar_pendientes` y `enviar_recordatorios`, y el log de `beat` muestra la entrada `enviar-recordatorios`. **Verifica:** líneas visibles en `docker compose logs worker beat`

## 7. KB, roadmap y documentación

- [x] 7.1 Registrar P-1 a P-7 confirmadas como DD-96 en adelante en `knowledge-base/09_decisiones_y_supuestos.md`; actualizar DD-89 (segunda pasada de `failed` resuelta) y SU-03 si cambió. **Verifica:** los códigos citados existen y no repiten números
- [x] 7.2 `knowledge-base/11_recordatorios_email.md` (§Programación del recordatorio, §Idempotencia y errores, §Tareas: cantidades del log, disparo manual, sin segunda pasada); `07_flujos_principales.md` Flujo 4 (hora perdida, hallazgo 1); `10_preguntas_abiertas.md` (IN-01 sigue como mejora posterior); `04_modelo_de_datos.md` si cambia algo del índice de recordatorios. **Verifica:** relectura de cada sección contra las specs
- [x] 7.3 `CHANGES.md`: entrada C-12 con estado, tests, specs nuevas y modificadas, decisiones, y nota para C-13 (cómo forzar la pasada en el smoke test); `CLAUDE.md` y `AGENTS.md` (roadmap: C-12 archivado, siguiente habilitado C-13; ambos archivos iguales); `README.md`: qué hace la pasada de recordatorios, a qué hora actúa y cómo forzarla desde la consola del contenedor para verla en Mailpit. **Verifica:** relectura; `CLAUDE.md` y `AGENTS.md` idénticos; `git status` no muestra `.env`

## 8. Verificación final

- [x] 8.1 Correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/` y `ruff check`; comparar con la línea base del grupo 1. **Verifica:** todo en verde y ningún test previo perdido
- [x] 8.2 `openspec validate reminders-cron --strict`. **Verifica:** en verde
