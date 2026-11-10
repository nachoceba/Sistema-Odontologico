# Spec Delta: public-booking

## Purpose

Reglas y casos de uso de la reserva de turnos online por el propio paciente, sin cuenta: qué profesionales y franjas se ofrecen, cómo se identifica al paciente por DNI y nombre sin modificar fichas existentes, y cómo la reserva queda pendiente hasta que se confirma desde el email del dueño del DNI o vence sola.

## ADDED Requirements

### Requirement: Profesionales que se ofrecen online (P-4)

La reserva pública SHALL ofrecer solo los profesionales activos que tienen al menos un tramo de horario de atención cargado. De cada uno MUST exponer únicamente su identificador y su nombre visible (`display_name`), ordenados por nombre visible; nunca la matrícula, el usuario asociado ni su email.

#### Scenario: Profesional activo con horario (esperado)
- **WHEN** la Dra. A está activa y tiene horario de lunes a viernes
- **THEN** figura en la lista pública con su identificador y su nombre visible y sin ningún otro dato

#### Scenario: Profesional inactivo (error de negocio)
- **WHEN** el Dr. B tiene la ficha desactivada
- **THEN** no figura en la lista pública

#### Scenario: Profesional activo sin horario (borde)
- **WHEN** un profesional activo no tiene ningún tramo de horario
- **THEN** no figura en la lista pública

### Requirement: Franjas reservables de un día (RN-TU-02, RN-TU-03, RN-TU-12, RN-GL-01, P-4)

Las franjas reservables de un profesional en un día local SHALL salir del mismo cálculo de franjas que usa la recepción: la misma zona horaria de `clinic_settings`, la misma grilla, el horario, las licencias y los turnos `scheduled`, incluidos los pendientes de confirmación, que ocupan su franja. El cálculo MUST quedarse solo con las franjas libres cuyo inicio respeta la anticipación mínima `min_notice_hours` respecto del momento actual. Solo MUST ofrecer días locales entre hoy y hoy + 13 días; un día fuera de ese horizonte MUST devolver una lista vacía. Cada franja MUST exponer solo inicio y fin; nunca qué turno ocupa una franja ni de qué paciente es.

#### Scenario: Día con franjas libres (esperado)
- **WHEN** la Dra. A atiende de 09:00 a 12:00, tiene un turno a las 10:00, el slot es de 30 minutos y faltan más de 6 horas para las 09:00
- **THEN** las franjas reservables son 09:00, 09:30, 10:30, 11:00 y 11:30, en UTC, sin la de las 10:00

#### Scenario: Franja retenida por una reserva pendiente (borde)
- **WHEN** a las 11:00 hay un turno online pendiente de confirmación que no venció
- **THEN** la franja de las 11:00 no es reservable

#### Scenario: Franja liberada por cancelación o vencimiento (borde)
- **WHEN** el turno de las 10:00 fue cancelado (por la recepción o, desde C-16, por el vencimiento de la reserva)
- **THEN** la franja de las 10:00 vuelve a ser reservable (RN-TU-05)

#### Scenario: Anticipación mínima exacta (borde)
- **WHEN** faltan exactamente 6 horas para una franja libre y `min_notice_hours` es 6
- **THEN** esa franja es reservable; una que empieza un minuto antes no lo es

#### Scenario: Día de licencia (error de negocio)
- **WHEN** el día pedido está cubierto por una licencia del profesional
- **THEN** la lista de franjas reservables está vacía (RN-HO-03)

#### Scenario: Día fuera del horizonte (borde)
- **WHEN** se piden las franjas del día hoy + 14 o de un día pasado
- **THEN** la lista está vacía

#### Scenario: Día local distinto del día UTC (borde)
- **WHEN** el consultorio está en `America/Argentina/Buenos_Aires` y una franja empieza a las 21:30 locales
- **THEN** la franja pertenece al día local pedido aunque en UTC sea del día siguiente

### Requirement: Identificación por DNI y nombre (DD-129, RN-PA-01, RN-PA-05)

Toda reserva online SHALL traer documento, nombre, apellido y email válidos según `patient-data-rules`; el teléfono es opcional. El documento MUST normalizarse con la regla del alta de pacientes. Si el documento ya pertenece a un paciente, el nombre y el apellido escritos MUST coincidir con los de la ficha. Para comparar, se pasan a mayúsculas, se les quitan las tildes y se reducen los espacios. Si coinciden, el turno se vincula a esa ficha y la reserva MUST NOT modificar ningún dato de ella (nombre, email, teléfono, fecha de nacimiento ni estado): el email y el teléfono escritos se ignoran. Si no coinciden, la reserva MUST rechazarse con el rechazo genérico `BOOKING_NOT_POSSIBLE`, sin escribir nada y sin revelar ningún dato de la ficha. Si el documento no existe, se crea un paciente activo con los datos escritos. Nunca MUST existir dos pacientes con el mismo documento.

#### Scenario: DNI nuevo (esperado)
- **WHEN** alguien reserva con el documento `40999888`, que no existe, nombre Lucía, apellido Díaz y email `lucia@example.com`
- **THEN** se crea la paciente activa con esos datos y el turno pendiente queda vinculado a ella

#### Scenario: DNI existente con nombre coincidente (esperado)
- **WHEN** Juan Pérez (documento `30111222`, email `juan@example.com`) reserva escribiendo `juan  perez` y el email `otro@example.com`
- **THEN** el turno pendiente se vincula a su ficha, la ficha sigue con `juan@example.com` y no se crea ningún paciente

#### Scenario: DNI existente con nombre distinto (error de negocio)
- **WHEN** alguien reserva con el documento `30111222` y el nombre Pedro Gómez
- **THEN** se rechaza con `BOOKING_NOT_POSSIBLE`, no se crea turno ni paciente y la respuesta no contiene ningún dato de la ficha

#### Scenario: Tildes y mayúsculas no cuentan (borde)
- **WHEN** la ficha dice "María José Núñez" y se escribe "MARIA JOSE NUNEZ"
- **THEN** los nombres coinciden

#### Scenario: Paciente inactivo o con turno superpuesto (error de negocio, P-7 reemplazada)
- **WHEN** el documento con nombre coincidente es de un paciente inactivo, o el paciente ya tiene otro turno `scheduled` a esa hora con otro profesional
- **THEN** se rechaza con el mismo `BOOKING_NOT_POSSIBLE`, sin decir el motivo

### Requirement: Reserva pendiente de confirmación (DD-130, RN-TU-01 a RN-TU-04, RN-TU-12, RN-PA-04)

La reserva online SHALL crear un turno `scheduled` sin usuario creador y pendiente de confirmación, con vencimiento a los `ONLINE_BOOKING_HOLD_MINUTES` minutos de la reserva, o al inicio del turno si este es anterior. Valida las mismas reglas de agenda que el alta de la recepción: grilla, horario, licencias, anticipación mínima, profesional activo, paciente activo y paciente sin otro turno `scheduled` superpuesto. A eso suma el horizonte de 14 días. El turno pendiente MUST ocupar su franja frente a cualquier otro turno, por dominio y por el constraint `ex_appointments_no_overlap`. El alta del paciente nuevo y el turno pendiente MUST guardarse en una sola transacción: si el turno se rechaza, no queda ningún paciente nuevo. La reserva MUST NOT registrar todavía la confirmación de C-11. Después de guardar, MUST pedir el envío del email de verificación con un enlace de un solo uso al email de la ficha. La respuesta MUST ser idéntica para un DNI nuevo y para un DNI existente con nombre coincidente: solo inicio, fin, nombre visible del profesional y hasta cuándo se puede confirmar; nunca el email ni datos del paciente.

#### Scenario: Reserva queda pendiente (esperado)
- **WHEN** una paciente nueva reserva con la Dra. A a las 10:30 de mañana a las 12:00 de hoy, con `ONLINE_BOOKING_HOLD_MINUTES = 60`
- **THEN** se crea el turno `scheduled` pendiente que vence a las 13:00 de hoy, no se registra confirmación ni recordatorio, y se pide el email de verificación a `lucia@example.com`

#### Scenario: Respuesta indistinguible (borde)
- **WHEN** se compara la respuesta de una reserva con DNI nuevo y la de una con DNI existente y nombre coincidente
- **THEN** tienen el mismo estado HTTP, los mismos campos y el mismo texto

#### Scenario: Franja ocupada (error de negocio, regla dura 6)
- **WHEN** se reserva a las 10:00 con la Dra. A y ya hay un turno `scheduled` (confirmado o pendiente) de 10:00 a 10:30
- **THEN** se rechaza con `SLOT_TAKEN` y no se crea el paciente nuevo ni el turno

#### Scenario: Dos reservas simultáneas de la misma franja (borde, regla dura 6)
- **WHEN** dos personas con documentos distintos reservan al mismo tiempo la franja de las 11:00 de la Dra. A y ambas pasan la validación del dominio
- **THEN** el constraint `ex_appointments_no_overlap` deja un solo turno; la otra reserva recibe `SLOT_TAKEN` y su paciente nuevo no queda guardado

#### Scenario: Reserva online contra la recepción (borde, regla dura 6)
- **WHEN** la recepción agenda a las 11:30 con la Dra. A al mismo tiempo que una reserva online para esa franja
- **THEN** queda un solo turno y el otro pedido recibe `SLOT_TAKEN`

#### Scenario: Dos reservas simultáneas con el mismo DNI nuevo (borde)
- **WHEN** dos reservas con el mismo documento inexistente llegan al mismo tiempo para franjas distintas
- **THEN** queda un solo paciente con ese documento y la reserva que pierde la carrera se rechaza con `BOOKING_NOT_POSSIBLE` sin crear un segundo perfil

#### Scenario: Inicio no reservable (error de negocio)
- **WHEN** se reserva a las 10:15 con slot de 30 minutos, o fuera del horario, o en un día de licencia, o a 3 horas de ahora, o dentro de 20 días
- **THEN** se rechaza con `SLOT_UNAVAILABLE` y no se escribe nada

#### Scenario: Profesional no ofrecido (error)
- **WHEN** se reserva con un profesional inexistente, inactivo o sin horario
- **THEN** se rechaza con `PROFESSIONAL_NOT_FOUND`

#### Scenario: Falla el aviso de verificación (borde, RN-NO-04)
- **WHEN** Redis no responde al pedir el email de verificación
- **THEN** el turno pendiente queda guardado y nadie puede confirmarlo después de su vencimiento

### Requirement: Confirmar la reserva con el enlace (DD-131)

Cada reserva pendiente SHALL tener un token aleatorio de al menos 32 bytes, generado con un generador criptográfico; la base guarda solo su hash SHA-256, nunca el token. Confirmar con un token válido de una reserva pendiente que no venció y cuyo inicio no llegó MUST dejar el turno confirmado (sin vencimiento ni token), registrar la confirmación `pending` de C-11 en la misma transacción y despacharla después del commit. Desde ese momento el turno recibe recordatorio como cualquier otro (C-12). El token MUST servir una sola vez. Un token desconocido, ya usado, de una reserva vencida, cancelada o con el turno ya empezado MUST dar el mismo rechazo `CONFIRMATION_LINK_INVALID`, sin decir cuál de esos casos fue. La confirmación MUST tomar la fila con bloqueo (`FOR UPDATE`), para que una cancelación simultánea deje un solo resultado. Hasta C-16 (`online-booking-expiry`), un pendiente vencido no se cancela solo: ya no se puede confirmar, sigue ocupando la franja hasta que la recepción lo cancela, y no se envía ningún email de cancelación.

#### Scenario: Confirmación a tiempo (esperado)
- **WHEN** la paciente abre el enlace 20 minutos después de reservar y la página lo envía
- **THEN** el turno queda confirmado, se registra la confirmación de C-11 y se envía el email de confirmación normal

#### Scenario: Enlace usado dos veces (error)
- **WHEN** se envía de nuevo un token ya confirmado
- **THEN** se rechaza con `CONFIRMATION_LINK_INVALID` y no se registra otra confirmación

#### Scenario: Enlace vencido (error de negocio)
- **WHEN** se envía el token 61 minutos después de la reserva con `ONLINE_BOOKING_HOLD_MINUTES = 60`
- **THEN** se rechaza con `CONFIRMATION_LINK_INVALID` y el turno no queda confirmado

#### Scenario: Reserva cancelada por la recepción (borde)
- **WHEN** la recepción canceló el turno pendiente y después se envía su token
- **THEN** se rechaza con `CONFIRMATION_LINK_INVALID`

#### Scenario: El hash no permite confirmar (borde)
- **WHEN** se envía como token el valor guardado en la base
- **THEN** se rechaza con `CONFIRMATION_LINK_INVALID`

#### Scenario: Pendiente vencido antes de C-16 (borde)
- **WHEN** una reserva venció sin confirmarse y C-16 todavía no está implementado
- **THEN** su enlace da `CONFIRMATION_LINK_INVALID`, la franja sigue ocupada hasta que la recepción cancela el turno y no sale ningún email de cancelación
