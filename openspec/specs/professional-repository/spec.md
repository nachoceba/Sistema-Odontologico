# professional-repository Specification

## Purpose
Dar a los changes de horarios y turnos (C-07, C-08) una forma única de leer las fichas de los profesionales (listado y búsqueda por id) que se comporte igual en memoria y en PostgreSQL, verificada por una batería de contrato común.

## Requirements

### Requirement: Listar fichas de profesionales

El repositorio de profesionales SHALL devolver las fichas con su id, id de cuenta, nombre a mostrar, matrícula (vacía si no tiene) y estado activo, ordenadas por nombre a mostrar sin distinguir mayúsculas. Con el filtro "solo activas" MUST omitir las fichas con `active = false`. Las implementaciones en memoria y PostgreSQL MUST pasar la misma batería de contrato.

#### Scenario: Listado con el seed (esperado)
- **WHEN** se listan las fichas sobre los dos profesionales cargados
- **THEN** se obtienen las dos ordenadas por nombre a mostrar, cada una con el id de su cuenta

#### Scenario: Solo activas (borde)
- **WHEN** una de las dos fichas está desactivada y se pide el listado de solo activas
- **THEN** se obtiene únicamente la ficha activa

#### Scenario: Sin fichas (borde)
- **WHEN** no hay ninguna ficha cargada
- **THEN** el listado es vacío, sin error

### Requirement: Buscar una ficha por identificador

El repositorio de profesionales SHALL devolver la ficha con el identificador pedido, activa o no. Un identificador inexistente o mal formado MUST devolver "sin resultado" sin lanzar error.

#### Scenario: Ficha existente (esperado)
- **WHEN** se busca por el id de la ficha de un odontólogo del seed
- **THEN** se obtiene su ficha con su nombre a mostrar y el id de su cuenta

#### Scenario: Identificador inexistente (error)
- **WHEN** se busca por un UUID válido que no corresponde a ninguna ficha
- **THEN** el resultado es "sin resultado"

#### Scenario: Identificador mal formado (borde)
- **WHEN** se busca por un texto que no es un UUID
- **THEN** el resultado es "sin resultado" sin error de base de datos

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
