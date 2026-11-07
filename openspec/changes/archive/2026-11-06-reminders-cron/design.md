# Design: reminders-cron (C-12)

> **Gobernanza ALTA.** Las decisiones P-1 a P-7 están **CONFIRMADAS por el usuario** (opción A en todas) y quedan registradas como DD-96 a DD-102 en `knowledge-base/09_decisiones_y_supuestos.md` (P-1 = DD-96, P-2 = DD-97, P-3 = DD-98, P-4 = DD-99, P-5 = DD-100, P-6 = DD-101, P-7 = DD-102).

## Context

Motivación en `proposal.md`. Estado real del código (revisado el 2026-11-06):

- **Lo que dejó C-11** (DD-87 a DD-95): `deliver_notification(deps, notification_id, *, attempt, max_attempts=3)` en `app/application/notifications.py` toma la fila con `claim_pending` (`FOR UPDATE SKIP LOCKED`), decide con `decide_delivery` (`SEND`, `SKIP`, `EXPIRE`), arma el email con `render_email(kind, EmailData)` (ya soporta `reminder`) y marca `sent`/`failed`; ante un fallo temporal con intentos disponibles revierte y devuelve `RETRY`. `requeue_pending` toma las `pending` de más de 5 minutos (tope 100). `NotificationDeps` y `RequeueDeps` se arman en `app/infrastructure/tasks/wiring.py`.
- **Celery** (`app/infrastructure/tasks/celery_app.py`): `timezone = CLINIC_TIMEZONE` (variable de entorno), `enable_utc = True`, JSON, `beat_schedule` con una sola entrada (`reencolar-pendientes`, 600 s). Tareas en `tasks/notifications.py`. `tests/unit/infrastructure/test_celery_app.py` fija hoy que solo existan dos tareas propias y que `enviar_recordatorios` **no** exista (esos tests cambian en C-12).
- **Docker Compose**: `worker` (depende de `db` y `redis`) y `beat` (`-s /tmp/celerybeat-schedule`) ya existen; no cambian.
- **Puertos**: `AppointmentRepository` solo lista por profesional o por paciente, con criterio de **superposición** (`list_for_professional`, `list_for_patient`); no hay listado global (DD-66). `NotificationRepository` registra solo `confirmation` (`add_pending_confirmation`, `ON CONFLICT DO NOTHING` en PostgreSQL). La unidad de trabajo de la agenda (memoria y PostgreSQL) agrupa turnos y notificaciones; reprogramar bloquea el turno (`FOR UPDATE`) y borra las `pending` del horario anterior.
- **Configuración**: `ClinicSettings` ya trae `timezone` y `reminder_send_hour` (DD-95); `04_modelo_de_datos.md` dice que la fuente de verdad de la zona en ejecución es `clinic_settings.timezone` y que `CLINIC_TIMEZONE` solo da el valor inicial.
- **Hora local**: `app/core/timezone.py` (`to_local`, `local_day_bounds`, librería estándar) ya lo usan funciones del dominio. Índice `(starts_at)` de `appointments` existe "para el job de recordatorios".
- **Context7** (`/websites/celeryq_dev_en_stable`, 2026-11-06): `timezone` es la zona con la que Celery evalúa la programación periódica, y con `enable_utc` los instantes de los mensajes van en UTC. Influyó en D-5 y P-4: el `crontab` de Beat se evalúa con `CLINIC_TIMEZONE`, pero la hora con la que decide la pasada se calcula aparte con la zona de la base.
- La skill `revisor-escenarios-turnos` se aplicó a las specs borrador (resultado al final).

## Goals / Non-Goals

**Goals:**
- Que cada turno `scheduled` del día siguiente reciba un recordatorio, como máximo uno por turno y horario, aunque la pasada corra dos veces.
- Decisión de "¿actúa?" y cálculo del día siguiente como funciones puras probadas con reloj fijo.
- Reusar el envío de C-11 sin duplicar lógica de envío ni de plantillas.

**Non-Goals:**
- Ventana de 24 h exactas (IN-01), recordatorios por WhatsApp (DD-09), más de un recordatorio por turno.
- Recuperar una hora perdida (P-3 = A) y segunda pasada de `failed` (P-2 = A).
- Pantallas, endpoints o configuración de la hora desde la interfaz.

## Decisiones confirmadas (P-1 a P-7)

Cada pregunta en lenguaje simple, con opciones, la elegida y por qué. **Todas CONFIRMADAS con la opción A.**

### P-1 — ¿La pasada manda los emails ella misma o los deja en la cola del worker? — CONFIRMADA (A), DD-96
La KB dice que la pasada "crea la notificación y envía el email" y registra `{ processed, sent, failed }` (Flujo 4, §Tareas).
- **A (elegida)**: la pasada registra cada recordatorio y lo envía en el momento, uno por uno, con el mismo envío de C-11. Un fallo permanente queda `failed`; uno temporal queda `pending` y lo levanta el reencolado a los pocos minutos con sus 3 reintentos (en el peor caso un recordatorio tiene hasta 4 intentos). El log informa `processed`, `sent`, `failed` y `pending` (se suma `pending` a lo que dice la KB).
- B: la pasada solo registra los recordatorios y pide su envío al worker (una tarea `enviar_email` por cada uno), como la confirmación. El log informa `processed`, `queued` y `not_queued`; si salió o falló se ve después, notificación por notificación.
**Por qué A**: hace lo que dicen el Flujo 4 y US-011 y deja en el log cuántos salieron y cuántos fallaron; con unos 64 emails por día la pasada dura poco. B es más uniforme con C-11 y respeta exacto los 3 intentos, pero el resumen de la pasada ya no dice cuántos se mandaron.

### P-2 — ¿Se reintentan más tarde los recordatorios que quedaron `failed`? (DD-89) — CONFIRMADA (A), DD-97
- **A (elegida)**: no. Una `failed` queda como historial y no se vuelve a intentar.
- B: una segunda pasada a la hora siguiente reintenta una vez los `reminder` `failed` de ese día con error `SMTP_TEMPORARY` (nunca los `SMTP_PERMANENT` ni `EXPIRED`); necesita volver una `failed` a `pending`.
- C: reintentar todas las `failed` del día.
**Por qué A**: un fallo temporal ya tuvo 3 intentos (DD-89) y un rechazo permanente no se arregla insistiendo; B suma una operación nueva al registro y un cambio de estado que hoy no existe; C gastaría el cupo con casillas que rebotan (mismo motivo que DD-89).

### P-3 — Si a la hora configurada el worker o Beat estaban caídos, ¿se recupera la pasada? — CONFIRMADA (A), DD-98
El Flujo 4 dice "la siguiente pasada recoge los turnos pendientes", pero con la regla "solo a la hora configurada" la pasada siguiente que actúa es la del otro día, que ya apunta a otro día.
- **A (elegida)**: no se recupera: ese día no salen recordatorios (los pacientes ya tienen su confirmación) y se corrige el Flujo 4 al archivar.
- B: la pasada actúa en cualquier hora desde la configurada hasta el fin del día; como no hay duplicados, las pasadas de las horas siguientes no reenvían, y además los turnos agendados para mañana después de la hora configurada reciben recordatorio.
**Por qué A**: es lo que pide el alcance de C-12 ("la tarea solo actúa a la hora configurada") y es lo más simple de probar. B es más robusta, pero cambia una regla de la KB ("un turno agendado después de la ejecución diaria recibe solo la confirmación") y queda como mejora posterior.

### P-4 — ¿Con qué zona horaria se calcula la hora y el "día siguiente"? — CONFIRMADA (A), DD-99
Hay dos fuentes: la variable `CLINIC_TIMEZONE` (la usa Celery) y `clinic_settings.timezone` (la base, fuente de verdad según `04_modelo_de_datos.md`).
- **A (elegida)**: la pasada lee la zona de `clinic_settings` en cada ejecución (igual que la hora configurada); `CLINIC_TIMEZONE` solo sirve para que Beat dispare en el minuto 0.
- B: usar la zona de Celery (`CLINIC_TIMEZONE`) para todo.
**Por qué A**: emails, agenda y franjas ya usan la zona de la base (RN-GL-01); si alguien cambia la zona en la base, los recordatorios siguen alineados con la agenda sin reiniciar. Con zonas de horas enteras disparar en el minuto 0 sirve igual con cualquiera de las dos.

### P-5 — ¿Qué turnos agendados de mañana reciben recordatorio? (DD-76) — CONFIRMADA (A), DD-100
DD-76 ya fija que los pacientes inactivos sí lo reciben. Falta decir qué pasa con los turnos de un profesional inactivo (DD-64 bloquea turnos nuevos, no los existentes) y con los turnos en conflicto por un cambio de horario o una licencia (DD-68: solo se avisa a recepción).
- **A (elegida)**: todos los `scheduled` de mañana, sin excepciones.
- B: saltear los de profesionales inactivos y los turnos en conflicto.
**Por qué A**: el turno sigue vigente hasta que recepción lo cancele o lo mueva (misma razón que DD-76: un recordatorio que no llega es peor) y el listado queda simple. B obliga a calcular conflictos de todos los profesionales en la pasada y a que el paciente se presente sin aviso a un turno que nadie canceló.

### P-6 — ¿Cómo se prueba el recordatorio en la demo sin esperar a las 9? — CONFIRMADA (A), DD-101
No hay endpoint (regla dura 4) y la pasada solo actúa a la hora configurada. C-13 pide en el smoke test "ejecución de la tarea de recordatorios".
- **A (elegida)**: la tarea acepta una opción `forzar` (falso por defecto) que se usa solo desde la consola del contenedor (`celery ... call enviar_recordatorios` con esa opción); Beat nunca la pasa. Con `forzar` se saltea solo el control de la hora.
- B: sin opción: para probar se cambia `reminder_send_hour` en la base a la hora actual.
- C: un script aparte en `backend/scripts/`.
**Por qué A**: una sola opción, sin ruta HTTP y sin tocar la base; repetirla no reenvía nada (no hay duplicados). B obliga a escribir en la base a mano; C duplica la forma de armar las dependencias.

### P-7 — ¿Un change o dos? — CONFIRMADA (A), DD-102
- **A (elegida)**: un solo change por grupos, con un punto de corte seguro tras el grupo 5 (pasada funcionando con repositorios en memoria y PostgreSQL, sin la tarea Celery).
- B: partir en C-12a (repositorio y caso de uso) y C-12b (tarea, Beat y KB).
**Por qué A**: son unas 30 tareas, menos que C-11, y las specs y la KB se cierran juntas.

## Decisiones técnicas

### D-1 — Capas y ubicación
- `app/domain/notifications/reminders.py` (nuevo, solo librería estándar y `app/core/timezone.py`): `reminder_target_day(now, timezone, send_hour, *, force=False) -> date | None` devuelve el día local siguiente si la hora local de `now` es `send_hour` (o si `force`), y `None` si no actúa; y `ReminderRunSummary` (`processed`, `sent`, `failed`, `pending`).
- `app/application/reminders.py` (nuevo): `ReminderDeps` (unidad de trabajo de la agenda, listado de turnos, configuración, `NotificationDeps` de C-11 y reloj) y `send_reminders(deps, *, force=False) -> ReminderRunSummary`.
- `app/infrastructure/tasks/notifications.py`: tarea `enviar_recordatorios`; `wiring.py`: `build_reminder_deps()`.
- Alternativa descartada: poner el control de la hora en la tarea Celery; quedaría sin probar con reloj fijo y mezclado con infraestructura.

### D-2 — Día siguiente y límites
El día objetivo es `to_local(now, tz).date() + 1 día`; el rango es `local_day_bounds(día, tz)` (`[00:00, 00:00 del día posterior)` en UTC), que no supone días de 24 h (SU-01). La hora local se compara con `reminder_send_hour` por igualdad (P-3 = A).

### D-3 — Listado global por inicio (DD-103)
Nuevo método del puerto `AppointmentRepository.list_scheduled_starting_between(start, end) -> list[Appointment]`: solo `scheduled`, `start <= starts_at < end`, orden `(starts_at, id)`, validación con `require_query_range` (ambos límites obligatorios). PostgreSQL: `WHERE status = 'scheduled' AND starts_at >= :start AND starts_at < :end` (usa el índice `(starts_at)`; se verifica el plan con `explain_query` del MCP de Postgres). Memoria: filtro sobre su diccionario. Criterio por inicio y no por superposición, porque `11_recordatorios_email.md` dice "cuyo `starts_at` cae en el día siguiente".
- Alternativa descartada: un `list_between(start, end, status=None)` genérico con superposición, que traería turnos del día anterior que cruzan la medianoche y obligaría a filtrar después.

### D-4 — Alta condicionada del recordatorio (DD-103)
Nuevo método `NotificationRepository.add_pending_reminder(appointment_id, starts_at) -> Notification | None`, llamado dentro de la unidad de trabajo de la agenda. PostgreSQL: un solo `INSERT … SELECT … FROM appointments WHERE id = :id AND status = 'scheduled' AND starts_at = :starts_at FOR SHARE ON CONFLICT DO NOTHING RETURNING`. El `FOR SHARE` espera a una reprogramación o cancelación en curso (que tiene el turno con `FOR UPDATE`) y vuelve a evaluar la condición con el dato confirmado: nunca queda una `pending` con un horario viejo que `decide_delivery` saltearía para siempre (el reencolado la pediría cada 10 minutos sin fin). Memoria: el registro en memoria recibe una función de consulta del turno desde la unidad de trabajo, o la unidad de trabajo hace la comprobación antes de registrar; se elige lo que deje la batería de contrato igual para ambas.
- Alternativas: leer el turno y registrar sin bloqueo (queda la carrera descrita); un método nuevo de bloqueo en `AppointmentRepository` solo para esto.

### D-5 — Pasada y envío (P-1 = A)
`send_reminders`: lee la configuración; `reminder_target_day`; si `None`, registra "fuera de la hora configurada" y termina. Si no, lista los turnos del día y por cada uno, dentro de un `try/except Exception`: abre la unidad de trabajo, `add_pending_reminder`; si devuelve `None` sigue (no cuenta); si no, después del commit llama a `deliver_notification(notification_deps, id, attempt=1)` y suma según el resultado (`SENT` → `sent`; `FAILED` o `EXPIRED` → `failed`; `RETRY` → `pending`; `SKIPPED` → `pending`, la toma otro). Un error inesperado registra el id del turno y la clase del error y suma `failed` si la notificación llegó a registrarse.
- Beat: `"enviar-recordatorios": {"task": "enviar_recordatorios", "schedule": crontab(minute=0)}`. `crontab` y no un intervalo de 3600 s: un intervalo depende de cuándo arrancó `beat` y tras un reinicio puede correr dos veces en la misma hora o saltear el borde; con el minuto 0 cada hora tiene su pasada.
- La tarea `enviar_recordatorios(forzar: bool = False)` no reintenta (`max_retries=0`); un error de base termina la tarea con el error registrado y la próxima oportunidad es al día siguiente (riesgo).

### D-6 — Registros
Una línea de resumen `recordatorios: processed=N sent=N failed=N pending=N` cuando actúa; "recordatorios: fuera de la hora configurada" cuando no. Cada envío sigue registrando lo de C-11 (ids, tipo y resultado). Nunca destinatario, nombres ni texto del servidor (DD-77).

### D-7 — Estrategia de tests
- Unitarios puros de `reminder_target_day`: 08:59:59, 09:00, 09:59:59, 10:00 locales; 09:00 UTC; `send_hour` 0 y 23; fin de mes y de año (31/12 → 01/01); `force`.
- Caso de uso con repositorios en memoria, reloj fijo y `FakeEmailSender` de C-11: doble ejecución, cancelado excluido, borde de zona (23:30 local del día anterior = 02:30 UTC del día objetivo), paciente inactivo, fallo parcial (permanente, temporal, error inesperado), cantidades del log y ausencia de datos del paciente en el log (`caplog`).
- Batería de contrato (memoria y PostgreSQL con `-m integration`) para el listado global y el alta condicionada, incluida la carrera con una reprogramación sin confirmar (dos sesiones).
- Tarea en modo inmediato (`task_always_eager`) y `beat_schedule` con dos entradas; actualizar `test_celery_app.py`.
- Integración en el contenedor: pasada forzada con un turno del seed para mañana → email en Mailpit (API HTTP de Mailpit, como en C-11) y fila `reminder` `sent`.
- Regla dura 6: un test de agenda confirma que la pasada no escribe turnos y que agendar dos veces el mismo horario sigue dando `SLOT_TAKEN` con la tarea registrada.

## Risks / Trade-offs

- [P-3 = A: una caída a la hora configurada deja ese día sin recordatorios] → los pacientes conservan la confirmación; se documenta en el Flujo 4; B queda como mejora posterior.
- [P-1 = A: un recordatorio con fallo temporal puede tener hasta 4 intentos (1 en la pasada + 3 del reencolado)] → se documenta en la spec `notification-sending`; el volumen es chico.
- [La pasada envía en serie; con el SMTP lento cada envío puede tardar hasta el timeout de 10 s] → con unos 64 turnos por día, en el peor caso unos 11 minutos dentro de la misma hora; el worker tiene más de un proceso y las confirmaciones no esperan.
- [Error de base al empezar la pasada] → la tarea no se reintenta y ese día no salen recordatorios (mismo efecto que P-3).
- [Recordatorio y confirmación casi juntos para un turno agendado esa mañana para mañana] → son dos emails distintos y es lo que dice la KB.
- [Zona con horario de verano (SU-01)] → una hora repetida actúa dos veces sin duplicar (alta condicionada); una hora inexistente perdería el día. Se acepta mientras SU-01 diga que no hay horario de verano.
- [Profesional inactivo o turno en conflicto con recordatorio (P-5 = A)] → recepción ya ve el aviso de conflictos (DD-86) y debe cancelar o mover antes de la hora configurada.

## Migration Plan

1. Sin migraciones ni variables nuevas. Reconstruir la imagen del backend y reiniciar `worker` y `beat`.
2. La primera pasada que actúa es la de la próxima hora configurada; los turnos de mañana que ya existían reciben su recordatorio en ese momento.
3. Reversión: quitar la entrada `enviar-recordatorios` de Beat y la tarea; las filas `reminder` existentes quedan como historial (las `pending` las toma el reencolado o vencen con `EXPIRED`).

## Open Questions

Ninguna: P-1 a P-7 están confirmadas.

## Revisión de escenarios (skill `revisor-escenarios-turnos`, 2026-11-06)

### Resumen
67 escenarios revisados (46 nuevos o modificados en este change), 11 hallazgos (2 ambigüedades, 2 bordes faltantes, 0 reglas solapadas, 1 pregunta abierta, 3 sin respaldo, 2 contrato incompleto, 1 contradicción). Todos quedan cubiertos con la opción elegida (P-n, confirmada) o como decisión técnica.

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Resolución (confirmada) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Contradicción | "Hora perdida" | El Flujo 4 dice que con Redis o el worker caídos "la siguiente pasada recoge los turnos pendientes", pero la pasada que actúa después es la del otro día, que apunta a otro día | `07_flujos_principales.md` Flujo 4 (casos de error); `11_recordatorios_email.md` §Programación del recordatorio | No recuperar y corregir el Flujo 4 (P-3) |
| 2 | Ambigüedad | "Resumen de la pasada", "Fallo temporal en la pasada" | El log pide `{ processed, sent, failed }`, pero un fallo temporal no es ni enviado ni fallido | `11_recordatorios_email.md` §Tareas; DD-89 | Envío en la pasada y cuarta cantidad `pending` (P-1) |
| 3 | Ambigüedad | "La hora se mide en la zona del consultorio" | Celery usa `CLINIC_TIMEZONE` y la base tiene `clinic_settings.timezone` | `04_modelo_de_datos.md` (`clinic_settings`); `11_recordatorios_email.md` §Programación; RN-GL-01 | Zona de la base en cada pasada (P-4) |
| 4 | Contrato incompleto | "Turnos de mañana de todos los profesionales" | No hay listado de turnos de todos los profesionales | DD-66; entrada C-12 de `CHANGES.md` | Listado por inicio, solo `scheduled` (técnico, D-3) |
| 5 | Contrato incompleto | "Registrar un recordatorio" | El registro solo sabe crear `confirmation` | spec `notification-registration`; RN-NO-03 | Alta condicionada de `reminder` (técnico, D-4) |
| 6 | Borde faltante | "Turno cancelado o reprogramado durante la pasada" | Entre leer el turno y registrar el recordatorio recepción puede cancelarlo o moverlo; quedaría una `pending` con horario viejo que se reencola sin fin | sin respaldo en la KB (RN-NO-05 cubre solo las `pending` que ya existían) | Alta con `FOR SHARE` (técnico, D-4) |
| 7 | Borde faltante | "Turno agendado antes de la pasada para mañana" | La KB solo dice qué pasa con los agendados después de la pasada | `11_recordatorios_email.md` §Programación; RN-NO-03 | Recibe confirmación y recordatorio (escenario agregado) |
| 8 | Pregunta abierta | "Límites del día en la zona del consultorio" | La zona del consultorio no está confirmada y se asume sin horario de verano | SU-01 (`09_decisiones_y_supuestos.md`), `10_preguntas_abiertas.md` (zona horaria, prioridad Media) | No bloquea: el código usa la zona de la base; riesgo documentado |
| 9 | Sin respaldo | "Profesional inactivo o turno en conflicto" | DD-76 cubre solo pacientes inactivos | DD-76, DD-64, DD-68 | Todos los `scheduled` (P-5) |
| 10 | Sin respaldo | "Sin segunda pasada de fallidas" | DD-89 deja la segunda pasada a C-12 sin decidir | DD-89; entrada C-12 de `CHANGES.md` | Sin segunda pasada (P-2) |
| 11 | Sin respaldo | "Forzar para la demo" | No hay forma de ejecutar la pasada fuera de hora sin endpoint | regla dura 4; entrada C-13 de `CHANGES.md` (smoke test) | Opción `forzar` desde la consola (P-6) |

### Escenarios sin hallazgos
Hora configurada y cualquier minuto de esa hora, fuera de hora, cambio de hora sin reiniciar, cancelado excluido (RN-NO-02, RN-TU-05), turno que cruza la medianoche, paciente inactivo (DD-76), sin turnos mañana, doble ejecución y pasadas simultáneas (RN-NO-03), reprogramado después del recordatorio y agendado después de la pasada (`11_recordatorios_email.md`), fallo parcial (RN-NO-04, US-011), registro sin datos personales (DD-77), tareas registradas, programación horaria, inventario de rutas sin cambios (regla dura 4), recordatorio visible en Mailpit.

Cada requirement tiene escenarios esperados, de error de negocio y de borde. No se inventaron estados ni columnas: los recordatorios usan `kind = reminder` y los estados `pending`/`sent`/`failed` de `04_modelo_de_datos.md`; no hay migración.

### Decisiones que necesitaban al usuario
P-1 a P-7 (arriba), todas confirmadas con la opción A.
