# Spec Delta: appointment-use-cases

## ADDED Requirements

### Requirement: Tratamiento al agendar y al reprogramar (DD-142, DD-144, DD-148)

Agendar un turno SHALL exigir un tratamiento válido según `treatment-management`. El chequeo del tratamiento MUST hacerse después de comprobar que el paciente y el profesional existen y están activos, y antes de las reglas de horario: un tratamiento inexistente responde `TREATMENT_NOT_FOUND` y uno inactivo o no ofrecido por el profesional responde `TREATMENT_NOT_AVAILABLE`, sin escribir nada. El turno se guarda con el tratamiento en la misma transacción que su confirmación por email. Las reglas de horario, de grilla, de anticipación y de superposición (del profesional y del paciente) MUST ser las mismas que antes, y un choque con otro turno MUST seguir respondiendo `SLOT_TAKEN` por el constraint de la base.

Reprogramar MUST conservar el tratamiento del turno sin volver a validarlo (aunque se haya desactivado o quitado al profesional) y MUST NOT permitir cambiarlo. Un turno sin tratamiento se reprograma igual que antes. Ningún caso de uso cambia el tratamiento de un turno existente. Cancelar y marcar atención no cambian.

#### Scenario: Agendar con tratamiento (esperado)
- **WHEN** la recepción agenda a Juan Perez con la Dra. A el lunes a las 10:00 con "Limpieza dental"
- **THEN** el turno queda `scheduled` con ese tratamiento y se registra su confirmación

#### Scenario: Tratamiento no ofrecido (error de negocio)
- **WHEN** la recepción agenda con el Dr. B el tratamiento "Blanqueamiento", que él no ofrece
- **THEN** se rechaza con `TREATMENT_NOT_AVAILABLE` y no se guarda nada

#### Scenario: Tratamiento inexistente (error)
- **WHEN** la recepción agenda con un tratamiento que no existe
- **THEN** se rechaza con `TREATMENT_NOT_FOUND`

#### Scenario: Orden de los rechazos (borde)
- **WHEN** la recepción agenda con un tratamiento inactivo en un horario fuera de la grilla
- **THEN** se rechaza con `TREATMENT_NOT_AVAILABLE`, porque el tratamiento se chequea antes que el horario

#### Scenario: Dos recepcionistas, mismo horario, distinto tratamiento (regla dura 6)
- **WHEN** dos recepcionistas agendan al mismo tiempo el mismo horario de la Dra. A con tratamientos distintos
- **THEN** uno queda guardado y el otro recibe `SLOT_TAKEN`

#### Scenario: Reprogramar conserva el tratamiento (esperado)
- **WHEN** la recepción reprograma un turno de "Extracción" al día siguiente
- **THEN** el turno movido sigue con "Extracción"

#### Scenario: Reprogramar con el tratamiento desactivado (borde)
- **WHEN** se desactivó "Blanqueamiento" y la recepción reprograma un turno que lo tiene
- **THEN** se reprograma y conserva "Blanqueamiento"
