# Flujos Principales

## Flujo 1: Inicio de sesión
**Disparador**: usuario abre la app sin sesión
**Actor**: administrador, recepcionista u odontólogo

**Pasos**:
1. La UI redirige a `/login`.
2. El usuario envía email y contraseña.
3. Supabase Auth valida y devuelve la sesión.
4. La app lee `profiles.role` y comprueba `active`.
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
3. El caso de uso `agendarTurno` valida RN-TU-01 a RN-TU-04 en el dominio.
4. Inserta el turno; el constraint de exclusión protege ante concurrencia.
5. Crea la fila `email_notifications` (`confirmation`, `pending`) y envía el email.
6. Actualiza la notificación a `sent` o `failed`.

**Diagrama de secuencia**:
```
Recepción → UI → Server Action → domain (valida)
                       │→ Postgres (INSERT turno)
                       │→ Resend (email confirmación)
                       ← turno creado
```

**Casos de error**:
- Slot ocupado o fuera de horario → error de validación, sin escribir.
- Choque concurrente (constraint de exclusión) → se traduce a "el slot acaba de ocuparse".
- Falla del email → el turno queda creado; la notificación queda `failed` (RN-NO-04).

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
4. Se genera el nuevo email de confirmación y recordatorio.

**Casos de error**:
- Nuevo slot inválido → el turno original no cambia (RN-TU-06).

## Flujo 4: Recordatorio previo
**Disparador**: cron diario a la hora `reminder_send_hour`
**Actor**: sistema

**Pasos**:
1. El cron llama a `/api/cron/reminders` con `Bearer CRON_SECRET`.
2. El handler valida el secreto.
3. Busca turnos `scheduled` del día siguiente sin notificación `reminder`.
4. Por cada uno crea la notificación y envía el email.
5. Registra `sent` o `failed` por turno y sigue con el siguiente.

**Casos de error**:
- Secreto inválido → 401.
- Falla de un envío → se registra y no corta el lote.
- Ejecución duplicada del cron → el `UNIQUE (appointment_id, kind)` evita reenvíos.

## Flujo 5: Definir horarios y licencias
**Disparador**: cambio en la disponibilidad de un profesional
**Actor**: administrador

**Pasos**:
1. El administrador edita `working_hours` o crea un `time_off`.
2. El sistema valida que los tramos no se superpongan.
3. Consulta los turnos `scheduled` que quedan fuera del nuevo horario y los lista como conflictos.
4. Recepción reprograma o cancela esos turnos.
