# Spec Delta: professional-repository

## ADDED Requirements

### Requirement: Editar nombre a mostrar y matrícula de una ficha

El repositorio de profesionales SHALL permitir cambiar el nombre a mostrar y la matrícula de una ficha existente, por separado o juntos, y MUST devolver la ficha actualizada. Un campo que no se pide cambiar MUST quedar igual; la matrícula MUST poder dejarse vacía. El cambio MUST NOT tocar el estado activo, la cuenta asociada ni otras fichas. Un identificador inexistente o mal formado MUST rechazarse con `PROFESSIONAL_NOT_FOUND` sin cambiar nada. Las implementaciones en memoria y PostgreSQL MUST pasar la misma batería de contrato, y en memoria la ficha editada MUST verse igual desde el repositorio de cuentas (que comparte las fichas).

#### Scenario: Cambiar el nombre a mostrar (esperado)
- **WHEN** se cambia el nombre a mostrar de la ficha de la Dra. A a "Dra. Ana Pérez"
- **THEN** buscarla por id devuelve el nombre nuevo, la misma matrícula, el mismo id de cuenta y el mismo estado, y el listado la ordena por el nombre nuevo

#### Scenario: Dejar la matrícula vacía (borde)
- **WHEN** se pide dejar sin matrícula la ficha del Dr. B
- **THEN** buscarla devuelve la matrícula vacía y el nombre sin cambios

#### Scenario: Ficha inactiva (borde)
- **WHEN** se cambia la matrícula de una ficha desactivada
- **THEN** el cambio se guarda y la ficha sigue desactivada

#### Scenario: Identificador inexistente o mal formado (error)
- **WHEN** se intenta editar con un UUID que no corresponde a ninguna ficha, o con un texto que no es un UUID
- **THEN** se rechaza con `PROFESSIONAL_NOT_FOUND` y ninguna ficha cambia
