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
