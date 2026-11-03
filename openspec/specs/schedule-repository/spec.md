# schedule-repository Specification

## Purpose
Definir el contrato para leer y reemplazar los tramos de horario de un profesional y para listar y agregar sus licencias sin depender de la base de datos, con una batería de pruebas que cualquier implementación debe cumplir.

## Requirements

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

### Requirement: Leer y reemplazar los tramos de horario de un profesional

Leer los tramos SHALL devolver todos los tramos del profesional ordenados por día de la semana y hora de inicio, o una lista vacía si no tiene. Reemplazar SHALL sustituir el conjunto completo de tramos del profesional en una sola operación (el administrador edita la semana entera, US-004) sin tocar los de otros profesionales. El repositorio no valida los tramos: el caso de uso (C-07) MUST validarlos antes con `schedule-validation`; pasar tramos inválidos es un error del llamador y su resultado no forma parte del contrato.

#### Scenario: Reemplazar y leer la semana de un profesional (esperado)
- **DADO** un repositorio vacío
- **CUANDO** se reemplazan los tramos de la Dra. A por: martes 14:00–18:00, lunes 14:00–18:00 y lunes 09:00–13:00
- **ENTONCES** leer los tramos de la Dra. A devuelve lunes 09:00–13:00, lunes 14:00–18:00 y martes 14:00–18:00, en ese orden

#### Scenario: Un nuevo reemplazo descarta los tramos anteriores (esperado)
- **DADO** la Dra. A con tramos lunes 09:00–13:00 y martes 09:00–13:00
- **CUANDO** se reemplazan sus tramos por miércoles 09:00–13:00
- **ENTONCES** leer los tramos de la Dra. A devuelve solo miércoles 09:00–13:00

#### Scenario: Reemplazar un profesional no toca a otro (borde)
- **DADO** la Dra. A y el Dr. B con tramos lunes 09:00–13:00
- **CUANDO** se reemplazan los tramos de la Dra. A por una lista vacía
- **ENTONCES** la Dra. A no tiene tramos y el Dr. B sigue con lunes 09:00–13:00

#### Scenario: Profesional sin horario cargado (borde)
- **DADO** un repositorio vacío
- **CUANDO** se leen los tramos del Dr. B
- **ENTONCES** se devuelve una lista vacía

### Requirement: Listar y agregar licencias de un profesional

Agregar una licencia SHALL recibir profesional, fecha de inicio, fecha de fin (ambas inclusivas) y un motivo opcional (US-005), y MUST devolver la licencia guardada con un identificador nuevo. Listar SHALL devolver todas las licencias del profesional con su identificador y motivo, ordenadas por fecha de inicio, sin filtrar por fecha actual (DD-28: licencias pasadas o superpuestas se aceptan). Cada licencia guardada MUST poder convertirse al dato de licencia que ya consumen `validate_appointment`, `compute_slots` e `is_date_in_time_off`. Una licencia con fin anterior al inicio MUST rechazarse como error de programación (`ValueError`), equivalente al `CHECK (starts_on <= ends_on)`; el caso de uso la valida antes con `schedule-validation`.

#### Scenario: Agregar y listar licencias con motivo (esperado)
- **DADO** un repositorio vacío
- **CUANDO** se agregan a la Dra. A una licencia del 12 al 16 de octubre de 2026 con motivo "Congreso" y otra del 5 al 5 de octubre sin motivo
- **ENTONCES** listar las licencias de la Dra. A devuelve primero la del 5 de octubre (sin motivo) y luego la del 12 al 16 (motivo "Congreso"), cada una con identificador distinto

#### Scenario: Licencias de otro profesional no aparecen (borde)
- **DADO** una licencia del Dr. B del 12 al 16 de octubre
- **CUANDO** se listan las licencias de la Dra. A
- **ENTONCES** se devuelve una lista vacía

#### Scenario: Licencias superpuestas se guardan las dos (borde)
- **DADO** una licencia de la Dra. A del 12 al 16 de octubre
- **CUANDO** se agrega otra de la Dra. A del 14 al 20 de octubre
- **ENTONCES** listar devuelve ambas (DD-28)

#### Scenario: Licencia con fin anterior al inicio (borde)
- **DADO** un repositorio vacío
- **CUANDO** se intenta agregar a la Dra. A una licencia del 16 al 12 de octubre
- **ENTONCES** se lanza `ValueError` y la Dra. A sigue sin licencias

#### Scenario: Las licencias guardadas bloquean la disponibilidad (esperado)
- **DADO** la Dra. A con tramo lunes 09:00–13:00 y una licencia guardada del 5 al 5 de octubre
- **CUANDO** los tramos y las licencias leídos del repositorio, convertidos, se pasan al cálculo de franjas del lunes 5 de octubre
- **ENTONCES** todas las franjas salen `OUTSIDE_HOURS` (RN-HO-03, DD-15)
