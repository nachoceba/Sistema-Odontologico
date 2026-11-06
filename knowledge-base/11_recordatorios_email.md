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
- El servicio `worker` (Celery) toma la tarea y envía el email por SMTP solo si la fila sigue `pending` y `appointment_starts_at` coincide con el turno actual (idempotencia ante reentregas y reprogramaciones). La fila se toma con `SELECT … FOR UPDATE SKIP LOCKED` dentro de una transacción: dos procesamientos simultáneos envían a lo sumo un email. Luego actualiza la fila a `sent` (con `sent_at`) o `failed` con el error (DD-94).
- Si al procesarla el turno ya empezó o ya no está `scheduled`, no se envía nada y la fila queda `failed` con el error `EXPIRED` (DD-88). Esto cubre también las `pending` acumuladas desde C-08.
- Un fallo de envío o de Redis nunca revierte ni bloquea el turno (RN-NO-04).
- La tarea de Beat `reencolar_pendientes` corre cada 10 minutos y reencola las notificaciones `pending` creadas hace más de 5 minutos (columna `created_at`), de la más antigua a la más nueva y hasta 100 por pasada (por ejemplo, las que no se pudieron publicar por un Redis caído). Solo toma las `pending`: nunca las `sent` ni las `failed` (DD-88, DD-89).

## Programación del recordatorio

- Celery Beat dispara `enviar_recordatorios` **cada hora**. La tarea no hace nada salvo que la hora local del consultorio sea igual a `clinic_settings.reminder_send_hour` (por defecto 9:00). Así el valor guardado en la base se respeta sin reiniciar el servicio `beat`.
- La aplicación Celery se configura con `timezone` igual a la zona del consultorio y `enable_utc = True`.
- Selecciona los turnos `scheduled` cuyo `starts_at` cae en el día siguiente (en la zona del consultorio) y sin notificación `reminder` para esa fecha.
- El aviso sale "el día anterior", no exactamente 24 h antes (IN-01). Con Beat cada hora, pasar a una ventana de 24 h exactas es una mejora posible.
- Un turno agendado después de la ejecución diaria recibe solo la confirmación.

## Idempotencia y errores

- `email_notifications` tiene `UNIQUE (appointment_id, kind, appointment_starts_at)`. Reejecutar la tarea no reenvía.
- Si el envío falla se guarda `status = failed` y `error`; el lote continúa (RN-NO-04).
- Reintentos (DD-89): un fallo temporal (servidor SMTP caído o sin respuesta, respuesta 4xx) se reintenta hasta 3 intentos en total, con esperas de 1 y 2 minutos, y la fila sigue `pending` mientras tanto. Un fallo permanente (5xx, destinatario o credenciales rechazados) queda `failed` al instante. En C-11 una `failed` no se reintenta; una segunda pasada diaria de `failed` queda para C-12.
- El texto de `error` es un código corto sin datos personales: `SMTP_PERMANENT 550`, `SMTP_TEMPORARY CONNECTION`, `SMTP_TEMPORARY TIMEOUT` o `EXPIRED`; nunca el texto del servidor ni la dirección.
- Reprogramar descarta las notificaciones `pending` de la fecha anterior y crea otras para la nueva fecha (RN-NO-05); por eso el `UNIQUE` incluye `appointment_starts_at`.

## Límites y riesgos

- **Solo desarrollo y pruebas:** Mailpit (contenedor incluido en Docker Compose) recibe todos los emails y los muestra en una interfaz web. No sale ningún email real.
- **Desarrollo y demo:** Mailpit es el servidor SMTP; los emails se ven en http://localhost:8025 (DD-87). El adaptador SMTP se configura solo con las variables `SMTP_*` y `EMAIL_FROM`, así que apuntar a otro servidor no toca el código. El proveedor de producción queda abierto (SU-02).
- Los emails de pacientes ficticios no deben apuntar a buzones de terceros reales. La variable opcional `EMAIL_REDIRECT_TO` manda todos los emails a una única casilla, con la línea "Email de demostración: en producción se enviaría al paciente del turno." y sin la dirección original; vacía, van al paciente.
- El broker Redis es un servicio más que puede caerse; ver el manejo en "Envío asincrónico".

## Tareas

| Tarea Celery | Disparador | Resumen |
|---|---|---|
| `enviar_email` | Encolada por los casos de uso | Envía una notificación y registra el resultado |
| `enviar_recordatorios` | Celery Beat (cada hora) | Solo actúa a la hora configurada: crea y envía los recordatorios de los turnos del día siguiente; registra `{ processed, sent, failed }` en el log |
| `reencolar_pendientes` | Celery Beat (cada 10 minutos) | Reencola las notificaciones `pending` de más de 5 minutos (tope 100 por pasada); registra solo la cantidad |
