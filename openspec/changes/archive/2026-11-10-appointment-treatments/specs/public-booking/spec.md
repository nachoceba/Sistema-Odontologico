# Spec Delta: public-booking

## MODIFIED Requirements

### Requirement: Profesionales que se ofrecen online (P-4)

La reserva pública SHALL ofrecer solo los profesionales activos que tienen al menos un tramo de horario de atención cargado y al menos un tratamiento activo asignado (C-17). De cada uno MUST exponer únicamente su identificador y su nombre visible (`display_name`), ordenados por nombre visible; nunca la matrícula, el usuario asociado ni su email.

#### Scenario: Profesional activo con horario (esperado)
- **WHEN** la Dra. A está activa, tiene horario de lunes a viernes y ofrece "Limpieza dental"
- **THEN** figura en la lista pública con su identificador y su nombre visible y sin ningún otro dato

#### Scenario: Profesional inactivo (error de negocio)
- **WHEN** el Dr. B tiene la ficha desactivada
- **THEN** no figura en la lista pública

#### Scenario: Profesional activo sin horario (borde)
- **WHEN** un profesional activo no tiene ningún tramo de horario
- **THEN** no figura en la lista pública

#### Scenario: Profesional sin tratamientos activos (borde)
- **WHEN** un profesional activo con horario no tiene ningún tratamiento activo asignado
- **THEN** no figura en la lista pública y sus franjas y tratamientos públicos responden `PROFESSIONAL_NOT_FOUND`

## ADDED Requirements

### Requirement: Tratamiento en la reserva online (C-17, DD-142)

La reserva pública SHALL ofrecer, para un profesional ofrecido, solo sus tratamientos asignados y activos, con su identificador y su nombre, ordenados por nombre. Toda reserva online MUST llevar un tratamiento. Si el tratamiento no existe, está inactivo o el profesional no lo ofrece, la reserva MUST rechazarse con `TREATMENT_NOT_AVAILABLE` sin crear ni vincular ningún paciente y sin escribir ningún turno; el chequeo MUST hacerse después de comprobar que el profesional se ofrece y antes de las reglas de horario y de buscar el documento, igual que en la recepción. Confirmar una reserva pendiente MUST NOT volver a validar el tratamiento: si se desactivó o se le quitó al profesional después de reservar, la reserva se confirma igual. El turno pendiente se guarda con el tratamiento; la respuesta de la reserva y la de la confirmación MUST incluir el nombre del tratamiento, y la respuesta MUST seguir siendo la misma para un DNI nuevo y para uno existente. El tratamiento MUST NOT cambiar la duración del turno ni las franjas reservables.

#### Scenario: Tratamientos de un profesional (esperado)
- **WHEN** se piden los tratamientos públicos de la Dra. A, que ofrece "Consulta" y "Limpieza dental"
- **THEN** se devuelven esos dos, ordenados por nombre, solo con identificador y nombre

#### Scenario: Reserva con tratamiento (esperado)
- **WHEN** un paciente reserva con la Dra. A el tratamiento "Limpieza dental" en una franja libre
- **THEN** el turno queda pendiente con ese tratamiento y la respuesta trae "Limpieza dental"

#### Scenario: Tratamiento de otro profesional (error de negocio)
- **WHEN** un paciente reserva con el Dr. B el tratamiento "Blanqueamiento", que el Dr. B no ofrece
- **THEN** se rechaza con `TREATMENT_NOT_AVAILABLE` y no se crea ni el paciente ni el turno

#### Scenario: Tratamiento desactivado mientras el paciente elegía (borde)
- **WHEN** el administrador desactiva "Blanqueamiento" y después el paciente envía la reserva con ese tratamiento
- **THEN** se rechaza con `TREATMENT_NOT_AVAILABLE`

#### Scenario: Tratamiento inactivo no se ofrece (borde)
- **WHEN** la Dra. A tiene asignado "Blanqueamiento" pero está inactivo
- **THEN** no figura entre sus tratamientos públicos

#### Scenario: Misma respuesta para DNI nuevo y existente (borde)
- **WHEN** se reserva el mismo tratamiento con un DNI nuevo y con uno existente con nombre coincidente
- **THEN** las dos respuestas tienen la misma forma y el mismo nombre de tratamiento

#### Scenario: Tratamiento inactivo y franja no reservable (borde)
- **WHEN** un paciente reserva con un tratamiento inactivo en un horario sin anticipación suficiente
- **THEN** se rechaza con `TREATMENT_NOT_AVAILABLE`, porque el tratamiento se chequea antes que el horario

#### Scenario: Tratamiento desactivado antes de confirmar (borde)
- **WHEN** el paciente reservó "Blanqueamiento", el administrador lo desactiva y después el paciente confirma a tiempo
- **THEN** la reserva queda confirmada con "Blanqueamiento"

#### Scenario: Confirmación con tratamiento (esperado)
- **WHEN** el paciente confirma la reserva desde el enlace
- **THEN** la respuesta trae el nombre del tratamiento reservado
