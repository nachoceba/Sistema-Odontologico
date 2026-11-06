# notification-registration Specification

## Purpose
Definir qué deja registrado la agenda en `email_notifications` al agendar, reprogramar y cancelar, y el contrato del registro para leer, tomar y marcar esas notificaciones, de modo que C-08 prepare las confirmaciones sin enviar emails y C-11 las envíe después del commit.

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

### Requirement: Contrato del registro de notificaciones

Toda implementación del registro de notificaciones (en memoria y PostgreSQL) SHALL cumplir una batería de contrato común: registrar una `confirmation` `pending`, listar las de un turno, borrar las `pending` de un turno (todas o las de un horario dado) sin tocar `sent` ni `failed`, y no duplicar una notificación con el mismo turno, tipo y horario. Desde C-11 la batería MUST cubrir además: tomar una notificación `pending` por id para enviarla (devuelve nada si no existe, si no está `pending` o si otro procesamiento ya la tomó), marcarla `sent` con su instante de envío, marcarla `failed` con un error, y listar las `pending` creadas antes de un instante dado, de la más antigua a la más nueva y con un tope de cantidad. Marcar una notificación que no está `pending` MUST NOT cambiarla. La batería de PostgreSQL corre solo con los tests de integración.

#### Scenario: Misma batería en memoria y PostgreSQL (esperado)
- **WHEN** se corre la batería con los tests de integración pedidos
- **THEN** cada escenario corre contra ambas implementaciones y todos pasan

#### Scenario: Registrar dos veces la misma confirmación (borde)
- **WHEN** se registra dos veces una `confirmation` para el mismo turno y el mismo horario
- **THEN** queda una sola, sin error

#### Scenario: Marcar enviada (esperado)
- **WHEN** se toma una `pending` y se la marca `sent` a las 09:00
- **THEN** al listar las del turno figura `sent` con `sent_at` 09:00 y sin error

#### Scenario: Marcar fallida (esperado)
- **WHEN** se toma una `pending` y se la marca `failed` con `SMTP_PERMANENT 550`
- **THEN** al listar las del turno figura `failed` con ese error y sin `sent_at`

#### Scenario: Tomar una que ya no está pendiente (error de negocio)
- **WHEN** se intenta tomar para envío una notificación `sent`
- **THEN** no se obtiene nada y la fila no cambia

#### Scenario: Toma simultánea en PostgreSQL (borde)
- **WHEN** una sesión tomó una `pending` sin terminar su transacción y otra sesión intenta tomar la misma
- **THEN** la segunda no obtiene nada, sin esperar a que la primera termine

#### Scenario: Pendientes antiguas con tope (borde)
- **WHEN** hay tres `pending` creadas a las 08:00, 08:10 y 08:20, una `sent` creada a las 07:00, y se piden las creadas antes de las 08:15 con tope 1
- **THEN** se obtiene solo la de las 08:00
