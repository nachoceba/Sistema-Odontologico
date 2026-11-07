# Spec Delta

## MODIFIED Requirements

### Requirement: Fallos de envío registrados y reintentos acotados (RN-NO-04, P-5)

Ante un fallo **permanente** (spec `email-sending`) el sistema SHALL marcar la notificación `failed` con el error sin datos personales, sin reintentar. Ante un fallo **temporal** la notificación MUST seguir `pending` y el envío MUST reintentarse automáticamente, con un máximo de 3 intentos en total por procesamiento de la tarea de envío y esperas crecientes de 1 y 2 minutos; si el tercer intento también falla, MUST quedar `failed` con el error del último intento. Un recordatorio cuyo primer intento, hecho dentro de la pasada de recordatorios, falla de forma temporal MUST quedar `pending` para que lo tome el reencolado, que lo procesa como a cualquier otra pendiente. Una notificación `failed` MUST NOT reintentarse nunca: no hay segunda pasada de `failed`. Ningún fallo de envío MUST modificar, revertir ni bloquear el turno.

#### Scenario: Fallo permanente (error de negocio)
- **WHEN** el servidor rechaza al destinatario con 550
- **THEN** la notificación queda `failed` con `error = SMTP_PERMANENT 550`, sin `sent_at`, se hizo un solo intento y el turno sigue igual

#### Scenario: Fallo temporal que se recupera (borde)
- **WHEN** el primer intento falla porque el servidor SMTP no responde y el segundo sale bien
- **THEN** se envía un solo email y la notificación queda `sent`

#### Scenario: Fallo temporal persistente (borde)
- **WHEN** los tres intentos fallan porque el servidor SMTP está caído
- **THEN** la notificación queda `failed` con el error del tercer intento y no se hace un cuarto intento en ese procesamiento

#### Scenario: El turno no se entera del fallo (esperado)
- **WHEN** el envío de la confirmación falla de forma permanente
- **THEN** el turno sigue `scheduled` con el mismo horario y se puede cancelar o reprogramar normalmente

#### Scenario: Recordatorio con fallo temporal en la pasada (borde)
- **WHEN** el recordatorio de un turno falla de forma temporal dentro de la pasada de recordatorios
- **THEN** queda `pending` y, pasados más de 5 minutos, el reencolado lo vuelve a pedir y se procesa con sus reintentos normales

#### Scenario: Sin segunda pasada de fallidas (error de negocio)
- **WHEN** un recordatorio quedó `failed` con `SMTP_TEMPORARY CONNECTION` a las 09:05 y corren las pasadas siguientes del mismo día
- **THEN** ninguna lo vuelve a intentar y la fila no cambia
