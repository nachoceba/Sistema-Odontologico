# Design: email-confirmation-infra (C-11)

> **Gobernanza ALTA.** Las decisiones P-1 a P-9 fueron **CONFIRMADAS** por el usuario el 2026-11-06, todas con la opción recomendada (A). Se registran como DD-87 a DD-95 en `knowledge-base/09_decisiones_y_supuestos.md`.

## Context

Motivación en `proposal.md`. Estado real del código (revisado el 2026-11-06):

- **Lo que dejó C-08** (DD-62): `book_appointment` y `reschedule_appointment` (`app/application/appointments.py`) registran la `confirmation` `pending` dentro de la unidad de trabajo y llaman a `_dispatch` después del commit; `_dispatch` atrapa cualquier excepción y registra solo ids de turno y el nombre de la clase del error. Reprogramar borra las `pending` del horario anterior (de cualquier tipo) y cancelar borra todas las `pending` del turno. El despachador de producción es `NoOpNotificationDispatcher` (`app/infrastructure/notifications.py`), inyectado en `get_agenda_deps` (`app/api/dependencies.py`).
- **Puerto de notificaciones** (`app/domain/appointments/ports.py`): `NotificationRepository` con `add_pending_confirmation`, `delete_pending` y `list_for_appointment`; `NotificationDispatcher.dispatch(notifications)`. Tipos `Notification`, `NotificationKind`, `NotificationStatus` en `app/domain/appointments/types.py` (sin `created_at`). Implementaciones en memoria y PostgreSQL (`INSERT … ON CONFLICT DO NOTHING`), con batería de contrato en `tests/contract/test_notification_repository.py`.
- **Esquema**: `email_notifications` (`id`, `appointment_id`, `kind`, `status`, `sent_at`, `error`, `appointment_starts_at`, `UNIQUE (appointment_id, kind, appointment_starts_at)`) **no tiene `created_at`** (`0001_initial_schema.py`, `EmailNotificationModel`), aunque `11_recordatorios_email.md` pide reencolar las `pending` "con más de unos minutos de antigüedad" (P-3). `clinic_settings` ya tiene `clinic_name`, `address`, `phone` y `reminder_send_hour`, y el seed los carga; el dominio (`ClinicSettings`) y el repositorio solo exponen `slot_minutes`, `timezone` y `min_notice_hours`.
- **Celery** (`app/infrastructure/tasks/celery_app.py`): app `odonto` con broker `REDIS_URL`, `timezone = CLINIC_TIMEZONE`, `enable_utc = True`, sin tareas; `tests/unit/infrastructure/test_celery_app.py::test_no_business_tasks_registered` fija que no haya tareas propias (este test cambia en C-11, spec `local-environment`). `app/infrastructure/email/` está vacío. `celery[redis]` ya es dependencia; mypy ignora los imports de Celery.
- **Configuración** (`app/core/config.py`): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` (`SecretStr`), `SMTP_USE_TLS`, `EMAIL_FROM` ya existen; `tests/unit/test_env_example.py` compara las variables con `.env.example`.
- **Docker Compose**: `worker` y `beat` usan la imagen del backend con `env_file: .env`; `worker` depende solo de `redis`; `mailpit` publica 8025 y escucha SMTP en 1025 dentro de la red.
- **Pacientes**: email obligatorio y en minúsculas (DD-73); la validación de emails existe en `app/domain/users/rules.is_valid_email`.
- **Regla de arquitectura**: `tests/unit/test_architecture.py` prohíbe importar FastAPI, SQLAlchemy, Celery y Redis desde `domain/`.
- La skill `revisor-escenarios-turnos` se aplicó a las specs borrador (resultado en "Revisión de escenarios" al final).

## Goals / Non-Goals

**Goals:**
- Que una confirmación salga sola, fuera del pedido HTTP, y quede registrada como `sent` o `failed`, sin que Redis, el worker o el SMTP puedan romper una operación de turno.
- Como máximo un email por notificación aunque la tarea se entregue dos veces o se reencole.
- Lógica de decisión y plantillas como funciones puras, probadas sin Celery ni SMTP.
- Dejar a C-12 todo listo: plantilla `reminder`, envío genérico por tipo, configuración del consultorio con `reminder_send_hour`.

**Non-Goals:**
- Crear recordatorios, `enviar_recordatorios`, listado global de turnos por rango y segunda pasada de `failed` (C-12).
- Emails de cancelación o de cambio de horario del profesional (RN-NO-05, DD-68).
- Pantallas o endpoints para ver o reenviar emails.
- HTML, adjuntos, enlaces de confirmación o cancelación (DD-06).
- Elegir un proveedor SMTP de producción (SU-02 queda abierto).

## Decisiones pendientes (P-1 a P-9)

Cada pregunta en lenguaje simple, con opciones, la recomendada y por qué. **Todas confirmadas por el usuario con la opción A (recomendada).

### P-1 — ¿Con qué servidor SMTP se mandan los emails en desarrollo y en la demo? (SU-02) — CONFIRMADA (Mailpit)
**Resolución del usuario (2026-11-06)**: el servidor SMTP de desarrollo y de la demo es **Mailpit** (los emails se ven en http://localhost:8025). No se elige ningún proveedor externo ni se crea ninguna cuenta. El adaptador SMTP sigue configurable por las variables `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS` y `EMAIL_FROM`, así que más adelante se puede apuntar a cualquier otro servidor SMTP sin tocar el código. El proveedor de producción queda abierto (SU-02 sigue abierto para producción y no bloquea C-11 ni C-12). La comparación de proveedores que figuraba aquí se retiró.

### P-2 — ¿Cómo evitamos que la demo mande emails a personas reales? — CONFIRMADA (opción A)
Los pacientes del seed tienen emails `@example.com` (no existen) y en una demo alguien podría cargar un paciente con un email real de un tercero. `11_recordatorios_email.md` pide que los emails de pacientes ficticios no apunten a buzones de terceros reales.
- **A (recomendada)**: variable opcional `EMAIL_REDIRECT_TO`. Si tiene una dirección, todos los emails van a esa casilla con una línea "Email de demostración"; vacía, van al paciente. En desarrollo queda vacía (Mailpit atrapa todo).
- B: lista de dominios permitidos; un email a otro dominio queda `failed`.
- C: nada: se confía en cargar solo emails del equipo.
**Por qué A**: con una sola variable la demo es segura aunque se carguen pacientes inventados. B obliga a mantener una lista; C depende de que nadie se equivoque.

### P-3 — ¿Cómo sabe la tarea de cada 10 minutos qué pendientes son "viejas"? — CONFIRMADA (opción A)
La KB dice que `reencolar_pendientes` toma las `pending` "con más de unos minutos", pero la tabla no guarda cuándo se creó cada fila.
- **A (recomendada)**: una migración chica agrega la columna `created_at` (con la hora de inserción) y un índice; la tarea toma las `pending` creadas hace más de 5 minutos, hasta 100 por pasada.
- B: sin migración: la tarea reencola **todas** las `pending` cada 10 minutos, incluidas las recién creadas.
**Por qué A**: hace exactamente lo que dice la KB y evita encolar dos veces lo que ya está en camino. Con B no se mandarían dos emails (el envío es idempotente), pero cada 10 minutos se duplicarían tareas y no se podría distinguir una pendiente trabada de una nueva. Costo de A: una migración reversible sobre una tabla de datos ficticios.

### P-4 — ¿Qué pasa con los avisos de turnos que ya pasaron? — CONFIRMADA (opción A)
Desde C-08 se acumularon confirmaciones `pending` que nadie envió (DD-62), y en el futuro un Redis caído varios días puede dejar pendientes de turnos ya ocurridos.
- **A (recomendada)**: al procesar una pendiente cuyo turno ya empezó (o que ya no está agendado) no se envía nada y se marca `failed` con el error `EXPIRED`. Las pendientes de turnos futuros acumuladas desde C-08 se envían normalmente.
- B: una migración de datos borra todas las `pending` existentes al instalar C-11 (y para el futuro, igual que A).
- C: se envían todas, aunque el turno haya pasado.
**Por qué A**: una sola regla cubre las acumuladas y las futuras, no hace falta tocar datos a mano y queda rastro de qué no se envió. C mandaría "Tu turno quedó agendado" para un turno de ayer; B borra historial y sigue necesitando la regla de A.

### P-5 — Si un envío falla, ¿se reintenta? — CONFIRMADA (opción A)
`11_recordatorios_email.md` deja la política de reintentos "a confirmar en la implementación".
- **A (recomendada)**: los fallos temporales (servidor caído, sin respuesta, "probá más tarde") se reintentan solos, hasta 3 intentos con esperas de 1 y 2 minutos; los permanentes (dirección rechazada, credenciales malas) quedan `failed` al instante. Una `failed` no se reintenta en C-11 (la segunda pasada diaria la decide C-12).
- B: sin reintentos: cualquier fallo queda `failed`.
- C: además de A, `reencolar_pendientes` también vuelve a intentar las `failed`.
**Por qué A**: un corte de unos segundos del proveedor no debería dejar a un paciente sin confirmación, y no tiene sentido insistir con una dirección rechazada. C podría mandar cada 10 minutos el mismo email a una casilla que rebota y gastar el cupo diario. Nota: el Flujo 2 de `07_flujos_principales.md` dice que `reencolar_pendientes` "reintenta" una notificación `failed`; con A se corrige el Flujo 2 para que diga solo `pending` (hallazgo 1 de la revisión).

### P-6 — ¿Qué dice el email? (pregunta abierta de `10_preguntas_abiertas.md`) — CONFIRMADA (opción A)
La KB pide como mínimo paciente, profesional, fecha y hora y dirección; el roadmap suma teléfono; la pregunta "¿el recordatorio debe incluir dirección, teléfono u otra información?" está abierta.
- **A (recomendada)**: texto plano (sin diseño HTML) con: saludo con el nombre del paciente, fecha y hora en la hora del consultorio escrita completa ("lunes 9 de noviembre de 2026, 10:00 h"), profesional, nombre, dirección y teléfono del consultorio (si tiene) y la aclaración "Este email es informativo: para cambiar o cancelar el turno comunicate con el consultorio". Al reprogramar se manda el mismo texto con el horario nuevo ("Tu turno quedó agendado"). El recordatorio cambia el asunto y dice "Te recordamos tu turno", sin "mañana". Textos exactos en la spec `email-templates`.
- B: igual que A pero con una versión HTML con formato además del texto plano.
- C: igual que A pero al reprogramar dice "Tu turno fue reprogramado" (hay que detectar que hubo un horario anterior).
**Por qué A**: el texto plano se lee bien en cualquier casilla, se prueba fácil y no tiene datos sensibles; B suma plantillas y pruebas sin cambiar lo que el paciente entiende. C es más claro para el paciente, pero obliga a buscar el historial del turno al enviar; queda como mejora posterior.

### P-7 — Un turno que vuelve a un horario que ya tuvo, ¿recibe otra confirmación? — CONFIRMADA (opción A)
Ya decidido en C-08 (DD-62): si un turno se mueve de las 10:00 (confirmación ya enviada) a las 11:00 y después vuelve a las 10:00, **no** se manda otra confirmación, porque la base no admite dos confirmaciones del mismo turno y horario. Con C-11 eso se nota: el último email que recibió el paciente dice 11:00, pero el turno es a las 10:00.
- **A (recomendada)**: mantener DD-62 (caso raro; recepción avisa por teléfono). Se documenta en el riesgo y en DD.
- B: al volver a un horario ya confirmado, borrar la confirmación vieja y crear una nueva `pending` (se pierde ese historial, cambia la regla de C-08 y su spec).
**Por qué A**: no toca la agenda ya archivada ni la base, y es un caso muy poco frecuente; B cambia escenarios archivados de C-08 por un borde.

### P-8 — ¿La pantalla avisa que se manda un email? — CONFIRMADA (opción A)
C-10 dejó el aviso "Turno agendado: Perez, Juan, Lun 09/11 10:00" sin mencionar emails y anotó que C-11 podía sumarlo.
- **A (recomendada)**: los avisos de agendar y reprogramar terminan con "Se enviará la confirmación por email al paciente." (futuro: el envío es posterior y lo hace el servidor). Sin mostrar la dirección.
- B: no tocar el frontend en C-11.
**Por qué A**: recepción sabe que el paciente va a recibir algo y puede decírselo; es un cambio de dos textos y sus tests. B deja el frontend fuera del change si se prefiere un C-11 solo de backend.

### P-9 — ¿Un change o dos? — CONFIRMADA (opción A)
El change tiene 13 grupos y unas 50 tareas, parecido a C-08.
- **A (recomendada)**: un solo change por grupos, con un **punto de corte seguro tras el grupo 8** (envío de punta a punta funcionando: agendar → cola → worker → Mailpit). Los grupos 9 a 12 (migración y reencolado, frontend, KB) completan el resto.
- B: partir en C-11a (envío: grupos 1 a 8) y C-11b (reencolado con migración, frontend y KB).
**Por qué A**: las specs y la KB se cierran juntas y C-12 recibe un solo archivo; el punto de corte da la misma seguridad que partirlo. B suma un ciclo de propose/archive y deja RN-NO-04 a medias (sin reencolado, un Redis caído pierde la confirmación hasta C-11b).

## Decisiones técnicas

### D-1 — Capas y ubicación
- `app/domain/notifications/` (nuevo, solo librería estándar): `types.py` (`OutgoingEmail` con destinatario, asunto y cuerpo; `DeliveryDecision`: `SEND`, `SKIP`, `EXPIRE`; `DeliveryOutcome`: `SENT`, `SKIPPED`, `EXPIRED`, `FAILED`, `RETRY`), `ports.py` (`EmailSender.send(email: OutgoingEmail) -> None`), `errors.py` (`EmailSendError(temporary: bool, code: str)`), `rules.py` (`decide_delivery`, `sanitize_error`).
- `app/application/notifications.py` (nuevo): `NotificationDeps`, `deliver_notification`, `requeue_pending`.
- `app/infrastructure/email/`: `smtp.py` (`SmtpEmailSender`), `templates.py` (plantillas puras), `redirect.py` (envoltorio de redirección, P-2).
- `app/infrastructure/tasks/`: `celery_app.py` (tareas incluidas y Beat), `notifications.py` (tareas `enviar_email` y `reencolar_pendientes`), `dispatcher.py` (`CeleryNotificationDispatcher`), `wiring.py` (arma `NotificationDeps` para el worker).
- El puerto `NotificationRepository` sigue en `app/domain/appointments/ports.py` (ya existe ahí) y se amplía.
- Alternativa descartada: plantillas en `domain/`. La KB (`08_arquitectura_propuesta.md`) ubica las plantillas en `infrastructure/email/`; igual son funciones puras sin I/O.

### D-2 — Decisión pura de envío
`decide_delivery(notification, appointment, now) -> DeliveryDecision`: `SKIP` si la notificación no está `pending` o su `appointment_starts_at` difiere del inicio del turno; `EXPIRE` si el turno no está `scheduled` o `starts_at <= now` (P-4); `SEND` en otro caso. La ausencia de fila o de turno se resuelve antes (`SKIP`). Recibe `now` como dato, igual que el resto del dominio.

### D-3 — Toma con bloqueo durante el envío
Nueva unidad de trabajo de envío (`NotificationSendUnitOfWork`, puerto en `domain/appointments/ports.py`, implementaciones en memoria y PostgreSQL con una sesión compartida, como la de C-08). Dentro de una sola transacción: `claim_pending(id)` hace `SELECT … FOR UPDATE SKIP LOCKED` sobre la fila `pending`; se leen turno, paciente, profesional y configuración; se envía por SMTP; se marca `sent` o `failed`; se confirma. Si otra transacción ya la tomó, `claim_pending` devuelve nada y la tarea termina sin enviar (idempotencia ante entregas dobles).
- Consecuencia: mientras dura el envío (a lo sumo el timeout SMTP), cancelar o reprogramar ese turno espera al borrar la `pending` (no falla). Si el worker se cae después de que el SMTP aceptó el mensaje y antes del commit, la fila sigue `pending` y podría enviarse otra vez (entrega "al menos una vez" en ese caso extremo; riesgo aceptado).
- Alternativas: marcar con `UPDATE … WHERE status = 'pending'` después de enviar (dos workers podrían mandar dos emails); estado nuevo `sending` (migración del enumerado y filas trabadas si el worker muere).

### D-4 — Reintentos
`deliver_notification(deps, notification_id, *, attempt, max_attempts=3)`. Fallo permanente → `failed` y `FAILED`. Fallo temporal con `attempt < max_attempts` → la transacción se revierte (la fila sigue `pending`) y devuelve `RETRY`; la tarea Celery llama a `self.retry(countdown=60 * 2 ** (attempt - 1))` (1 y 2 minutos). Temporal en el último intento → `failed`. El texto de `error` sale de `sanitize_error`: `SMTP_PERMANENT <código>`, `SMTP_TEMPORARY <código|CONNECTION|TIMEOUT>`, `EXPIRED`; nunca el texto del servidor (que puede repetir la dirección).

### D-5 — Plantillas
Funciones puras `render_confirmation(data) -> (asunto, cuerpo)` y `render_reminder(data)`; `data` lleva nombre y apellido del paciente, nombre a mostrar del profesional, `starts_at` en UTC, zona, nombre, dirección y teléfono del consultorio. Días y meses en castellano con tablas propias (sin `locale`, que depende del sistema operativo del contenedor). Hora con `to_local` de `app/core/timezone.py`.

### D-6 — Adaptador SMTP
`smtplib.SMTP(host, port, timeout=10)`; `starttls()` si `SMTP_USE_TLS`; `login()` solo con `SMTP_USER`; `email.message.EmailMessage` con `set_content(cuerpo)` (UTF-8). Traducción de errores: `SMTPResponseException` con código 4xx → temporal, 5xx → permanente; `SMTPAuthenticationError` → permanente; `OSError`/`TimeoutError`/`SMTPServerDisconnected` → temporal. Sin dependencias nuevas (`aiosmtplib` no hace falta: el worker es síncrono).

### D-7 — Tareas y Beat
- `enviar_email(notification_id: str)`: `bind=True`, `name="enviar_email"`, serializador JSON, solo el id como argumento. Arma `NotificationDeps` con `wiring.py`. Un id mal formado o inexistente termina `SKIPPED` sin reintentar.
- `reencolar_pendientes()`: `requeue_pending(deps, now)` lista las `pending` creadas antes de `now - 5 min` (tope 100, más antiguas primero) y publica `enviar_email` por cada una con `apply_async(retry=False)`. Registra solo la cantidad.
- `beat_schedule = {"reencolar-pendientes": {"task": "reencolar_pendientes", "schedule": 600.0}}`.
- Publicación: `apply_async(args=[id], retry=False)` y `broker_transport_options = {"socket_connect_timeout": 2}`; con Redis caído `apply_async` lanza `kombu.exceptions.OperationalError` rápido y el despachador lo atrapa.
- **Consultado con Context7** (`/websites/celeryq_dev_en_stable`, 2026-11-06): `apply_async(..., retry=False)` desactiva el reintento de publicación ante fallos de conexión y `apply_async` lanza `kombu.exceptions.OperationalError` si no puede conectarse; `broker_connection_timeout` **solo aplica al worker**, no al productor, y para el productor hay que usar `broker_transport_options` (influyó en D-7: el timeout corto va en `broker_transport_options`); `task_always_eager` y `task_eager_propagates` ejecutan las tareas en el mismo proceso y propagan excepciones (base de los tests de tareas, D-11); reintentos con `autoretry_for`/`retry_backoff` o `self.retry` (se eligió `self.retry` con espera explícita porque la clasificación temporal/permanente la hace el caso de uso, no el tipo de excepción).

### D-8 — Despachador real
`CeleryNotificationDispatcher(publish)` en `infrastructure/tasks/dispatcher.py`, donde `publish(notification_id)` es `enviar_email.apply_async(args=[id], retry=False)`. Publica una por una con `try/except` propio (si una falla se registra el id del turno y la clase del error, y sigue con la siguiente). `get_agenda_deps` lo inyecta en lugar del `NoOp`; `NoOpNotificationDispatcher` queda solo como doble de tests. El `_dispatch` de C-08 no cambia (sigue siendo la segunda red).

### D-9 — Migración `0002` (P-3 = A)
`0002_notifications_created_at`: `ADD COLUMN created_at timestamptz NOT NULL DEFAULT now()` (las filas existentes reciben el instante de la migración) e índice parcial `ix_email_notifications_pending_created_at (created_at) WHERE status = 'pending'`. `downgrade` quita índice y columna. Se actualiza `EmailNotificationModel` (el test "modelos y migración coinciden" lo controla). El tipo de dominio `Notification` no cambia; `created_at` solo lo usa el repositorio al listar pendientes antiguas (en memoria se guarda aparte con un reloj inyectable).

### D-10 — Configuración
- `ClinicSettings` suma `clinic_name: str = "Consultorio"`, `address: str = ""`, `phone: str | None = None`, `reminder_send_hour: int = 9` (campos con valor por defecto al final: los usos actuales no cambian). Los repositorios en memoria y PostgreSQL los devuelven.
- `Settings.EMAIL_REDIRECT_TO: str = ""` validado con `is_valid_email` cuando no está vacío, con `hide_input_in_errors` (no repite el valor). `.env.example` suma `EMAIL_REDIRECT_TO=` vacío.
- Docker Compose: `worker.depends_on` suma `db: service_healthy`.

### D-11 — Estrategia de tests
- Unitarios puros: `decide_delivery`, `sanitize_error`, plantillas (texto exacto, medianoche, sin teléfono, sin datos sensibles).
- Casos de uso con repositorios en memoria, reloj fijo y `FakeEmailSender` (guarda los mensajes; se le puede pedir que falle temporal o permanentemente).
- Batería de contrato de notificaciones ampliada (memoria + PostgreSQL con `-m integration`), incluida la toma simultánea con dos sesiones (`SKIP LOCKED`).
- Tareas con la app Celery en modo inmediato (`task_always_eager = True`, `task_eager_propagates = True`) y el remitente falso.
- Despachador con un `publish` que lanza `OperationalError` (Redis caído) y test de API: agendar responde 201 y la `pending` queda.
- Integración en el contenedor (`-m integration`): SMTP real contra Mailpit (se consulta su API HTTP `GET http://mailpit:8025/api/v1/messages`), Redis caído simulado con una URL a un puerto sin servicio midiendo que agendar responde en menos de 5 segundos, y la prueba de punta a punta del grupo 8.

### D-12 — Registros
El worker registra `notification_id`, `appointment_id`, `kind` y el resultado (`SENT`, `SKIPPED`, `EXPIRED`, `FAILED`, `RETRY`); nunca destinatario, nombres ni texto del servidor (DD-77). `reencolar_pendientes` registra solo la cantidad.

## Risks / Trade-offs

- [Worker caído después de que el SMTP aceptó y antes del commit] → la fila sigue `pending` y puede salir un segundo email. Se acepta (muy raro; datos ficticios); evitarlo exige un estado intermedio y su recuperación.
- [El bloqueo durante el envío demora cancelar o reprogramar ese turno hasta 10 segundos] → solo si coincide con el envío de ese mismo turno; la operación espera y termina bien.
- [Proveedor SMTP de producción sin elegir] → el código solo depende de las variables `SMTP_*`; la demo y el desarrollo usan Mailpit (SU-02 abierto para producción).
- [P-7 = A: el paciente que vuelve a su horario original no recibe confirmación nueva] → recepción avisa por teléfono; se documenta.
- [Cancelar no avisa al paciente aunque ya recibió la confirmación] → es lo que dice RN-NO-05 ("uno cancelado no genera ninguna"); se deja anotado como mejora posterior.
- [Credenciales SMTP reales] → solo en `.env` local, `SecretStr`, nunca en registros ni en el frontend (regla dura 5, RN-PR-03).
- [Timeout de conexión de 2 segundos con Redis lento pero vivo] → la publicación podría fallar y la confirmación saldría hasta 15 minutos más tarde por el reencolado; aceptable para un aviso informativo.
- [Tamaño del change (~50 tareas)] → punto de corte seguro tras el grupo 8 (P-9).

## Migration Plan

1. Aplicar `alembic upgrade head` (migración `0002`, P-3 = A); las `pending` de C-08 quedan con `created_at` del momento.
2. Reconstruir la imagen del backend y levantar `api`, `worker` y `beat`. A los 10 minutos la primera pasada de `reencolar_pendientes` toma las `pending` acumuladas: las de turnos futuros se envían y las de turnos pasados quedan `failed` con `EXPIRED` (P-4 = A).
3. La demo usa Mailpit: los emails se ven en http://localhost:8025. Apuntar a otro servidor SMTP es cambiar las variables `SMTP_*` y `EMAIL_FROM`.
4. Reversión: volver a inyectar `NoOpNotificationDispatcher`, detener `worker` y `beat` y `alembic downgrade -1`; las filas `sent`/`failed` quedan como historial (datos ficticios).

## Open Questions

Ninguna diferible: P-1 a P-9 están arriba y quedaron confirmadas (opción A).

## Revisión de escenarios (skill `revisor-escenarios-turnos`, 2026-11-06)

### Resumen
64 escenarios revisados (62 nuevos o modificados en este change), 14 hallazgos (3 ambigüedades, 3 bordes faltantes, 0 reglas solapadas, 2 preguntas abiertas, 3 sin respaldo, 2 contrato incompleto, 1 contradicción). Todos quedaron cubiertos en las specs con la opción sugerida, confirmada (P-n), o como decisión técnica.

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Contradicción | "Enviadas y fallidas no se tocan" | El Flujo 2 dice que una notificación `failed` o `pending` la reintenta `reencolar_pendientes`; `11_recordatorios_email.md` dice que solo reencola las `pending` | `07_flujos_principales.md` Flujo 2 (casos de error); `11_recordatorios_email.md` §Envío asincrónico y §Idempotencia y errores | Solo `pending`; corregir el Flujo 2 (P-5) |
| 2 | Contrato incompleto | "Pendiente recién creada" | La tabla no tiene `created_at` y la KB pide reencolar las de "más de unos minutos" | `04_modelo_de_datos.md` (`email_notifications`); `11_recordatorios_email.md` §Envío asincrónico | Migración con `created_at` (P-3) |
| 3 | Contrato incompleto | Plantillas con datos del consultorio | El puerto de configuración solo expone slot, zona y anticipación | spec `clinic-settings-repository`; `04_modelo_de_datos.md` (`clinic_settings`); entrada C-11 de `CHANGES.md` | Ampliar `ClinicSettings` (técnico, D-10) |
| 4 | Borde faltante | "Pendiente acumulada de un turno pasado" | Nada dice qué hacer con una `pending` cuyo turno ya ocurrió | DD-62 (deja la decisión a C-11); sin respaldo en la KB para la regla | No enviar y marcar `failed` `EXPIRED` (P-4) |
| 5 | Borde faltante | Volver a un horario ya confirmado | El paciente queda con un email que dice otro horario | DD-62 (consecuencia aceptada), RN-NO-03 | Mantener DD-62 (P-7) |
| 6 | Borde faltante | "Dos entregas a la vez", "Cancelar mientras se envía" | La KB pide idempotencia ante reentregas pero no dice cómo convive con cancelar | `11_recordatorios_email.md` §Envío asincrónico; RN-NO-04, RN-NO-05 | Bloqueo de la fila durante el envío (técnico, D-3) |
| 7 | Pregunta abierta | Plantillas de confirmación y recordatorio | "¿El recordatorio debe incluir dirección, teléfono u otra información?" sin responder | `10_preguntas_abiertas.md` (prioridad Media, decisor Dueño) | Texto de la spec `email-templates` (P-6) |
| 8 | Pregunta abierta | Envío real en la demo | Proveedor SMTP sin elegir | SU-02; `10_preguntas_abiertas.md` (prioridad Alta) | Mailpit en desarrollo y demo, adaptador configurable (P-1) |
| 9 | Sin respaldo | "Fallo temporal que se recupera" | La política de reintentos está "a confirmar" | `11_recordatorios_email.md` §Idempotencia y errores | 3 intentos solo para fallos temporales (P-5) |
| 10 | Sin respaldo | "Demo con redirección" | La KB pide no escribir a buzones de terceros pero no dice cómo | `11_recordatorios_email.md` §Límites y riesgos; seed con `@example.com` (`04_modelo_de_datos.md`) | `EMAIL_REDIRECT_TO` (P-2) |
| 11 | Sin respaldo | Avisos de pantalla | C-10 dejó explícito "el aviso no menciona emails" y la KB no dice si la pantalla debe avisar | Nota de C-10 en `CHANGES.md`; spec `frontend-appointment-management` | Sumar "Se enviará la confirmación…" (P-8) |
| 12 | Ambigüedad | "Paciente que cambió su nombre después de agendar" | ¿Datos al registrar o al enviar? DD-73 dice que cambiar el email "no toca notificaciones ya registradas" | DD-73 (`09_decisiones_y_supuestos.md`) | Datos vigentes al enviar: la fila no guarda destinatario, así que no se "toca" nada (técnico; se aclara en DD) |
| 13 | Ambigüedad | Reprogramar y recordatorio | El roadmap dice "reprogramar reemplaza el recordatorio pendiente", pero los recordatorios los crea C-12 | RN-NO-05; entrada C-11 de `CHANGES.md`; spec `notification-registration` (C-08 ya borra las `pending` de cualquier tipo del horario anterior) | Cubierto: C-08 ya borra y el envío descarta horarios que no coinciden (D-2); sin trabajo nuevo |
| 14 | Ambigüedad | Mismo texto al agendar y reprogramar | RN-NO-05 pide notificación nueva al reprogramar, pero no dice si el texto distingue | RN-NO-05; `11_recordatorios_email.md` §Tipos de email | Mismo texto con el horario vigente (P-6) |

### Escenarios sin hallazgos
Envío a Mailpit, STARTTLS y autenticación, acentos, clasificación de fallos, errores sin datos personales, confirmación enviada, recordatorio enviado, paciente desactivado con turno vigente (DD-76), notificación ya enviada o borrada, horario que no coincide, turno cerca de la medianoche (RN-GL-01, SU-01 sin horario de verano), tareas registradas, programación de Beat, Redis caído al agendar y reprogramar (RN-NO-04), cancelar no publica (RN-NO-05), inventario de rutas sin cambios (regla dura 4), configuración del consultorio, migración reversible.

Cada requirement tiene escenarios esperados, de error de negocio y de borde. No se inventaron estados de notificación: `EXPIRED` es un texto de `error` con el estado `failed` que ya existe en `04_modelo_de_datos.md`; la única columna nueva es `created_at` y depende de P-3.

### Decisiones que necesitan al usuario
P-1 a P-9 (arriba): confirmadas por el usuario y registradas como DD-87 a DD-95 en la KB.
