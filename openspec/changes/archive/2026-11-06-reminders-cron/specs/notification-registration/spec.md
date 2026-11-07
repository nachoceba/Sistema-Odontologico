# Spec Delta

## MODIFIED Requirements

### Requirement: Contrato del registro de notificaciones

Toda implementación del registro de notificaciones (en memoria y PostgreSQL) SHALL cumplir una batería de contrato común: registrar una `confirmation` `pending`, listar las de un turno, borrar las `pending` de un turno (todas o las de un horario dado) sin tocar `sent` ni `failed`, y no duplicar una notificación con el mismo turno, tipo y horario. Desde C-11 la batería MUST cubrir además: tomar una notificación `pending` por id para enviarla (devuelve nada si no existe, si no está `pending` o si otro procesamiento ya la tomó), marcarla `sent` con su instante de envío, marcarla `failed` con un error, y listar las `pending` creadas antes de un instante dado, de la más antigua a la más nueva y con un tope de cantidad. Desde C-12 la batería MUST cubrir también registrar un `reminder` `pending` para un turno y su horario: se registra solo si el turno sigue `scheduled` con ese mismo horario en ese momento (si no, no se registra nada y no hay error), devuelve nada si ya existía un `reminder` de ese turno y horario en cualquier estado, y no afecta la `confirmation` del mismo turno y horario. Marcar una notificación que no está `pending` MUST NOT cambiarla. La batería de PostgreSQL corre solo con los tests de integración.

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

#### Scenario: Registrar un recordatorio (esperado)
- **WHEN** se registra un `reminder` para un turno `scheduled` del lunes 10:00 con ese horario, y el turno ya tiene su `confirmation` `sent`
- **THEN** al listar las del turno figuran la `confirmation` `sent` y un `reminder` `pending` con horario lunes 10:00

#### Scenario: Recordatorio ya existente en cualquier estado (borde)
- **WHEN** el turno ya tiene un `reminder` `failed` con horario lunes 10:00 y se vuelve a registrar un `reminder` con ese horario
- **THEN** no se obtiene nada, sin error, y sigue habiendo un solo `reminder` para ese horario

#### Scenario: Recordatorio de un turno que ya no está vigente con ese horario (error de negocio)
- **WHEN** se registra un `reminder` con horario lunes 10:00 para un turno que está `cancelled`, o que ahora empieza a las 11:00
- **THEN** no se obtiene nada, no se registra ninguna fila y no hay error

#### Scenario: Recordatorio mientras se reprograma el turno en PostgreSQL (borde)
- **WHEN** una sesión reprogramó el turno de las 10:00 a las 11:00 sin terminar su transacción y otra registra un `reminder` con horario 10:00
- **THEN** cuando la reprogramación se confirma, no queda ningún `reminder` con horario 10:00 para ese turno
