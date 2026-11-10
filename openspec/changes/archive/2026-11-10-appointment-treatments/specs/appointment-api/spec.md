# Spec Delta: appointment-api

## ADDED Requirements

### Requirement: Tratamiento en los pedidos y respuestas de turnos (C-17)

`POST /api/v1/appointments` SHALL exigir `treatment_id` en el cuerpo, junto a `patient_id`, `professional_id` y `starts_at`; sin él, la respuesta MUST ser 422. Las respuestas de turnos MUST incluir `treatment_id` (nulo en turnos anteriores). El listado y el detalle (`GET /api/v1/appointments` y `GET /api/v1/appointments/{appointment_id}`) MUST incluir además `treatment_name`, el nombre vigente del tratamiento o nulo. `POST /api/v1/appointments/{appointment_id}/reschedule` MUST NOT cambiar el tratamiento: su cuerpo sigue siendo `{starts_at}` y un `treatment_id` enviado se ignora, como cualquier campo desconocido de ese cuerpo. Los rechazos nuevos son 404 `TREATMENT_NOT_FOUND` y 409 `TREATMENT_NOT_AVAILABLE`, con el cuerpo uniforme y mensajes en castellano. Los permisos de cada ruta no cambian.

#### Scenario: Agendar con tratamiento (esperado)
- **WHEN** la recepción hace `POST /api/v1/appointments` con un tratamiento que ofrece el profesional
- **THEN** la respuesta es 201 con `treatment_id` igual al enviado

#### Scenario: Agendar sin tratamiento (error)
- **WHEN** la recepción hace `POST /api/v1/appointments` sin `treatment_id`
- **THEN** la respuesta es 422 y no se crea ningún turno

#### Scenario: Tratamiento no ofrecido (error de negocio)
- **WHEN** la recepción agenda con un tratamiento que el profesional no ofrece
- **THEN** la respuesta es 409 con `error.code = "TREATMENT_NOT_AVAILABLE"`

#### Scenario: Listado con nombre del tratamiento (esperado)
- **WHEN** el odontólogo lista sus turnos del día
- **THEN** cada turno trae `treatment_name`, nulo en los turnos anteriores

#### Scenario: Nombre vigente (borde)
- **WHEN** el administrador cambió "Limpieza" a "Limpieza dental" después de agendar
- **THEN** el detalle del turno muestra "Limpieza dental"

#### Scenario: Reprogramar no cambia el tratamiento (error)
- **WHEN** se manda `POST /api/v1/appointments/{id}/reschedule` con `treatment_id`
- **THEN** el turno se mueve y conserva su tratamiento original
