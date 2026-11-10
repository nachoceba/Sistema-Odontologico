# Spec Delta: database-schema

## ADDED Requirements

### Requirement: Tipo de notificación del aviso de vencimiento (DD-140)

La migración `0004` SHALL agregar el valor `booking_expired` al tipo `notification_kind`, sin tocar las notificaciones existentes ni el `UNIQUE (appointment_id, kind, appointment_starts_at)`. Su reversión MUST fallar sin cambiar nada si hay notificaciones `booking_expired`; si no las hay, MUST volver el tipo a `confirmation` y `reminder`.

#### Scenario: Aviso de vencimiento guardado (esperado)
- **CUANDO** se inserta una notificación `booking_expired` `pending`
- **ENTONCES** la base la acepta

#### Scenario: Aviso duplicado (error de negocio)
- **CUANDO** se inserta un segundo `booking_expired` para el mismo turno e inicio
- **ENTONCES** la base lo rechaza por el `UNIQUE`

#### Scenario: Revertir con avisos guardados (borde)
- **CUANDO** se revierte la migración `0004` y hay notificaciones `booking_expired`
- **ENTONCES** la reversión falla y el esquema queda como estaba
