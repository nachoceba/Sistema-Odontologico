# Spec Delta

## MODIFIED Requirements

### Requirement: Contrato único para horarios y licencias

Toda implementación de los repositorios de horarios y de licencias SHALL cumplir los escenarios de esta spec; la batería de contrato MUST ejecutarse contra cada implementación registrada (la de memoria y la de PostgreSQL), partiendo de repositorios vacíos. Las referencias a profesionales que usa la batería MUST obtenerse de la fábrica de cada implementación, que garantiza que existan donde la implementación lo exige. Una licencia que termina antes de empezar MUST rechazarse con `ValueError` en todas las implementaciones, antes de llegar a la base.

#### Scenario: La batería corre contra cada implementación (esperado)
- **DADO** la batería de contrato de horarios y licencias y la lista de implementaciones registradas
- **CUANDO** se ejecuta la batería
- **ENTONCES** cada escenario corre una vez por implementación y todos pasan

#### Scenario: Reemplazar tramos en PostgreSQL no deja tramos viejos (borde)
- **DADO** la Dra. A con tramos lunes 09:00–13:00 y martes 09:00–13:00 guardados en PostgreSQL
- **CUANDO** se reemplazan sus tramos por uno solo, lunes 14:00–18:00
- **ENTONCES** al leerlos solo está el lunes 14:00–18:00, y los tramos del Dr. B no cambian
