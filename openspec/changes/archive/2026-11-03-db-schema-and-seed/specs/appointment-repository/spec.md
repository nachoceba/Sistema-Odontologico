# Spec Delta

## MODIFIED Requirements

### Requirement: Contrato único para todas las implementaciones

Toda implementación del repositorio de turnos SHALL cumplir los escenarios de esta spec. La batería de pruebas de contrato MUST ejecutarse contra cada implementación registrada (la de memoria y la de PostgreSQL) y MUST partir de un repositorio vacío en cada escenario. Las referencias a profesionales, pacientes y usuarios que usa la batería (Dra. A, Dr. B, Juan Pérez, Ana Gómez, recepción) MUST obtenerse de la fábrica de cada implementación, que garantiza que existan donde la implementación lo exige (claves foráneas de la base); los escenarios MUST NOT depender del formato de los identificadores. Los escenarios de PostgreSQL corren contra la base real con la migración aplicada y solo cuando se piden los tests de integración.

#### Scenario: La misma batería corre contra cada implementación (esperado)
- **DADO** la batería de contrato del repositorio de turnos y la lista de implementaciones registradas
- **CUANDO** se ejecuta la batería
- **ENTONCES** cada escenario corre una vez por implementación, con un repositorio vacío, y todos pasan

#### Scenario: La implementación PostgreSQL solo corre a pedido (borde)
- **DADO** la batería de contrato con las implementaciones de memoria y de PostgreSQL
- **CUANDO** se corre la batería por defecto, sin pedir los tests de integración
- **ENTONCES** solo corren los escenarios de la implementación en memoria, y los de PostgreSQL se ejecutan al pedir los tests de integración con la base levantada

#### Scenario: Identificador con formato que la base no usa (borde)
- **DADO** el repositorio de PostgreSQL con un turno guardado
- **CUANDO** se busca el turno `no-existe`, o se intenta cambiar su estado
- **ENTONCES** la búsqueda devuelve "no encontrado" sin error y el cambio de estado se rechaza con `APPOINTMENT_NOT_FOUND`, igual que en memoria
