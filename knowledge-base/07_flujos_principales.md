# Flujos Principales

## Flujo 1: Inicio de sesión
**Disparador**: usuario abre la app sin sesión
**Actor**: administrador, recepcionista u odontólogo

**Pasos**:
1. La UI redirige a `/login`.
2. El usuario envía email y contraseña a `POST /api/v1/auth/login`.
3. La API verifica el hash de la contraseña, comprueba que el usuario esté activo y devuelve un JWT de acceso con el rol.
4. El frontend guarda el token y lo envía en cada llamada (`Authorization: Bearer`).
5. Redirige a la agenda según el rol.

**Casos de error**:
- Credenciales inválidas → mensaje genérico, sin revelar cuál dato falló.
- Usuario inactivo → sesión rechazada.

## Flujo 2: Agendar un turno
**Disparador**: recepción elige un slot libre
**Actor**: recepcionista

**Pasos**:
1. La UI pide la disponibilidad: `domain` calcula slots a partir de `working_hours`, `time_off` y turnos `scheduled`.
2. Recepción selecciona o crea el paciente y confirma el slot.
3. El caso de uso `agendar_turno` valida RN-TU-01 a RN-TU-04 en el dominio.
4. Inserta el turno; el constraint de exclusión protege ante concurrencia.
5. Crea la fila `email_notifications` (`confirmation`, `pending`) y encola la tarea `enviar_email` en Redis.
6. El worker de Celery envía el email y actualiza la notificación a `sent` o `failed`.

**Diagrama de secuencia**:
```
Recepción → Frontend React → FastAPI → domain (valida)
                               │→ PostgreSQL (INSERT turno)
                               │→ Redis (encola enviar_email)
                               ← turno creado
Worker Celery → servidor SMTP (email de confirmación)
```

**Casos de error**:
- Slot ocupado o fuera de horario → error de validación, sin escribir.
- Choque concurrente (constraint de exclusión) → se traduce a "el slot acaba de ocuparse".
- Falla del email o de Redis → el turno queda creado; la notificación queda `pending` (Redis caído o fallo temporal del SMTP) o `failed` (fallo permanente o reintentos agotados); `reencolar_pendientes` reintenta solo las `pending` (RN-NO-04, DD-89).

## Flujo 3: Cancelar o reprogramar
**Disparador**: el paciente avisa por teléfono o mensaje
**Actor**: recepcionista

**Pasos (cancelar)**:
1. Recepción abre el turno y elige "Cancelar" con un motivo.
2. El turno pasa a `cancelled` y el slot queda libre.

**Pasos (reprogramar)**:
1. Recepción elige un nuevo slot.
2. Se validan las reglas de agendar contra el nuevo horario.
3. Se actualiza `starts_at` y `ends_at` en una sola operación.
4. Se genera la nueva confirmación; el recordatorio lo crea la tarea diaria para la nueva fecha.

**Casos de error**:
- Nuevo slot inválido → el turno original no cambia (RN-TU-06).

## Flujo 4: Recordatorio previo
**Disparador**: Celery Beat (cada hora); la tarea actúa solo a la hora `reminder_send_hour`
**Actor**: sistema

**Pasos**:
1. Celery Beat dispara la tarea `enviar_recordatorios` (no hay ruta HTTP que proteger).
2. La tarea lee la zona y la hora configurada de `clinic_settings`; si la hora local no es `reminder_send_hour`, termina sin hacer nada.
3. Calcula el día siguiente en la zona del consultorio y busca los turnos `scheduled` de todos los profesionales que empiezan ese día.
4. Por cada uno crea la notificación `reminder` (solo si no existe para ese horario y el turno sigue vigente) y envía el email por SMTP en el momento.
5. Registra `sent` o `failed` por turno (o lo deja `pending` ante un fallo temporal) y sigue con el siguiente; al final registra `processed`, `sent`, `failed` y `pending`.

**Casos de error**:
- Redis, Beat o el worker caídos durante toda la hora configurada → la tarea no corre ese día y las pasadas de otras horas no lo recuperan (DD-98); los pacientes conservan su confirmación.
- Falla de un envío → se registra y no corta el lote; un fallo temporal deja la fila `pending` para el reencolado y una `failed` no se reintenta (DD-97).
- Ejecución duplicada de la tarea → el `UNIQUE (appointment_id, kind, appointment_starts_at)` evita reenvíos.

## Flujo 5: Definir horarios y licencias
**Disparador**: cambio en la disponibilidad de un profesional
**Actor**: administrador

**Pasos**:
1. El administrador edita `working_hours` o crea un `time_off`.
2. El sistema valida que los tramos no se superpongan.
3. Consulta los turnos `scheduled` que quedan fuera del nuevo horario y los lista como conflictos.
4. Recepción reprograma o cancela esos turnos.

## Flujo 6: Reserva online
**Disparador**: el paciente abre `/turnos`
**Actor**: paciente (sin sesión) y sistema

**Pasos**:
1. La página pública pide `GET /api/v1/public/professionals` y las franjas libres del profesional elegido (`.../slots?date=`).
2. El paciente elige una franja y completa DNI, nombre, apellido y email (teléfono opcional). El campo trampa `website` va vacío.
3. `POST /api/v1/public/appointments` aplica el límite por IP (5 por hora) y valida los datos. El caso de uso `reservar_online` busca el DNI: si no existe crea la ficha; si existe, compara nombre y apellido con la ficha y la vincula sin modificarla.
4. Inserta el turno como `scheduled` con `pending_until` y el hash del token, sin `created_by`; el constraint de exclusión protege ante concurrencia. La respuesta es 202 y trae solo profesional, día, hora y el plazo.
5. Después del commit se encola `enviar_verificacion_reserva`, que manda al email de la ficha el enlace `PUBLIC_APP_URL/turnos/confirmar#token=…`.
6. El paciente abre el enlace y toca el botón; la página hace `POST /api/v1/public/appointment-confirmations` con el token (10 por hora por IP).
7. En una transacción se busca el turno por el hash con `FOR UPDATE`, se comprueba que siga `scheduled`, que `pending_until` no haya pasado y que el turno no haya empezado, y se limpian `pending_until` y el hash. Se registra la notificación `confirmation` y se envía el email de confirmación normal (C-11). Desde ahí el turno recibe el recordatorio como cualquier otro.

**Casos de error**:
- Franja ocupada o fuera de horario → `SLOT_TAKEN` o `SLOT_UNAVAILABLE`, sin crear la ficha de un DNI nuevo.
- DNI existente con otro nombre, paciente inactivo, paciente con otro turno a la misma hora o carrera de DNI → el mismo `BOOKING_NOT_POSSIBLE` ("Verifique sus datos ingresados."), sin pistas de cuál fue el motivo.
- Campo trampa completo → `BOOKING_REJECTED`. Límite excedido → `TOO_MANY_REQUESTS` con `Retry-After`.
- Enlace usado, inexistente o de una reserva vencida o cancelada → `CONFIRMATION_LINK_INVALID` (410), con la pantalla "Enlace no válido".
- Redis caído al encolar la verificación → la reserva queda pendiente sin email; el paciente puede volver a reservar.
- Mientras no exista el vencimiento automático (C-16), una reserva pendiente vencida sigue ocupando la franja hasta que la recepción la cancele.
