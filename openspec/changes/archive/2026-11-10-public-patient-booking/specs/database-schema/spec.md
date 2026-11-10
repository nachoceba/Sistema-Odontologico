# Spec Delta: database-schema

## MODIFIED Requirements

### Requirement: Integridad de los datos de un turno

La tabla de turnos SHALL guardar inicio y fin como instantes con zona horaria, MUST rechazar un inicio igual o posterior al fin, MUST asignar `scheduled` como estado por defecto y MUST rechazar un estado fuera de `scheduled`, `cancelled`, `completed` y `no_show`. Paciente y profesional MUST existir. El usuario creador es opcional (C-15): nulo significa que el turno se reservó online; si tiene valor, ese usuario MUST existir. Una migración nueva (`0003`) MUST volver opcional la columna sin tocar los turnos existentes, y su reversión MUST fallar sin cambiar nada si hay turnos sin usuario creador. Un instante escrito con otra zona horaria MUST leerse como el mismo instante.

#### Scenario: Inicio igual o posterior al fin (error de negocio)
- **CUANDO** se inserta directo en la base un turno de 10:30 a 10:30, o de 10:30 a 10:00
- **ENTONCES** la base rechaza la inserción por el CHECK de inicio anterior al fin

#### Scenario: El instante se conserva entre zonas (esperado)
- **CUANDO** se guarda un turno con inicio `2026-10-05T10:00-03:00`
- **ENTONCES** al leerlo, su inicio es el instante `2026-10-05T13:00Z`

#### Scenario: Estado por defecto (esperado)
- **CUANDO** se inserta un turno sin indicar el estado
- **ENTONCES** queda `scheduled`

#### Scenario: Estado inválido (error de negocio)
- **CUANDO** se inserta un turno con estado `pending`
- **ENTONCES** la base lo rechaza

#### Scenario: Paciente o profesional inexistente (error de negocio)
- **CUANDO** se inserta un turno con un paciente, un profesional o un usuario creador (no nulo) que no existen
- **ENTONCES** la base lo rechaza por clave foránea

#### Scenario: Turno online sin usuario creador (esperado)
- **CUANDO** se inserta un turno con usuario creador nulo
- **ENTONCES** la base lo acepta y el constraint de no superposición lo cubre igual que a los demás

#### Scenario: Revertir con turnos online guardados (borde)
- **CUANDO** se revierte la migración `0003` y hay turnos con usuario creador nulo
- **ENTONCES** la reversión falla y el esquema queda como estaba

## ADDED Requirements

### Requirement: Datos de la reserva pendiente en el turno (DD-130, DD-131)

La migración `0003` SHALL agregar a `appointments` dos columnas opcionales: `pending_until` (instante con zona) y `confirmation_token_hash` (texto). Un turno está pendiente de confirmación cuando `pending_until` no es nulo. La base MUST garantizar:

- las dos columnas son nulas juntas o no nulas juntas;
- solo un turno sin usuario creador puede estar pendiente;
- un hash de token no se repite: índice único parcial sobre `confirmation_token_hash` cuando no es nulo;
- un índice parcial sobre `pending_until` cuando no es nulo, para la tarea de vencimiento.

El estado del turno pendiente es `scheduled`, así que el constraint `ex_appointments_no_overlap` lo cubre sin cambios. La migración MUST NOT modificar el tipo `appointment_status` ni el constraint de exclusión.

#### Scenario: Pendiente bien formado (esperado)
- **CUANDO** se inserta un turno sin usuario creador con `pending_until` y `confirmation_token_hash`
- **ENTONCES** la base lo acepta

#### Scenario: Pendiente con solo una de las columnas (error de negocio)
- **CUANDO** se inserta un turno con `pending_until` y sin `confirmation_token_hash`
- **ENTONCES** la base lo rechaza por CHECK

#### Scenario: Pendiente creado por la recepción (error de negocio)
- **CUANDO** se inserta un turno con usuario creador y `pending_until`
- **ENTONCES** la base lo rechaza por CHECK

#### Scenario: Pendiente contra confirmado superpuestos (borde, regla dura 6)
- **CUANDO** se inserta un turno pendiente que se superpone con un turno `scheduled` confirmado del mismo profesional
- **ENTONCES** la base lo rechaza por `ex_appointments_no_overlap`

#### Scenario: Hash repetido (borde)
- **CUANDO** dos turnos pendientes tienen el mismo `confirmation_token_hash`
- **ENTONCES** la base rechaza el segundo
