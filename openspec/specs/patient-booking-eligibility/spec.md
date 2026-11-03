# patient-booking-eligibility Specification

## Purpose
Decidir, sin base de datos, si un paciente puede recibir un turno nuevo según su estado activo o inactivo (RN-PA-04), como regla separada de la validación del horario del turno.

## Requirements
> Todos los datos son ficticios. Las decisiones de dominio P-1 a P-10 fueron confirmadas por el usuario (ver `design.md` y DD-21 a DD-30 en la KB).

### Requirement: Paciente inactivo no recibe turnos nuevos (RN-PA-04)

La decisión SHALL recibir si el paciente está activo y devolver un resultado aceptado o rechazado, sin lanzar excepciones por motivos de negocio. Un paciente activo MUST aceptarse. Un paciente inactivo (`active = false`, RN-PA-03) MUST rechazarse con el motivo `PATIENT_INACTIVE`. Esta regla es independiente de las reglas de horario de `appointment-creation`: no cambia su orden de evaluación ni sus motivos. Si también aplica al reprogramar es una decisión del caso de uso.

#### Scenario: Paciente activo (funcionamiento esperado)
- **DADO** el paciente ficticio Juan Pérez con `active = true`
- **CUANDO** se pregunta si puede recibir un turno nuevo
- **ENTONCES** el resultado es aceptado

#### Scenario: Paciente inactivo (error de negocio)
- **DADO** el paciente ficticio Ana Gómez con `active = false`
- **CUANDO** se pregunta si puede recibir un turno nuevo
- **ENTONCES** se rechaza con el motivo `PATIENT_INACTIVE` (RN-PA-04)

#### Scenario: Valor de actividad que no es booleano (borde)
- **DADO** un valor de actividad que no es booleano (por ejemplo `None` o el texto `"false"`)
- **CUANDO** se pregunta si puede recibir un turno nuevo
- **ENTONCES** se lanza `ValueError` (error de programación; un texto `"false"` no se interpreta como verdadero)
