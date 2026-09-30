# Recordatorios por Email

Integración central de v1 (extra al conjunto canónico). Usa Redis y Celery para el envío asincrónico.

## Tipos de email

| Tipo (`kind`) | Cuándo | Contenido mínimo |
|---|---|---|
| `confirmation` | Inmediatamente al agendar o reprogramar | Paciente, profesional, fecha y hora, dirección del consultorio |
| `reminder` | Una vez, antes del turno (ver "Programación") | Igual que la confirmación, con aviso de que es un recordatorio |

Ambos son **informativos**: el paciente no confirma ni cancela desde el email (DD-06). Para cambios debe contactar al consultorio.

## Envío asincrónico

- Al agendar o reprogramar, el caso de uso guarda el turno y la fila `email_notifications` (`pending`) en la misma transacción. **Después del commit** encola la tarea `enviar_email` en Redis.
- La publicación usa `apply_async(retry=False)` con un timeout corto dentro de un `try/except`, para que la respuesta de la API no espere a Redis. Si falla, la notificación queda `pending`.
- El servicio `worker` (Celery) toma la tarea y envía el email por SMTP solo si la fila sigue `pending` y `appointment_starts_at` coincide con el turno actual (idempotencia ante reentregas y reprogramaciones). Luego actualiza la fila a `sent` o `failed` con el error.
- Un fallo de envío o de Redis nunca revierte ni bloquea el turno (RN-NO-04).
- La tarea de Beat `reencolar_pendientes` corre cada 10 minutos y reencola las notificaciones `pending` con más de unos minutos de antigüedad (por ejemplo, las que no se pudieron publicar por un Redis caído).

## Programación del recordatorio

- Celery Beat dispara `enviar_recordatorios` **cada hora**. La tarea no hace nada salvo que la hora local del consultorio sea igual a `clinic_settings.reminder_send_hour` (por defecto 9:00). Así el valor guardado en la base se respeta sin reiniciar el servicio `beat`.
- La aplicación Celery se configura con `timezone` igual a la zona del consultorio y `enable_utc = True`.
- Selecciona los turnos `scheduled` cuyo `starts_at` cae en el día siguiente (en la zona del consultorio) y sin notificación `reminder` para esa fecha.
- El aviso sale "el día anterior", no exactamente 24 h antes (IN-01). Con Beat cada hora, pasar a una ventana de 24 h exactas es una mejora posible.
- Un turno agendado después de la ejecución diaria recibe solo la confirmación.

## Idempotencia y errores

- `email_notifications` tiene `UNIQUE (appointment_id, kind, appointment_starts_at)`. Reejecutar la tarea no reenvía.
- Si el envío falla se guarda `status = failed` y `error`; el lote continúa (RN-NO-04).
- Reintento: Celery puede reintentar una tarea fallida con espera creciente; además, una segunda pasada diaria puede reintentar las notificaciones `failed` (decisión a confirmar en la implementación).
- Reprogramar descarta las notificaciones `pending` de la fecha anterior y crea otras para la nueva fecha (RN-NO-05); por eso el `UNIQUE` incluye `appointment_starts_at`.

## Límites y riesgos

- **Solo desarrollo y pruebas:** Mailpit (contenedor incluido en Docker Compose) recibe todos los emails y los muestra en una interfaz web. No sale ningún email real.
- **Producción o demo:** hace falta un servidor SMTP gratuito. Verificar límites diarios y restricciones del proveedor elegido antes de construir (SU-02).
- Los emails de pacientes ficticios no deben apuntar a buzones de terceros reales.
- El broker Redis es un servicio más que puede caerse; ver el manejo en "Envío asincrónico".

## Tareas

| Tarea Celery | Disparador | Resumen |
|---|---|---|
| `enviar_email` | Encolada por los casos de uso | Envía una notificación y registra el resultado |
| `enviar_recordatorios` | Celery Beat (cada hora) | Solo actúa a la hora configurada: crea y envía los recordatorios de los turnos del día siguiente; registra `{ processed, sent, failed }` en el log |
| `reencolar_pendientes` | Celery Beat (cada 10 minutos) | Reencola las notificaciones `pending` antiguas |
