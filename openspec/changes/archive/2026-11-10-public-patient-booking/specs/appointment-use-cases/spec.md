# Spec Delta: appointment-use-cases

## ADDED Requirements

### Requirement: Turnos pendientes de confirmación en la recepción (DD-130, DD-133, P-3 y P-6 nuevas)

Un turno pendiente de confirmación SHALL ocupar su franja para todos los casos de uso de agenda. Para la recepción y el administrador:

- **Agendar**: no pueden agendar otro turno en su franja (`SLOT_TAKEN`).
- **Cancelar**: lo pueden cancelar con motivo como cualquier otro turno. Al cancelar, el token se borra, así que el enlace deja de servir.
- **Reprogramar**: MUST NOT poder reprogramarlo; se rechaza con `PENDING_CONFIRMATION`.
- **Confirmar**: no hay confirmación manual; solo lo confirma el paciente desde el enlace.
- **Marcar atención**: MUST rechazarse con `PENDING_CONFIRMATION`, porque un pendiente vence o se confirma antes de empezar. Si su inicio llegó y sigue pendiente, la tarea de vencimiento lo cancela.

#### Scenario: Recepción cancela un pendiente (esperado)
- **WHEN** la recepción cancela con motivo un turno online pendiente
- **THEN** queda `cancelled`, el token deja de servir y la franja se libera

#### Scenario: Recepción intenta agendar sobre un pendiente (error de negocio, regla dura 6)
- **WHEN** la recepción agenda a las 11:00 con la Dra. A y hay un turno pendiente a esa hora
- **THEN** se rechaza con `SLOT_TAKEN`

#### Scenario: Reprogramar un pendiente (error de negocio)
- **WHEN** la recepción reprograma un turno pendiente
- **THEN** se rechaza con `PENDING_CONFIRMATION` y el turno no cambia

#### Scenario: Turno online confirmado (borde)
- **WHEN** la recepción cancela o reprograma un turno online ya confirmado
- **THEN** se aplica lo mismo que a un turno de recepción
