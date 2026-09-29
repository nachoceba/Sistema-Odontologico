# Recordatorios por Email

Integración central de v1 (extra al conjunto canónico).

## Tipos de email

| Tipo (`kind`) | Cuándo | Contenido mínimo |
|---|---|---|
| `confirmation` | Inmediatamente al agendar o reprogramar | Paciente, profesional, fecha y hora, dirección del consultorio |
| `reminder` | Una vez, antes del turno (ver "Programación") | Igual que la confirmación, con aviso de que es un recordatorio |

Ambos son **informativos**: el paciente no confirma ni cancela desde el email (DD-06). Para cambios debe contactar al consultorio.

## Programación del recordatorio

- Un cron diario a la hora `clinic_settings.reminder_send_hour` (por defecto 9:00, hora del consultorio) llama a `/api/cron/reminders`.
- Selecciona los turnos `scheduled` cuyo `starts_at` cae en el día siguiente (en la zona del consultorio) y sin notificación `reminder`.
- Consecuencia: el aviso sale "el día anterior", no exactamente 24 h antes (IN-01, SU-03).
- Un turno agendado después de la ejecución del cron del día anterior recibe solo la confirmación.

## Idempotencia y errores

- `email_notifications` tiene `UNIQUE (appointment_id, kind)`. Reejecutar el cron no reenvía.
- Si el envío falla se guarda `status = failed` y `error`; el lote continúa (RN-NO-04).
- Reintento: una segunda pasada del cron puede reintentar las notificaciones `failed` del mismo día (decisión a confirmar en la implementación).
- Reprogramar reemplaza la notificación pendiente por una nueva para la nueva fecha (RN-NO-05).

## Límites y riesgos

- Cuota de envíos del plan gratuito de Resend: verificar límite diario y mensual.
- Sin dominio propio verificado, el envío puede restringirse a la cuenta dueña (SU-02). En el seed, los pacientes ficticios usan emails de prueba controlados por el equipo.
- Los emails de pacientes ficticios no deben apuntar a buzones de terceros reales.

## Endpoint

`GET/POST /api/cron/reminders`
- Requiere `Authorization: Bearer $CRON_SECRET`; sin él responde 401.
- Devuelve un resumen: `{ processed, sent, failed }`.
