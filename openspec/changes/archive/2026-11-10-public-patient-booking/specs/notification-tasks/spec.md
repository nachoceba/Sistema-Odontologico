# Spec Delta: notification-tasks

## ADDED Requirements

### Requirement: Email de verificación de una reserva online (DD-130, DD-131)

Después de guardar una reserva pendiente, el caso de uso SHALL encolar una tarea de envío del email de verificación con el identificador del turno y el token en claro. El token viaja solo en el mensaje de la cola; nunca se guarda en la base ni en el log. La tarea MUST enviar el email solo si el turno sigue pendiente, no venció y el hash del token coincide con el guardado. En cualquier otro caso termina sin enviar. Reintenta los fallos temporales del servidor SMTP como la confirmación (DD-89). No crea filas en `email_notifications` y `reencolar_pendientes` MUST NOT tomarla. Un fallo al encolar MUST NOT deshacer la reserva: el turno queda pendiente hasta su vencimiento. El log de la tarea lleva solo el identificador del turno y el resultado.

#### Scenario: Envío de la verificación (esperado)
- **WHEN** se guarda una reserva pendiente y el worker procesa la tarea
- **THEN** sale un email al email de la ficha con el enlace de confirmación

#### Scenario: Turno ya cancelado o vencido (borde)
- **WHEN** el worker procesa la tarea de un turno que la recepción ya canceló
- **THEN** no sale ningún email

#### Scenario: Token en el log (borde)
- **WHEN** la tarea registra su resultado
- **THEN** el log no contiene el token ni el email
