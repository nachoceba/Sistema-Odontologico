# Spec Delta

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Aviso posterior al commit sin efecto en C-08 (RN-NO-04, borde con C-11)
**Reason**: C-11 reemplaza el despachador que no hacía nada por el encolado real del envío.
**Migration**: el comportamiento posterior al commit (publicar después de confirmar, no publicar si se revirtió, un fallo nunca rompe la operación y se registra sin datos del paciente) pasa al requirement "Encolar después del commit sin depender de Redis" de la spec `notification-tasks`.
