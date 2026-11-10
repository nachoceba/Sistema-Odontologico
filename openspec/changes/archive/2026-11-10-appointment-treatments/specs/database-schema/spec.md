# Spec Delta: database-schema

## ADDED Requirements

### Requirement: Catálogo de tratamientos y tratamiento del turno (C-17)

La migración `0005` SHALL crear:

- La tabla `treatments` con `id` uuid PK (`gen_random_uuid()`), `name` text NOT NULL, `name_key` text NOT NULL, `active` boolean NOT NULL default true y `created_at` timestamptz NOT NULL default `now()`. `name_key` es el nombre normalizado por el dominio (mayúsculas, sin tildes y con un solo espacio) y un constraint único sobre `name_key` MUST impedir dos tratamientos con el mismo nombre. Un CHECK MUST exigir `char_length(name) BETWEEN 1 AND 80`.
- La tabla `professional_treatments` con `professional_id` FK a `professionals.id` y `treatment_id` FK a `treatments.id`, clave primaria compuesta `(professional_id, treatment_id)` e índice sobre `treatment_id`.
- La columna `appointments.treatment_id` uuid NULL, FK a `treatments.id`, con índice.

Todas las FK MUST ser `ON DELETE RESTRICT` (DD-39). La migración MUST NOT cambiar el constraint `ex_appointments_no_overlap`, el tipo `appointment_status` ni ninguna columna existente, y MUST NOT completar `treatment_id` en los turnos existentes. La reversión MUST fallar con un mensaje claro si algún turno tiene tratamiento; sin turnos con tratamiento, MUST dejar el esquema como en `0004`.

#### Scenario: Turno con tratamiento (esperado)
- **WHEN** se inserta un turno con un `treatment_id` existente
- **THEN** la base lo acepta

#### Scenario: Turno anterior sin tratamiento (borde)
- **WHEN** se aplica `0005` sobre una base con turnos
- **THEN** los turnos existentes quedan con `treatment_id` nulo y sin otros cambios

#### Scenario: Tratamiento inexistente (error)
- **WHEN** se inserta un turno con un `treatment_id` que no existe
- **THEN** la base lo rechaza por la FK

#### Scenario: Nombre repetido con otra mayúscula o tilde (error)
- **WHEN** existe "Extracción" y se inserta "EXTRACCION", que tiene el mismo `name_key`
- **THEN** la base lo rechaza por el constraint único

#### Scenario: Borrar un tratamiento usado (error)
- **WHEN** se intenta borrar un tratamiento que tiene un turno o un profesional asociado
- **THEN** la base lo rechaza por `ON DELETE RESTRICT`

#### Scenario: Asignación repetida (borde)
- **WHEN** se inserta dos veces el mismo par profesional y tratamiento
- **THEN** la base rechaza la segunda por la clave primaria

#### Scenario: La regla de no superposición no cambia (regla dura 6)
- **WHEN** se insertan dos turnos `scheduled` superpuestos del mismo profesional con tratamientos distintos
- **THEN** la base rechaza el segundo por `ex_appointments_no_overlap`

#### Scenario: Reversión con turnos con tratamiento (error)
- **WHEN** se revierte `0005` y hay un turno con tratamiento
- **THEN** la reversión falla y no borra nada
