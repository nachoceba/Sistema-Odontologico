# Spec Delta: schedule-repository

## ADDED Requirements

### Requirement: Borrar una licencia de un profesional

El repositorio de licencias SHALL permitir borrar una licencia indicando el profesional y el identificador de la licencia (P-4), y MUST informar si la borró. Una licencia inexistente, con identificador mal formado o que pertenece a otro profesional MUST informar "no se borró" sin cambiar nada. Borrar MUST NOT tocar otras licencias ni los tramos de horario. Las implementaciones en memoria y PostgreSQL MUST pasar la misma batería de contrato.

#### Scenario: Borrar una licencia propia (esperado)
- **DADO** la Dra. A con una licencia del 12 al 16 de octubre y otra del 5 al 5 de octubre
- **CUANDO** se borra la del 12 al 16
- **ENTONCES** se informa que se borró y listar las licencias de la Dra. A devuelve solo la del 5 de octubre

#### Scenario: Licencia de otro profesional (borde)
- **DADO** una licencia del Dr. B del 12 al 16 de octubre
- **CUANDO** se intenta borrarla indicando a la Dra. A como profesional
- **ENTONCES** se informa que no se borró y la licencia del Dr. B sigue guardada

#### Scenario: Identificador inexistente o mal formado (borde)
- **DADO** un repositorio con una licencia de la Dra. A
- **CUANDO** se intenta borrar un UUID que no existe o un texto que no es un UUID
- **ENTONCES** se informa que no se borró, sin error de base de datos, y la licencia sigue guardada

#### Scenario: Borrar devuelve la disponibilidad (esperado)
- **DADO** la Dra. A con tramo lunes 09:00–13:00 y una licencia del 5 al 5 de octubre
- **CUANDO** se borra la licencia y se calculan las franjas del lunes 5 de octubre con lo que queda en los repositorios
- **ENTONCES** las franjas de 09:00 a 13:00 salen `FREE`
