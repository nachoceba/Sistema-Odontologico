# Spec Delta: appointment-use-cases

## MODIFIED Requirements

### Requirement: Consultar turnos

El sistema SHALL permitir leer un turno por identificador y listar los turnos de un profesional en un rango `[desde, hasta)` de instantes, en cualquier estado y ordenados por inicio (DD-31, DD-35). Cada turno leído o listado MUST venir acompañado del nombre y el apellido de su paciente, tal como están guardados en ese momento, aunque el paciente esté inactivo (P-1 de C-09, CONFIRMADA (2026-11-04)); MUST NOT incluir otros datos del paciente (email, teléfono, documento ni fecha de nacimiento). Un odontólogo MUST NOT leer turnos de otro profesional ni listarlos: se rechaza con `FORBIDDEN` (DD-53), sin revelar datos del paciente. Un turno inexistente se informa como `APPOINTMENT_NOT_FOUND`. Un listado con `desde` no anterior a `hasta`, o con un rango de más de 31 días, se rechaza como pedido inválido. Consultar MUST NOT modificar ningún turno, notificación ni paciente.

#### Scenario: Recepción lista la semana de la Dra. A (esperado)
- **WHEN** recepción lista los turnos de la Dra. A del lunes 00:00 al lunes siguiente 00:00 (hora del consultorio)
- **THEN** recibe todos los turnos de esa semana, incluidos cancelados y atendidos, ordenados por inicio, cada uno con el nombre y el apellido de su paciente

#### Scenario: Odontóloga lee un turno ajeno (error de negocio)
- **WHEN** la Dra. A pide el detalle de un turno del Dr. B
- **THEN** se rechaza con `FORBIDDEN` y no recibe ningún dato del paciente

#### Scenario: Turno que cruza el límite del rango (borde)
- **WHEN** se listan los turnos de un día y un turno empieza 15 minutos antes del inicio del rango y termina dentro
- **THEN** el turno aparece en el listado

#### Scenario: Paciente inactivo sigue nombrado (borde)
- **WHEN** Juan Perez tiene un turno `scheduled` con la Dra. A, se lo desactiva y recepción lista ese día
- **THEN** el turno aparece con "Juan" y "Perez" y sigue `scheduled`

#### Scenario: El nombre es el vigente (borde)
- **WHEN** se corrige el apellido de un paciente después de agendarle un turno y se vuelve a listar
- **THEN** el turno aparece con el apellido corregido

#### Scenario: Solo nombre y apellido (esperado)
- **WHEN** la Dra. A lista sus turnos de un día
- **THEN** cada turno trae nombre y apellido del paciente y ningún email, teléfono, documento ni fecha de nacimiento

#### Scenario: Consultar no cambia nada (borde)
- **WHEN** recepción lista los turnos de una semana y lee el detalle de uno
- **THEN** ningún turno, notificación ni paciente cambió (regla dura 6)
