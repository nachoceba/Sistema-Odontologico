# Spec Delta: patient-management

## Purpose

Casos de uso de la gestión de pacientes (US-003): buscar, ver, dar de alta, editar, desactivar, reactivar y borrar, validando con las reglas de `patient-data-rules`, con el alcance de cada rol y sin cambiar nunca un turno.

## ADDED Requirements

### Requirement: Permisos por rol en los casos de uso (matriz RBAC, RN-PR-02, P-4 y P-6 confirmadas)

Cada caso de uso SHALL chequear el rol de quien lo pide, además de la ruta. El administrador MUST poder usar todos. La recepción MUST poder buscar, ver, dar de alta, editar, desactivar y reactivar, y MUST NOT poder borrar. El odontólogo MUST poder buscar y ver a cualquier paciente y MUST NOT poder escribir. Un rechazo MUST ser `FORBIDDEN` y MUST NOT cambiar nada.

#### Scenario: Recepción da de alta (esperado)
- **CUANDO** la recepcionista da de alta a Laura Ruiz con datos válidos
- **ENTONCES** Laura queda guardada y activa

#### Scenario: Odontólogo intenta editar (error de negocio)
- **CUANDO** la Dra. A intenta cambiar el email de Juan Pérez
- **ENTONCES** se rechaza con `FORBIDDEN` y la ficha de Juan no cambia

#### Scenario: Recepción intenta borrar (error de negocio)
- **CUANDO** la recepcionista intenta borrar a un paciente sin turnos
- **ENTONCES** se rechaza con `FORBIDDEN` y el paciente sigue existiendo

#### Scenario: Odontólogo sin ficha de profesional busca (borde)
- **CUANDO** una cuenta `dentist` sin ficha de profesional busca `Pérez`
- **ENTONCES** recibe el resultado igual que otro odontólogo (la lectura de pacientes no depende de la ficha)

### Requirement: Buscar y listar pacientes (US-003, P-3 y P-5 confirmadas)

Buscar SHALL recibir un texto opcional (recortado; vacío equivale a sin texto) y la opción de incluir inactivos, y devolver como máximo 50 pacientes con la regla de búsqueda del repositorio, junto con una indicación de si había más resultados que no se devolvieron.

#### Scenario: Buscar por apellido (esperado)
- **DADO** los 10 pacientes del seed
- **CUANDO** se busca `lopez`
- **ENTONCES** el resultado es Marta López y la indicación "hay más" es falsa

#### Scenario: Más de 50 coincidencias (borde)
- **DADO** 51 pacientes activos
- **CUANDO** se busca sin texto
- **ENTONCES** se devuelven los 50 primeros por apellido y la indicación "hay más" es verdadera

#### Scenario: Texto en blanco (borde)
- **CUANDO** se busca `"   "`
- **ENTONCES** el resultado es el mismo que sin texto

### Requirement: Ver un paciente

Ver SHALL devolver la ficha completa de un paciente, activo o inactivo. Un paciente inexistente MUST rechazarse con `PATIENT_NOT_FOUND`.

#### Scenario: Paciente inactivo (esperado)
- **CUANDO** la recepcionista pide la ficha de Ana Gómez, inactiva
- **ENTONCES** recibe sus datos con `active = false`

#### Scenario: Inexistente (error de negocio)
- **CUANDO** se pide la ficha de `no-existe`
- **ENTONCES** se rechaza con `PATIENT_NOT_FOUND`

### Requirement: Alta de paciente (US-003, RN-PA-01, RN-PA-02)

El alta SHALL validar los datos con `patient-data-rules` (la fecha de nacimiento contra el día de hoy del consultorio, con el reloj del sistema) y guardar el paciente activo. Un documento ya usado por otro paciente, activo o inactivo, MUST rechazarse con `DOCUMENT_TAKEN`. Una fecha de nacimiento futura MUST rechazarse con `INVALID_PATIENT_DATA`. Ningún rechazo MUST guardar nada.

#### Scenario: Alta completa (esperado)
- **CUANDO** se da de alta a Laura Ruiz, documento `40.222.333`, email `Laura@Example.com`, teléfono y fecha de nacimiento 1990-05-10
- **ENTONCES** queda activa con documento `40222333` y email `laura@example.com`

#### Scenario: Documento repetido escrito distinto (error de negocio)
- **DADO** Juan Pérez con documento `30111222`
- **CUANDO** se da de alta a otra persona con documento `30.111.222`
- **ENTONCES** se rechaza con `DOCUMENT_TAKEN` y no se guarda nada

#### Scenario: Fecha de nacimiento futura (error de negocio)
- **DADO** el reloj fijo en 2026-11-04 10:00 en Buenos Aires
- **CUANDO** se da de alta con fecha de nacimiento 2027-01-01
- **ENTONCES** se rechaza con `INVALID_PATIENT_DATA` y no se guarda nada

### Requirement: Edición de paciente (P-9 confirmada)

La edición SHALL cambiar solo los datos enviados, con las mismas validaciones del alta, y MUST permitirse aunque el paciente esté inactivo. El documento y el email MUST poder cambiarse. Cambiar el email MUST NOT tocar turnos ni notificaciones ya registradas. Un documento de otro paciente MUST rechazarse con `DOCUMENT_TAKEN`; un paciente inexistente con `PATIENT_NOT_FOUND`.

#### Scenario: Corregir el email (esperado)
- **DADO** Juan Pérez con un turno agendado y su confirmación `pending` registrada
- **CUANDO** la recepcionista cambia el email de Juan
- **ENTONCES** la ficha tiene el email nuevo y el turno y la notificación siguen iguales

#### Scenario: Editar un paciente inactivo (borde)
- **CUANDO** la recepcionista cambia el teléfono de Ana Gómez, inactiva
- **ENTONCES** se guarda y Ana sigue inactiva

#### Scenario: Documento de otro paciente (error de negocio)
- **CUANDO** se cambia el documento de Luis Fernández al de Juan Pérez
- **ENTONCES** se rechaza con `DOCUMENT_TAKEN` y Luis no cambia

### Requirement: Desactivar sin tocar los turnos (RN-PA-03, RN-PA-04, DD-25, P-7 confirmada)

Desactivar SHALL marcar al paciente inactivo y devolver su ficha junto con la lista de sus turnos `scheduled` que todavía no empezaron (inicio posterior al momento actual; un turno que empieza justo ahora ya está iniciado, DD-23), ordenados por inicio. Desactivar MUST NOT cancelar, mover ni modificar ningún turno ni notificación (DD-25). Desde ese momento, agendar o reprogramar un turno para ese paciente MUST rechazarse con `PATIENT_INACTIVE` (C-08 y DD-25, sin cambios), mientras que cancelar sus turnos MUST seguir permitido. Desactivar a quien ya está inactivo MUST NOT ser un error.

#### Scenario: Paciente con turnos futuros (esperado)
- **DADO** Juan Pérez con un turno `scheduled` mañana con la Dra. A, uno `cancelled` la semana que viene y uno `completed` ayer
- **CUANDO** la recepcionista lo desactiva
- **ENTONCES** queda inactivo, la respuesta lista solo el turno de mañana y los tres turnos siguen con su estado

#### Scenario: Después no se le agenda (error de negocio)
- **DADO** Juan Pérez desactivado
- **CUANDO** se le agenda un turno en una franja libre con el caso de uso de C-08
- **ENTONCES** se rechaza con `PATIENT_INACTIVE` y no se crea ningún turno

#### Scenario: Turno ya iniciado no se lista (borde)
- **DADO** el reloj en 10:15 y Juan Pérez con un turno `scheduled` de 10:00 a 10:30 de hoy
- **CUANDO** se lo desactiva
- **ENTONCES** la lista de turnos futuros es vacía y el turno sigue `scheduled`

#### Scenario: Turno que empieza justo ahora (borde)
- **DADO** el reloj en 10:00:00 y Juan Pérez con un turno `scheduled` que empieza a las 10:00 de hoy y otro a las 10:30
- **CUANDO** se lo desactiva
- **ENTONCES** la lista trae solo el de las 10:30

#### Scenario: Cancelar un turno de un paciente inactivo (borde)
- **DADO** Juan Pérez desactivado con un turno `scheduled` mañana
- **CUANDO** la recepcionista lo cancela con motivo usando el caso de uso de C-08
- **ENTONCES** el turno queda `cancelled` y el slot se libera

#### Scenario: Ya inactivo (borde)
- **CUANDO** se desactiva a Ana Gómez, que ya está inactiva
- **ENTONCES** se devuelve su ficha inactiva y la lista de sus turnos futuros, sin error

### Requirement: Reactivar

Reactivar SHALL marcar al paciente activo; desde ese momento MUST poder recibir turnos nuevos. Reactivar a quien ya está activo MUST NOT ser un error. Un paciente inexistente MUST rechazarse con `PATIENT_NOT_FOUND`.

#### Scenario: Reactivar y agendar (esperado)
- **DADO** Ana Gómez inactiva
- **CUANDO** la recepcionista la reactiva y le agenda un turno en una franja libre
- **ENTONCES** el turno se crea

#### Scenario: Ya activo (borde)
- **CUANDO** se reactiva a Juan Pérez, que ya está activo
- **ENTONCES** se devuelve su ficha activa, sin error

### Requirement: Borrado definitivo restringido (matriz RBAC, RN-PA-03, P-6 confirmada)

Solo el administrador SHALL poder borrar definitivamente a un paciente, y solo si no tiene ningún turno en ningún estado. Si tiene turnos MUST rechazarse con `PATIENT_HAS_APPOINTMENTS` sin borrar nada (el paciente se desactiva en su lugar). Un paciente inexistente MUST rechazarse con `PATIENT_NOT_FOUND`.

#### Scenario: Alta cargada por error (esperado)
- **DADO** Laura Ruiz recién dada de alta, sin turnos
- **CUANDO** el administrador la borra
- **ENTONCES** ya no existe y su documento queda libre para otra alta

#### Scenario: Paciente con un turno cancelado (error de negocio)
- **DADO** Juan Pérez con un único turno, `cancelled`
- **CUANDO** el administrador lo borra
- **ENTONCES** se rechaza con `PATIENT_HAS_APPOINTMENTS` y Juan y su turno siguen existiendo

#### Scenario: Inexistente (borde)
- **CUANDO** el administrador borra `no-existe`
- **ENTONCES** se rechaza con `PATIENT_NOT_FOUND`

### Requirement: La gestión de pacientes no altera la agenda (regla dura 6)

Ningún caso de uso de pacientes SHALL crear, cancelar, mover ni cambiar el estado de un turno. La no superposición de turnos de un profesional MUST seguir garantizada por la agenda (C-08) y por la base, sin cambios.

#### Scenario: Reactivar no habilita superponer (esperado)
- **DADO** Ana Gómez reactivada y la Dra. A con un turno `scheduled` de Juan Pérez a las 10:00
- **CUANDO** se agenda a Ana con la Dra. A a las 10:00
- **ENTONCES** se rechaza con `SLOT_TAKEN` y sigue habiendo un solo turno `scheduled` a esa hora
