# Spec Delta: appointment-api

## ADDED Requirements

### Requirement: Origen y confirmación del turno en las respuestas (DD-133)

Toda respuesta de turno de la API interna (agendar, listar, detalle, cancelar, reprogramar y marcar atención) SHALL incluir:

- `origin`: `"staff"` cuando el turno tiene usuario creador y `"online"` cuando no lo tiene. `created_by` MUST ser el identificador del usuario, o `null` en los turnos online.
- `pending_until`: el instante UTC hasta el que se puede confirmar, o `null` si el turno no está pendiente.

Las respuestas MUST NOT incluir nunca el token ni su hash. Los permisos y el resto de los campos no cambian.

#### Scenario: Turno agendado por recepción (esperado)
- **WHEN** la recepción agenda un turno con `POST /api/v1/appointments`
- **THEN** la respuesta trae `origin = "staff"`, `created_by` con el identificador de la recepcionista y `pending_until = null`

#### Scenario: Turno online pendiente en el listado (esperado)
- **WHEN** la recepción lista los turnos de la Dra. A y uno se reservó online y no se confirmó
- **THEN** ese turno trae `origin = "online"`, `created_by = null` y `pending_until` con su vencimiento

#### Scenario: Turno online confirmado (borde)
- **WHEN** el paciente confirmó su reserva
- **THEN** el turno trae `origin = "online"` y `pending_until = null`

#### Scenario: Reprogramar un pendiente por la API (error de negocio)
- **WHEN** la recepción hace `POST /api/v1/appointments/{id}/reschedule` sobre un turno pendiente
- **THEN** la respuesta es 409 con `error.code = "PENDING_CONFIRMATION"`
