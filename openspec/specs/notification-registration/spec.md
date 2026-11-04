# notification-registration Specification

## Purpose
Definir qué deja registrado la agenda en `email_notifications` al agendar, reprogramar y cancelar, y el aviso posterior al commit que C-11 usará para encolar los envíos, de modo que C-08 prepare las notificaciones sin enviar ningún email.

## Requirements

### Requirement: Confirmación pendiente al agendar (RN-NO-01, P-1)

Al agendar un turno, el sistema SHALL registrar, en la misma transacción que el turno, una notificación de tipo `confirmation` en estado `pending`, sin fecha de envío ni error, cuyo `appointment_starts_at` es el inicio del turno. C-08 MUST NOT enviar ningún email ni conectarse a Redis o SMTP.

#### Scenario: Agendar registra la confirmación (esperado)
- **WHEN** se agenda un turno de la Dra. A mañana a las 10:00
- **THEN** existe una sola notificación `confirmation` `pending` de ese turno con `appointment_starts_at` igual a mañana 10:00

#### Scenario: Agendar rechazado no registra nada (error de negocio)
- **WHEN** se intenta agendar en un horario ocupado
- **THEN** no se registra ninguna notificación

### Requirement: Reprogramar reemplaza las pendientes (RN-NO-05, P-2)

Al reprogramar, el sistema SHALL borrar, en la misma transacción, las notificaciones `pending` del turno (de cualquier tipo) cuyo `appointment_starts_at` es el horario anterior, y registrar una `confirmation` `pending` para el nuevo inicio. Las notificaciones `sent` y `failed` MUST conservarse como historial. Si ya existe una confirmación para el nuevo inicio (el turno vuelve a un horario que ya tuvo), MUST NOT duplicarse ni hacer fallar la reprogramación (RN-NO-03).

#### Scenario: Reprogramar con confirmación sin enviar (esperado)
- **WHEN** un turno de las 10:00 tiene su confirmación `pending` y se lo mueve a las 11:00
- **THEN** la confirmación de las 10:00 ya no existe y hay una `confirmation` `pending` para las 11:00

#### Scenario: Reprogramar con confirmación ya enviada (borde)
- **WHEN** un turno de las 10:00 tiene su confirmación `sent` y se lo mueve a las 11:00
- **THEN** la confirmación `sent` de las 10:00 se conserva y se agrega una `confirmation` `pending` para las 11:00

#### Scenario: Volver a un horario anterior (borde)
- **WHEN** un turno se movió de las 10:00 (confirmación `sent`) a las 11:00 y después se lo vuelve a mover a las 10:00
- **THEN** la reprogramación se acepta, la confirmación `sent` de las 10:00 se conserva sin duplicarse y la `pending` de las 11:00 se borra

#### Scenario: Reprogramar rechazado no toca notificaciones (error de negocio)
- **WHEN** se intenta reprogramar a un horario ocupado
- **THEN** las notificaciones del turno quedan exactamente como estaban

### Requirement: Cancelar descarta las pendientes (RN-NO-05, US-008)

Al cancelar un turno, el sistema SHALL borrar en la misma transacción sus notificaciones `pending` y MUST NOT registrar ninguna nueva. Las `sent` y `failed` se conservan. Marcar atención MUST NOT crear ni borrar notificaciones.

#### Scenario: Cancelar con confirmación sin enviar (esperado)
- **WHEN** se cancela un turno cuya confirmación sigue `pending`
- **THEN** el turno queda `cancelled` y no le queda ninguna notificación `pending`

#### Scenario: Cancelar con confirmación enviada (borde)
- **WHEN** se cancela un turno cuya confirmación ya está `sent`
- **THEN** la confirmación `sent` se conserva y no se crea ninguna notificación nueva

### Requirement: Aviso posterior al commit sin efecto en C-08 (RN-NO-04, borde con C-11)

Después de que la transacción de agendar o reprogramar se confirma, el sistema SHALL avisar al despachador de notificaciones con las notificaciones registradas. En C-08 el despachador MUST NOT hacer nada (C-11 lo reemplaza por el encolado). El despachador MUST NOT ser llamado si la transacción se revirtió. Si el despachador falla, la operación de turno MUST responder igual como exitosa y el turno y la notificación `pending` MUST quedar guardados (RN-NO-04); el fallo se registra en el log sin datos del paciente.

#### Scenario: Aviso tras agendar (esperado)
- **WHEN** se agenda un turno válido
- **THEN** el despachador recibe exactamente una notificación, la confirmación recién registrada, después de confirmada la transacción

#### Scenario: Sin aviso si se rechaza (error de negocio)
- **WHEN** agendar se rechaza con `SLOT_TAKEN`
- **THEN** el despachador no recibe nada

#### Scenario: El despachador falla (borde)
- **WHEN** el despachador lanza un error tras agendar
- **THEN** la API responde 201 con el turno, y el turno y su confirmación `pending` quedan guardados

### Requirement: Contrato del registro de notificaciones

Toda implementación del registro de notificaciones (en memoria y PostgreSQL) SHALL cumplir una batería de contrato común: registrar una `confirmation` `pending`, listar las de un turno, borrar las `pending` de un turno (todas o las de un horario dado) sin tocar `sent` ni `failed`, y no duplicar una notificación con el mismo turno, tipo y horario. La batería de PostgreSQL corre solo con los tests de integración.

#### Scenario: Misma batería en memoria y PostgreSQL (esperado)
- **WHEN** se corre la batería con los tests de integración pedidos
- **THEN** cada escenario corre contra ambas implementaciones y todos pasan

#### Scenario: Registrar dos veces la misma confirmación (borde)
- **WHEN** se registra dos veces una `confirmation` para el mismo turno y el mismo horario
- **THEN** queda una sola, sin error
