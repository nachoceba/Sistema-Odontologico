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
- Falla del email o de Redis → el turno queda creado; la notificación queda `failed` o `pending` y `reencolar_pendientes` la reintenta (RN-NO-04).

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
2. La tarea calcula el día siguiente en la zona del consultorio.
3. Busca turnos `scheduled` del día siguiente sin notificación `reminder`.
4. Por cada uno crea la notificación y envía el email por SMTP.
5. Registra `sent` o `failed` por turno y sigue con el siguiente.

**Casos de error**:
- Redis o el worker caídos → la tarea no corre ese día; la siguiente pasada recoge los turnos pendientes.
- Falla de un envío → se registra y no corta el lote.
- Ejecución duplicada de la tarea → el `UNIQUE (appointment_id, kind, appointment_starts_at)` evita reenvíos.

## Flujo 5: Definir horarios y licencias
**Disparador**: cambio en la disponibilidad de un profesional
**Actor**: administrador

**Pasos**:
1. El administrador edita `working_hours` o crea un `time_off`.
2. El sistema valida que los tramos no se superpongan.
3. Consulta los turnos `scheduled` que quedan fuera del nuevo horario y los lista como conflictos.
4. Recepción reprograma o cancela esos turnos.
