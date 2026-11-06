# Tasks: email-confirmation-infra (C-11)

> **Gobernanza ALTA.** Grupo 0 cerrado (confirmaciones P-1 a P-9 de `design.md`). Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso (TRIANGULATE) y refactor con los tests en verde (REFACTOR). Los tests de integración corren en el contenedor (`pytest -m integration`). No editar `.env`; `.env.example` solo suma `EMAIL_REDIRECT_TO=` vacío (sin valores reales). `domain/` sin imports de FastAPI, SQLAlchemy, Celery ni Redis; type hints en todo. Ningún dato de paciente en registros, errores guardados ni mensajes de la cola. Todo cambio en la agenda conserva su test de no superposición (regla dura 6). Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`. Cada task indica **Verifica:** cómo se comprueba.

## 0. Confirmaciones del usuario (CONFIRMADAS, opción A en P-1 a P-9)

- [x] 0.1 Obtener respuesta a P-1 (servidor SMTP de desarrollo y demo: Mailpit, SU-02) y P-2 (redirección de destinatarios) y marcarlas CONFIRMADAS en `design.md`; si P-2 ≠ A, ajustar el requirement "Redirección de destinatarios para la demo" de `email-sending` y la task 7.5 con `/opsx:update`. **Verifica:** `design.md` sin "PENDIENTE" en P-1 y P-2
- [x] 0.2 Obtener respuesta a P-3 (antigüedad de las pendientes), P-4 (avisos de turnos pasados) y P-5 (reintentos) y marcarlas CONFIRMADAS; si P-3 = B, quitar la spec delta `database-schema` y la task 9.1; si P-4 = B, sumar una migración de datos al grupo 9. **Verifica:** `design.md` sin "PENDIENTE" en P-3 a P-5
- [x] 0.3 Obtener respuesta a P-6 (texto de los emails), P-7 (volver a un horario ya confirmado) y P-8 (aviso en pantalla) y marcarlas CONFIRMADAS; si P-8 = B, quitar la spec delta `frontend-appointment-management` y el grupo 10. **Verifica:** `design.md` sin "PENDIENTE" en P-6 a P-8
- [x] 0.4 Obtener respuesta a P-9 (un change o dos); si es B, partir con `/opsx:update` entre los grupos 8 y 9. **Verifica:** `design.md` sin "PENDIENTE" en P-9
- [x] 0.5 Si alguna respuesta difiere de la recomendación, ajustar specs, design y tasks; quitar las marcas "pendiente de confirmación" de las specs. **Verifica:** `openspec validate email-confirmation-infra --strict` en verde

## 1. Preparación y línea base

- [x] 1.1 Safety net: correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/`, `ruff check`, y en `frontend/` `npm test`, `npx tsc --noEmit` y `npx eslint .`; anotar los números (C-09 dejó 1349 por defecto y 279 de integración; C-10, 379 de frontend). **Verifica:** todo en verde; si algo falla, frenar y reportarlo como falla previa

## 2. Dominio puro de notificaciones — specs notification-sending y email-sending

- [x] 2.1 RED: `tests/unit/domain/notifications/test_delivery_rules.py`: `decide_delivery` devuelve `SEND` (pendiente, horario igual, turno `scheduled` futuro), `SKIP` (`sent`, `failed`, horario distinto), `EXPIRE` (turno empieza justo ahora, ya empezó, `completed`, `cancelled`); ver que falla. **Verifica:** el test falla por falta del módulo
- [x] 2.2 GREEN → TRIANGULATE → REFACTOR: `app/domain/notifications/types.py` y `rules.py`; segundo caso por decisión con otro horario y otra zona de entrada. **Verifica:** tests en verde y `tests/unit/test_architecture.py` en verde
- [x] 2.3 RED → GREEN → TRIANGULATE: `sanitize_error` y `EmailSendError`: 550 con la dirección en el texto → `SMTP_PERMANENT 550` sin la dirección; 451 → `SMTP_TEMPORARY 451`; conexión → `SMTP_TEMPORARY CONNECTION`; timeout → `SMTP_TEMPORARY TIMEOUT`; nunca más de 200 caracteres. **Verifica:** tests en verde; ningún caso contiene `@`
- [x] 2.4 Puerto `EmailSender` en `app/domain/notifications/ports.py` y `FakeEmailSender` de tests (guarda mensajes; falla temporal o permanente a pedido) en `tests/` con su propio test. **Verifica:** `mypy --strict app/ tests/` limpio

## 3. Plantillas — spec email-templates

- [x] 3.1 RED: `tests/unit/infrastructure/email/test_templates.py` con los escenarios de "Email de confirmación" (texto exacto del asunto y orden del cuerpo, sin teléfono, medianoche UTC → `lunes 9 de noviembre de 2026, 23:30 h`, datos vigentes, sin documento, teléfono del paciente ni nacimiento); ver que falla. **Verifica:** el test falla por falta del módulo
- [x] 3.2 GREEN → TRIANGULATE → REFACTOR: `app/infrastructure/email/templates.py` con tablas propias de días y meses y `to_local`; segundo caso con otro día de la semana y otro mes. **Verifica:** tests en verde
- [x] 3.3 RED → GREEN: "Email de recordatorio" (asunto, "Te recordamos tu turno.", sin "mañana" ni "24 horas") y tipo desconocido rechazado. **Verifica:** tests en verde

## 4. Datos del consultorio — spec clinic-settings-repository

- [x] 4.1 Safety net: correr `tests/contract/test_clinic_settings_repository.py` (memoria y PostgreSQL) y anotar el número. **Verifica:** en verde antes de tocar nada
- [x] 4.2 RED: sumar a la batería de contrato los escenarios "Valores por defecto" ampliado, "Datos del consultorio para los emails" y "Consultorio sin teléfono"; ver que fallan. **Verifica:** fallan en memoria y en PostgreSQL
- [x] 4.3 GREEN → REFACTOR: `ClinicSettings` con `clinic_name`, `address`, `phone`, `reminder_send_hour` (con valor por defecto, D-10) y los dos repositorios. **Verifica:** batería en verde con `-m integration`; tests de agenda de C-05b a C-10 sin cambios y en verde

## 5. Registro de notificaciones y unidad de trabajo de envío — spec notification-registration

- [x] 5.1 Safety net: correr `tests/contract/test_notification_repository.py` y `tests/contract/test_agenda_unit_of_work.py` (memoria y PostgreSQL). **Verifica:** en verde y número anotado
- [x] 5.2 RED: escenarios nuevos del contrato: tomar una `pending` (y nada si no existe, si es `sent` o si es otro id), marcar `sent` con `sent_at`, marcar `failed` con error, marcar una que no está `pending` no la cambia; ver que fallan. **Verifica:** fallan en ambas implementaciones
- [x] 5.3 GREEN → TRIANGULATE → REFACTOR: puerto ampliado en `app/domain/appointments/ports.py`, `NotificationSendUnitOfWork` (D-3) en memoria y PostgreSQL con sesión compartida y `FOR UPDATE SKIP LOCKED`. **Verifica:** batería en verde con `-m integration`
- [x] 5.4 RED → GREEN: integración "Toma simultánea en PostgreSQL" con dos sesiones (la segunda no obtiene nada sin esperar; `lock_timeout` y `join(timeout)` para no colgar la suite). **Verifica:** test en verde 20 corridas seguidas

## 6. Caso de uso de envío (memoria) — spec notification-sending

- [x] 6.1 RED: `tests/unit/application/test_deliver_notification.py` con repositorios en memoria, reloj fijo y `FakeEmailSender`: confirmación enviada (`sent_at` = reloj), recordatorio enviado, paciente desactivado con turno vigente, ya enviada, borrada, horario distinto (sin enviar ni cambiar la fila); ver que fallan. **Verifica:** el test falla por falta del caso de uso
- [x] 6.2 GREEN → TRIANGULATE → REFACTOR: `app/application/notifications.py` con `NotificationDeps` y `deliver_notification` (D-2, D-3). **Verifica:** tests en verde; el turno no cambia en ningún caso
- [x] 6.3 RED → GREEN: avisos de turnos pasados o no vigentes (`EXPIRED`, sin email, sin `sent_at`) incluidas las acumuladas de C-08 pasadas y futuras (P-4). **Verifica:** tests en verde
- [x] 6.4 RED → GREEN → TRIANGULATE: fallos y reintentos (P-5): permanente → `failed` en un intento; temporal con intentos restantes → `RETRY` y la fila sigue `pending`; temporal en el tercero → `failed` con el último error; el turno sigue cancelable y reprogramable tras un fallo. **Verifica:** tests en verde
- [x] 6.5 Test de registros: con `caplog`, ningún registro del caso de uso contiene el email ni el apellido del paciente (D-12). **Verifica:** test en verde

## 7. Adaptador SMTP, redirección y configuración — spec email-sending

- [x] 7.1 RED: `tests/unit/infrastructure/email/test_smtp.py` con un `smtplib.SMTP` reemplazado por un doble: sin `SMTP_USER` no hay `login`; con `SMTP_USE_TLS` hay `starttls` antes de `login`; timeout 10 s; traducción de 550, 535, 451, `ConnectionRefusedError` y `TimeoutError` a fallos temporales o permanentes; ver que falla. **Verifica:** el test falla por falta del adaptador
- [x] 7.2 GREEN → TRIANGULATE → REFACTOR: `app/infrastructure/email/smtp.py` (D-6) con `EmailMessage` UTF-8. **Verifica:** tests en verde y `mypy --strict` limpio
- [x] 7.3 RED → GREEN: el adaptador nunca escribe `SMTP_PASSWORD` ni `SMTP_USER` en errores ni registros (escenario "Fallo de autenticación"). **Verifica:** test en verde
- [x] 7.4 RED → GREEN: `EMAIL_REDIRECT_TO` en `app/core/config.py` (vacía por defecto; inválida falla nombrando la variable sin repetir el valor) y `.env.example` con `EMAIL_REDIRECT_TO=` vacío. **Verifica:** `tests/unit/core/test_config.py` y `tests/unit/test_env_example.py` en verde
- [x] 7.5 RED → GREEN: envoltorio de redirección (P-2): con dirección, todo va ahí con la línea de demostración y sin la dirección original; vacía, va al paciente. **Verifica:** tests en verde
- [x] 7.6 Integración (`-m integration`): envío real a Mailpit (`mailpit:1025`) y lectura por su API HTTP: remitente, destinatario, asunto, acentos y eñes intactos; servidor sin escuchar → fallo temporal. **Verifica:** test en verde en el contenedor

## 8. Tareas Celery, despachador y envío de punta a punta — specs notification-tasks, notification-registration y local-environment

- [x] 8.1 RED: `tests/unit/infrastructure/test_celery_app.py` cambia "sin tareas de negocio" por "las únicas tareas propias son `enviar_email` y `reencolar_pendientes`" y suma `broker_transport_options` con `socket_connect_timeout <= 2`; ver que falla. **Verifica:** el test falla
- [x] 8.2 GREEN: `app/infrastructure/tasks/notifications.py` con `enviar_email` (solo id; `self.retry` con 1 y 2 minutos ante `RETRY`; id inexistente o mal formado termina sin reintentar) y `wiring.py`; `reencolar_pendientes` registrada con un cuerpo mínimo que se completa en el grupo 9. **Verifica:** tests en verde
- [x] 8.3 RED → GREEN: tareas en modo inmediato (`task_always_eager`, `task_eager_propagates`) con `FakeEmailSender`: éxito → `sent`; fallo permanente → `failed`; temporal → reintento; doble ejecución de la misma tarea → un solo mensaje (idempotencia por `UNIQUE` y toma). **Verifica:** tests en verde
- [x] 8.4 RED → GREEN: el mensaje publicado de `enviar_email` lleva solo el id (sin email ni apellido). **Verifica:** test en verde
- [x] 8.5 RED → GREEN → TRIANGULATE: `CeleryNotificationDispatcher` (D-8): publica una tarea por notificación con `retry=False`; si `publish` lanza `OperationalError`, registra el id del turno y la clase del error y sigue con la siguiente. **Verifica:** tests en verde
- [x] 8.6 RED → GREEN: `get_agenda_deps` inyecta el despachador real; tests de API: agendar con Redis caído (publicación que falla) responde 201 y la `pending` queda; reprogramar con Redis caído responde 200; agendar rechazado y cancelar no publican. **Verifica:** tests en verde; `tests/unit/api/test_route_inventory.py` y todos los `*_permissions.py` sin cambios y en verde (regla dura 4)
- [x] 8.7 Test de no superposición: agendar dos veces el mismo horario con el despachador real sigue dando `SLOT_TAKEN` y publica una sola tarea (regla dura 6). **Verifica:** test en verde
- [x] 8.8 `docker-compose.yml`: `worker` con `depends_on: db: service_healthy` además de `redis`. **Verifica:** `docker compose config` válido y `docker compose up` deja `worker` listo con las dos tareas en su log
- [x] 8.9 Integración de punta a punta (`-m integration`): con PostgreSQL, Redis, worker y Mailpit del entorno, agendar un turno futuro de un paciente del seed → la confirmación llega a Mailpit en pocos segundos y la fila queda `sent`; con Redis a una URL sin servicio, agendar responde 201 en menos de 5 segundos y la fila queda `pending`. **Verifica:** tests en verde en el contenedor
- [x] 8.10 **Punto de corte seguro (P-9)**: correr toda la batería (por defecto, integración, `mypy --strict app/`, `ruff check`). **Verifica:** todo en verde; el envío funciona sin el grupo 9

## 9. Migración y reencolado de pendientes — specs database-schema, notification-registration, notification-sending y notification-tasks

- [x] 9.1 RED: `tests/integration/db/test_migration.py` suma la migración `0002` (aplicar sobre filas existentes, valor por defecto, revertir y volver a aplicar) y el test de modelos y migración incluye `created_at` y el índice parcial; ver que falla. **Verifica:** fallan con `-m integration`
- [x] 9.2 GREEN: `alembic/versions/0002_notifications_created_at.py` y `EmailNotificationModel` (D-9). **Verifica:** tests de migración en verde; `alembic upgrade head` y `alembic downgrade -1` sin errores
- [x] 9.3 RED → GREEN → TRIANGULATE: contrato "Pendientes antiguas con tope" (memoria con reloj inyectable y PostgreSQL): solo `pending`, creadas antes del instante, más antiguas primero, con tope. **Verifica:** batería en verde con `-m integration`
- [x] 9.4 RED → GREEN: `requeue_pending` en `app/application/notifications.py`: 20 minutos → se pide; 1 minuto → no; `sent`/`failed` → no; 150 → 100 más antiguas; registra solo la cantidad. **Verifica:** tests en verde
- [x] 9.5 RED → GREEN: `reencolar_pendientes` completa y `beat_schedule` con una sola entrada propia cada 600 segundos; en modo inmediato, reencolar algo que ya estaba en la cola produce un solo email. **Verifica:** tests en verde
- [x] 9.6 Integración: con el `worker` detenido se agenda; al volver a levantarlo y correr una pasada (o esperar a Beat) el email sale (escenario "Worker detenido"). **Verifica:** test o comprobación documentada en el contenedor con la fila `sent`

## 10. Avisos en pantalla — spec frontend-appointment-management (P-8)

- [x] 10.1 Safety net: `npm test` en `frontend/` y número anotado. **Verifica:** en verde
- [x] 10.2 RED → GREEN: `src/appointments/messages.ts`: `bookedNotice` y `rescheduledNotice` terminan con "Se enviará la confirmación por email al paciente."; actualizar los tests de mensajes y de los flujos de agendar y reprogramar; el aviso no contiene el email del paciente. **Verifica:** `npm test`, `npx tsc --noEmit` y `npx eslint .` en verde

## 11. KB, roadmap y documentación

- [x] 11.1 Registrar P-1 a P-9 confirmadas como DD-87 en adelante en `knowledge-base/09_decisiones_y_supuestos.md`; dejar SU-02 abierto solo para producción (la demo usa Mailpit). **Verifica:** los códigos citados existen y no repiten números
- [x] 11.2 `knowledge-base/10_preguntas_abiertas.md`: SU-02 y "¿El recordatorio debe incluir dirección, teléfono…?" pasan a resueltas; `07_flujos_principales.md` Flujo 2: `reencolar_pendientes` reintenta solo las `pending` (hallazgo 1); `11_recordatorios_email.md`: reintentos, `EXPIRED`, `created_at` y `EMAIL_REDIRECT_TO`; `04_modelo_de_datos.md`: `created_at`; `08_arquitectura_propuesta.md`: `EMAIL_REDIRECT_TO`. **Verifica:** relectura de cada sección contra las specs
- [x] 11.3 `CHANGES.md`: entrada C-11 con el estado y lo que C-12 recibe hecho (plantilla `reminder`, envío genérico, `reminder_send_hour` en `ClinicSettings`, `failed` sin segunda pasada); `README.md`: cómo ver los emails en Mailpit y que el adaptador se configura por variables `SMTP_*` sin versionar credenciales. **Verifica:** relectura; `git status` no muestra `.env`

## 12. Verificación final

- [x] 12.1 Correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/` y `ruff check`; en `frontend/`, `npm test`, `npx tsc --noEmit` y `npx eslint .`; comparar con la línea base del grupo 1. **Verifica:** todo en verde y ningún test previo perdido
- [x] 12.2 `openspec validate email-confirmation-infra --strict`. **Verifica:** en verde
