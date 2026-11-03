# Spec Delta

## Purpose

Definir el contrato mínimo para consultar un paciente por identificador y saber si existe y si está activo, que es lo que necesitan los casos de uso de turnos para aplicar RN-PA-04 sin depender de la base de datos.

## ADDED Requirements

> Todos los datos son ficticios: Juan Pérez (`pac-1`, activo, `juan.perez@example.com`) y Ana Gómez (`pac-2`, inactiva, `ana.gomez@example.com`). El alcance de este repositorio depende de la pregunta de `design.md`: alta, búsqueda por apellido o documento y unicidad del documento (RN-PA-01) son de C-06.

### Requirement: Contrato único para pacientes

Toda implementación del repositorio de pacientes SHALL cumplir los escenarios de esta spec; la batería de contrato MUST poder ejecutarse sin cambios contra cada implementación registrada.

#### Scenario: La batería corre contra cada implementación (esperado)
- **DADO** la batería de contrato de pacientes y la lista de implementaciones registradas
- **CUANDO** se ejecuta la batería
- **ENTONCES** cada escenario corre una vez por implementación y todos pasan

### Requirement: Buscar un paciente por identificador

Buscar un paciente SHALL devolver su identificador, nombre, apellido, email y si está activo, o un valor "no encontrado" si no existe (no es un error). El dato `active` devuelto MUST ser booleano, para poder pasarlo tal cual a la regla de `patient-booking-eligibility`.

#### Scenario: Paciente activo (esperado)
- **DADO** el paciente Juan Pérez cargado como activo
- **CUANDO** se lo busca por su identificador
- **ENTONCES** se devuelve con nombre, apellido, email y `active = true`

#### Scenario: Paciente inactivo, listo para la regla RN-PA-04 (error de negocio)
- **DADO** la paciente Ana Gómez cargada como inactiva
- **CUANDO** se la busca y su `active` se pasa a la regla de elegibilidad
- **ENTONCES** la regla rechaza con `PATIENT_INACTIVE`

#### Scenario: Paciente inexistente (borde)
- **DADO** un repositorio con Juan Pérez
- **CUANDO** se busca un identificador que no existe
- **ENTONCES** el resultado es "no encontrado", sin error
