# Spec Delta: frontend-appointment-management

## ADDED Requirements

### Requirement: Acciones sobre un turno pendiente de confirmación (DD-133)

En el detalle de un turno pendiente de confirmación, la recepción y el administrador SHALL ver "Pendiente de confirmación hasta las HH:MM" (hora local) y solo la acción "Cancelar", con el mismo diálogo de motivo. Nunca MUST ver "Reprogramar" ni "Marcar atendido o ausente". El odontólogo ve el detalle sin acciones. Ante un `PENDING_CONFIRMATION` de la API, la pantalla MUST mostrar "Este turno espera la confirmación del paciente." y recargar el turno.

#### Scenario: Detalle de un pendiente para la recepción (esperado)
- **WHEN** la recepción abre un turno pendiente que vence a las 13:00
- **THEN** ve "Pendiente de confirmación hasta las 13:00" y solo "Cancelar"

#### Scenario: Pendiente para el odontólogo (borde)
- **WHEN** el odontólogo abre un turno propio pendiente
- **THEN** ve el detalle sin acciones

#### Scenario: Se venció mientras estaba abierto (error)
- **WHEN** la recepción cancela un pendiente que la tarea ya canceló
- **THEN** ve el mensaje de turno ya cancelado de siempre y el turno recargado
