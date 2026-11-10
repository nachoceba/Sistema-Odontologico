# Spec Delta: frontend-agenda

## ADDED Requirements

### Requirement: Etiquetas de turnos online (DD-133)

En la grilla del día, en la vista de la semana y en el detalle del turno, cada turno `scheduled` con `pending_until` no nulo SHALL mostrar la etiqueta "Pendiente de confirmación", y su franja MUST verse ocupada. Cada turno con `origin = "online"` y sin `pending_until` MUST mostrar la etiqueta "Online" junto a su estado. Los turnos de recepción no llevan etiqueta. Las etiquetas MUST distinguirse por texto, no solo por color.

#### Scenario: Turno pendiente en la grilla (esperado)
- **WHEN** la Dra. A tiene a las 10:30 una reserva online sin confirmar
- **THEN** la grilla muestra la franja ocupada con el turno y la etiqueta "Pendiente de confirmación"

#### Scenario: Turno online confirmado (esperado)
- **WHEN** el paciente confirmó la reserva de las 10:30
- **THEN** la grilla muestra el turno con "Agendado" y la etiqueta "Online"

#### Scenario: Turno de recepción (borde)
- **WHEN** un turno lo agendó la recepción
- **THEN** no muestra ninguna de las dos etiquetas
