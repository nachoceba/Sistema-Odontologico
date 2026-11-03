# Spec Delta

## MODIFIED Requirements

### Requirement: Contrato único para pacientes

Toda implementación del repositorio de pacientes SHALL cumplir los escenarios de esta spec; la batería de contrato MUST ejecutarse contra cada implementación registrada (la de memoria y la de PostgreSQL). Los pacientes iniciales de cada escenario MUST cargarse a través de la fábrica, que completa los datos que la base exige y la batería no usa (por ejemplo, un documento ficticio único), y la batería MUST referirse a ellos por los identificadores que devuelve la fábrica.

#### Scenario: La batería corre contra cada implementación (esperado)
- **DADO** la batería de contrato de pacientes y la lista de implementaciones registradas
- **CUANDO** se ejecuta la batería
- **ENTONCES** cada escenario corre una vez por implementación y todos pasan

#### Scenario: Identificador con formato que la base no usa (borde)
- **DADO** el repositorio de PostgreSQL con Juan Pérez cargado
- **CUANDO** se busca el paciente `no-existe`
- **ENTONCES** el resultado es "no encontrado", sin error
