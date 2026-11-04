# Spec Delta: professional-schedule-use-cases

## Purpose

Orquestar la administración de las fichas de profesionales, sus horarios semanales y sus licencias (US-004, US-005, Flujo 5): validar con las reglas puras de horarios, guardar por los repositorios, aplicar el alcance por rol y listar los turnos en conflicto sin cancelarlos (RN-HO-04).

## ADDED Requirements

### Requirement: Listar y ver fichas de profesionales

Listar fichas SHALL devolver todas las fichas, activas e inactivas, con su estado, ordenadas por nombre a mostrar (P-7). Para un odontólogo, el listado MUST contener solo su propia ficha, y MUST ser vacío si no tiene ficha (RN-AU-04, DD-53). Ver una ficha por identificador MUST devolverla a administración y recepción aunque esté inactiva; un odontólogo MUST recibir `FORBIDDEN` con una ficha ajena o un identificador mal formado (DD-53). Una ficha inexistente MUST responder `PROFESSIONAL_NOT_FOUND` a administración y recepción.

#### Scenario: Recepción lista todas las fichas (esperado)
- **WHEN** recepción lista las fichas y la del Dr. B está inactiva
- **THEN** obtiene la Dra. A y el Dr. B, ordenados por nombre, con el Dr. B marcado como inactivo

#### Scenario: Odontóloga lista solo la suya (esperado)
- **WHEN** la Dra. A lista las fichas
- **THEN** obtiene únicamente su ficha

#### Scenario: Odontólogo sin ficha (borde)
- **WHEN** un odontólogo sin ficha de profesional lista las fichas
- **THEN** obtiene una lista vacía, sin error

#### Scenario: Odontóloga pide una ficha ajena (error de negocio)
- **WHEN** la Dra. A pide la ficha del Dr. B
- **THEN** recibe `FORBIDDEN` y no se le devuelve ningún dato del Dr. B

#### Scenario: Ficha inexistente (error de negocio)
- **WHEN** el administrador pide una ficha con un identificador que no existe
- **THEN** recibe `PROFESSIONAL_NOT_FOUND`

### Requirement: Editar la ficha del profesional

Solo el administrador SHALL poder editar el nombre a mostrar y la matrícula de una ficha (DD-60, matriz RBAC). Los campos no enviados MUST quedar como estaban. El nombre a mostrar MUST tener de 1 a 200 caracteres tras recortar espacios; la matrícula MUST tener de 1 a 50 caracteres tras recortar, o quedar vacía si se pide borrarla (P-8). La edición MUST NOT cambiar el estado activo de la ficha (eso sigue la cuenta, DD-59) ni sus turnos, horarios o licencias. Una ficha inactiva MUST poder editarse (P-6).

#### Scenario: Corregir el nombre a mostrar (esperado)
- **WHEN** el administrador cambia el nombre a mostrar de la Dra. A a "Dra. Ana Pérez"
- **THEN** la ficha queda con ese nombre, la misma matrícula y el mismo estado, y los turnos de la Dra. A no cambian

#### Scenario: Borrar la matrícula (borde)
- **WHEN** el administrador pide dejar sin matrícula la ficha del Dr. B
- **THEN** la ficha queda sin matrícula y con el mismo nombre

#### Scenario: Editar una ficha inactiva (borde)
- **WHEN** el administrador edita la matrícula de la ficha inactiva del Dr. B
- **THEN** el cambio se guarda y la ficha sigue inactiva

#### Scenario: Ficha inexistente (error de negocio)
- **WHEN** el administrador edita una ficha que no existe
- **THEN** recibe `PROFESSIONAL_NOT_FOUND` y nada cambia

### Requirement: Leer y reemplazar el horario semanal

Leer el horario SHALL devolver los tramos del profesional ordenados por día de la semana y hora de inicio. Reemplazar el horario SHALL recibir la semana completa (cero o más tramos, varios por día, US-004) y MUST validarla con la validación de tramos (`schedule-validation`: día 0 a 6, minutos exactos, inicio anterior al fin, sin superposición dentro del mismo día; tramos contiguos válidos, DD-27). Si la validación informa algún problema, MUST rechazarse con `INVALID_WORKING_HOURS`, informando cada problema con su código y las posiciones de los tramos involucrados, y el horario guardado MUST NOT cambiar. Si es válida, MUST reemplazar el conjunto completo en una sola operación y devolver el horario guardado junto con los turnos en conflicto calculados con el horario nuevo y las licencias vigentes (`schedule-conflicts`). Los turnos en conflicto MUST NOT cancelarse ni modificarse (RN-HO-04, P-5). Un profesional inexistente MUST responder `PROFESSIONAL_NOT_FOUND`; una ficha inactiva MUST aceptar el cambio (P-6). El horario nuevo MUST regir de inmediato para agendar, reprogramar y calcular franjas (US-004).

#### Scenario: Cargar varios tramos por día (esperado)
- **WHEN** el administrador reemplaza el horario de la Dra. A por lunes 09:00–13:00 y 14:00–18:00 y martes 09:00–13:00
- **THEN** el horario guardado es exactamente esos tres tramos, ordenados, y la lista de conflictos es vacía

#### Scenario: Tramos superpuestos (error de negocio)
- **WHEN** el administrador envía lunes 09:00–13:00 y lunes 12:00–15:00
- **THEN** recibe `INVALID_WORKING_HOURS` con el problema `OVERLAPPING_BLOCKS` sobre los tramos en las posiciones 0 y 1, y el horario anterior de la Dra. A sigue igual

#### Scenario: Inicio posterior al fin (error de negocio)
- **WHEN** el administrador envía un tramo martes 18:00–09:00
- **THEN** recibe `INVALID_WORKING_HOURS` con el problema `START_NOT_BEFORE_END` y nada cambia

#### Scenario: Acortar el horario con turnos afectados (esperado)
- **WHEN** la Dra. A tiene un turno `scheduled` futuro el lunes de 16:00 a 16:30 y el administrador reemplaza su lunes por 09:00–13:00
- **THEN** el horario se guarda, la respuesta lista ese turno con motivo "fuera de horario" y el turno sigue `scheduled` con el mismo horario

#### Scenario: Vaciar la semana (borde)
- **WHEN** el administrador reemplaza el horario del Dr. B por una semana sin tramos
- **THEN** el Dr. B queda sin tramos, todos sus turnos `scheduled` futuros se listan como conflictos y sus franjas de cualquier día salen fuera de horario

#### Scenario: El cambio rige de inmediato (esperado)
- **WHEN** el administrador agrega el tramo miércoles 09:00–13:00 a la Dra. A, que antes no atendía los miércoles
- **THEN** a continuación se puede agendar un turno de la Dra. A el miércoles 7 de octubre a las 09:00 respetando la anticipación mínima, y las franjas de ese miércoles muestran franjas libres

#### Scenario: Cambiar el horario no habilita superponer turnos (borde, regla dura 6)
- **WHEN** la Dra. A tiene un turno `scheduled` el lunes de 10:00 a 10:30 y el administrador cambia su lunes de 09:00–13:00 a 10:00–14:00
- **THEN** el turno no aparece en conflicto y un intento de agendar otro turno de la Dra. A el lunes a las 10:00 se rechaza con `SLOT_TAKEN`

#### Scenario: Profesional inexistente (error de negocio)
- **WHEN** el administrador reemplaza el horario de un profesional que no existe
- **THEN** recibe `PROFESSIONAL_NOT_FOUND` y no se guarda ningún tramo

### Requirement: Listar, cargar y borrar licencias

Listar licencias SHALL devolver todas las licencias del profesional, con identificador, fechas y motivo, ordenadas por fecha de inicio, incluidas las pasadas (DD-28). Cargar una licencia SHALL recibir fecha de inicio y de fin (fechas locales, ambas inclusivas) y un motivo opcional de hasta 500 caracteres tras recortar; un motivo vacío MUST guardarse como "sin motivo" (P-10). Una licencia con fin anterior al inicio MUST rechazarse con `INVALID_TIME_OFF` sin guardar nada (`END_BEFORE_START`). Licencias superpuestas o en el pasado MUST aceptarse (DD-28). Al cargarla MUST devolverse la licencia guardada y los turnos en conflicto calculados con el horario vigente y todas las licencias, incluida la nueva, sin cancelarlos (RN-HO-04). Borrar una licencia (P-4) MUST quitarla del profesional indicado; una licencia inexistente o de otro profesional MUST responder `TIME_OFF_NOT_FOUND` sin borrar nada. Un profesional inexistente MUST responder `PROFESSIONAL_NOT_FOUND`.

#### Scenario: Cargar una licencia con motivo (esperado)
- **WHEN** el administrador carga a la Dra. A una licencia del 12 al 16 de octubre de 2026 con motivo "Congreso" y no tiene turnos esos días
- **THEN** la licencia queda guardada con un identificador nuevo, la lista de conflictos es vacía y las franjas de la Dra. A del 14 de octubre salen fuera de horario (US-005)

#### Scenario: Licencia sobre turnos existentes (esperado)
- **WHEN** la Dra. A tiene dos turnos `scheduled` el 14 de octubre y el administrador carga una licencia del 12 al 16
- **THEN** la licencia se guarda, la respuesta lista los dos turnos con motivo "en licencia" y ambos siguen `scheduled`

#### Scenario: Fin anterior al inicio (error de negocio)
- **WHEN** el administrador carga una licencia del 16 al 12 de octubre
- **THEN** recibe `INVALID_TIME_OFF` y la Dra. A no tiene licencias nuevas

#### Scenario: Licencia de un solo día y licencia pasada (borde)
- **WHEN** el administrador carga una licencia del 5 al 5 de octubre y otra de un mes ya pasado
- **THEN** se guardan las dos (DD-28)

#### Scenario: Motivo vacío (borde)
- **WHEN** el administrador carga una licencia con motivo formado solo por espacios
- **THEN** se guarda sin motivo

#### Scenario: Borrar una licencia cargada por error (esperado)
- **WHEN** el administrador borra la licencia del 12 al 16 de octubre de la Dra. A
- **THEN** la licencia ya no figura en su listado y las franjas del 14 de octubre vuelven a mostrar franjas libres según su horario

#### Scenario: Borrar una licencia de otro profesional (error de negocio)
- **WHEN** el administrador pide borrar, bajo la Dra. A, una licencia que pertenece al Dr. B
- **THEN** recibe `TIME_OFF_NOT_FOUND` y la licencia del Dr. B sigue guardada

### Requirement: Consultar los turnos en conflicto

Consultar los conflictos de un profesional SHALL devolver, en el momento del pedido, los turnos `scheduled` que todavía no empezaron y que quedan fuera de su horario vigente o dentro de alguna licencia (`schedule-conflicts`), con su motivo, ordenados por inicio (P-1: se calculan, no se guardan). Un turno deja de figurar en cuanto se cancela, se reprograma a un horario válido o se corrige el horario o la licencia. Administración y recepción MUST poder consultar cualquier profesional; un odontólogo, solo el propio (RN-AU-04).

#### Scenario: Recepción ve los conflictos pendientes (esperado)
- **WHEN** la Dra. A tiene un turno futuro el lunes a las 16:00 y su horario del lunes es 09:00–13:00
- **THEN** recepción consulta los conflictos de la Dra. A y obtiene ese turno con motivo "fuera de horario"

#### Scenario: Resolver el conflicto lo saca de la lista (esperado)
- **WHEN** recepción cancela ese turno con un motivo, o lo reprograma al lunes a las 10:00 libre
- **THEN** al consultar de nuevo, los conflictos de la Dra. A son vacíos

#### Scenario: Odontóloga consulta conflictos ajenos (error de negocio)
- **WHEN** la Dra. A consulta los conflictos del Dr. B
- **THEN** recibe `FORBIDDEN`

#### Scenario: Profesional sin conflictos (borde)
- **WHEN** todos los turnos futuros del Dr. B entran en su horario y ninguno cae en licencia
- **THEN** la consulta devuelve una lista vacía

### Requirement: Solo el administrador escribe horarios, licencias y fichas (DD-48)

Editar la ficha, reemplazar el horario, cargar y borrar licencias SHALL estar permitidos solo al rol administrador. Recepción y odontólogo MUST recibir `FORBIDDEN` y nada MUST cambiar. Leer fichas, horarios, licencias y conflictos MUST estar permitido a administración y recepción para cualquier profesional, y al odontólogo solo para el propio (DD-53). El chequeo de permiso MUST ocurrir antes que cualquier validación de los datos enviados o búsqueda del profesional.

#### Scenario: Recepción intenta cambiar un horario (error de negocio)
- **WHEN** recepción intenta reemplazar el horario de la Dra. A
- **THEN** recibe `FORBIDDEN` y el horario no cambia

#### Scenario: Odontóloga intenta cargar su propia licencia (error de negocio)
- **WHEN** la Dra. A intenta cargarse una licencia
- **THEN** recibe `FORBIDDEN` y no se guarda nada (solo el administrador edita, DD-48)

#### Scenario: Odontóloga lee su propio horario (esperado)
- **WHEN** la Dra. A lee su horario y sus licencias
- **THEN** obtiene sus tramos y sus licencias
