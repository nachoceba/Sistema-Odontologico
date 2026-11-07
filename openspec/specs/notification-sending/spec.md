# notification-sending Specification

## Purpose
Definir qué hace el sistema con una notificación registrada en `email_notifications`: cuándo se envía, cuándo se descarta por obsoleta, cómo queda registrado el resultado (`sent` o `failed`) y cómo se recuperan las pendientes que no llegaron a encolarse, garantizando como máximo un email por tipo, turno y horario (RN-NO-03, RN-NO-04).

## Requirements

### Requirement: Enviar una notificación pendiente (RN-NO-01, Flujo 2 pasos 5 y 6)

Al procesar una notificación, el sistema SHALL armar el email de su tipo (spec `email-templates`) con los datos vigentes del turno, del paciente, del profesional y del consultorio, enviarlo al email del paciente (o a `EMAIL_REDIRECT_TO`, spec `email-sending`) y, si el envío sale bien, marcarla `sent` con `sent_at` igual al instante del envío y sin `error`. Procesar una notificación MUST NOT cambiar el turno ni ninguna otra notificación.

#### Scenario: Confirmación enviada (esperado)
- **WHEN** el turno de Juan Perez del lunes 09/11 10:00 está `scheduled`, su confirmación está `pending` con ese horario y el envío sale bien a las 09:00 del viernes 06/11
- **THEN** se envía un solo email a `juan.perez@example.com` y la notificación queda `sent` con `sent_at` igual a ese instante y `error` vacío

#### Scenario: Recordatorio enviado (esperado)
- **WHEN** existe un `reminder` `pending` de un turno `scheduled` futuro y su horario coincide con el del turno
- **THEN** se envía el email de recordatorio y la notificación queda `sent`

#### Scenario: Paciente desactivado con turno vigente (borde)
- **WHEN** el paciente del turno fue desactivado después de agendar y el turno sigue `scheduled` y futuro
- **THEN** la confirmación igual se envía (DD-76: el turno sigue vigente hasta que recepción lo cancele)

### Requirement: Como máximo un email por notificación (RN-NO-03, idempotencia)

El sistema SHALL enviar el email solo si, en el momento de procesarla, la notificación existe, sigue `pending` y su `appointment_starts_at` es igual al inicio actual del turno. En cualquier otro caso MUST NOT enviar nada ni modificar la notificación. Dos procesamientos simultáneos de la misma notificación (reentrega de la tarea, reencolado) MUST producir a lo sumo un email: mientras un procesamiento la tiene tomada, el otro MUST terminar sin enviar.

#### Scenario: Notificación ya enviada (error de negocio)
- **WHEN** se procesa una confirmación que ya está `sent`
- **THEN** no se envía ningún email y la fila no cambia

#### Scenario: Notificación borrada por cancelar o reprogramar (borde)
- **WHEN** se procesa el id de una confirmación que ya no existe porque el turno se canceló o se reprogramó antes del envío
- **THEN** no se envía ningún email y no hay error

#### Scenario: Horario que ya no es el del turno (borde)
- **WHEN** una `pending` tiene `appointment_starts_at` 10:00 pero el turno ahora empieza a las 11:00
- **THEN** no se envía ningún email y la fila no cambia

#### Scenario: Dos entregas a la vez (borde)
- **WHEN** dos procesos toman a la vez la misma confirmación `pending`
- **THEN** se envía exactamente un email y la notificación queda `sent` una sola vez

#### Scenario: Cancelar mientras se envía (borde)
- **WHEN** recepción cancela el turno mientras su confirmación se está enviando
- **THEN** la cancelación se completa igual (RN-NO-04) y queda una de dos situaciones: el email salió y la confirmación queda `sent` como historial, o la confirmación se borró antes y no salió ningún email; nunca un email enviado con la fila borrada sin registro

### Requirement: Avisos de turnos que ya empezaron o no están vigentes (P-4)

Si al procesar una notificación `pending` su turno ya empezó (inicio anterior o igual al instante del procesamiento) o no está `scheduled`, el sistema SHALL NOT enviar el email y MUST marcarla `failed` con `error = EXPIRED` y sin `sent_at`, para que no se vuelva a encolar. Esto cubre las confirmaciones `pending` acumuladas desde C-08 (DD-62) de turnos ya pasados.

#### Scenario: Pendiente acumulada de un turno pasado (esperado)
- **WHEN** al activar C-11 hay una confirmación `pending` registrada en C-08 de un turno que fue ayer
- **THEN** no se envía ningún email y queda `failed` con `error = EXPIRED`

#### Scenario: Pendiente acumulada de un turno futuro (esperado)
- **WHEN** al activar C-11 hay una confirmación `pending` registrada en C-08 de un turno `scheduled` de la semana próxima
- **THEN** la confirmación se envía y queda `sent`

#### Scenario: Turno que empieza justo ahora (borde)
- **WHEN** se procesa la confirmación a las 10:00:00 de un turno que empieza a las 10:00
- **THEN** no se envía y queda `failed` con `error = EXPIRED`

#### Scenario: Turno ya marcado atendido (borde)
- **WHEN** la confirmación sigue `pending` y el turno ya está `completed`
- **THEN** no se envía y queda `failed` con `error = EXPIRED`

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

### Requirement: Reencolar las pendientes antiguas (P-3)

Cada pasada de reencolado SHALL tomar las notificaciones `pending` creadas hace más de 5 minutos, de la más antigua a la más nueva y hasta 100 por pasada, y volver a pedir su envío. MUST NOT tomar las `pending` más recientes (todavía pueden estar en camino), ni las `sent` o `failed`. La pasada MUST registrar en el log solo la cantidad reencolada. Reencolar una notificación que ya estaba en la cola MUST NOT producir dos emails (requirement de idempotencia).

#### Scenario: Pendiente que no llegó a encolarse (esperado)
- **WHEN** una confirmación quedó `pending` hace 20 minutos porque Redis estaba caído al agendar, y corre la pasada
- **THEN** se pide su envío y, al procesarla, queda `sent`

#### Scenario: Pendiente recién creada (borde)
- **WHEN** una confirmación quedó `pending` hace 1 minuto y corre la pasada
- **THEN** no se toma en esta pasada

#### Scenario: Enviadas y fallidas no se tocan (error de negocio)
- **WHEN** hay notificaciones `sent` y `failed` creadas hace horas y corre la pasada
- **THEN** ninguna se vuelve a pedir

#### Scenario: Más de 100 pendientes antiguas (borde)
- **WHEN** hay 150 `pending` antiguas y corre una pasada
- **THEN** se piden las 100 más antiguas y las otras 50 quedan para la pasada siguiente

#### Scenario: Reencolar algo que ya estaba en la cola (borde)
- **WHEN** una `pending` antigua ya tenía su tarea en la cola y la pasada la vuelve a pedir
- **THEN** sale un solo email y la notificación queda `sent`
