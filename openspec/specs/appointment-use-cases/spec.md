# appointment-use-cases Specification

## Purpose
Definir qué hacen los casos de uso de la agenda (agendar, cancelar, reprogramar, marcar atención y consultar turnos y franjas) uniendo las reglas puras del dominio con los datos reales del consultorio, con un único motivo de rechazo por pedido y sin escribir nada cuando se rechaza.

## Requirements

### Requirement: Agendar un turno (US-007, RN-TU-01 a RN-TU-04, RN-TU-12, RN-PA-04)

Agendar SHALL recibir paciente, profesional, inicio pedido y la cuenta que agenda, y MUST guardar un turno `scheduled` de exactamente `slot_minutes` minutos (leídos de la configuración del consultorio, no un valor fijo) cuyo creador es esa cuenta. Las reglas de grilla, horario, licencia, anticipación mínima y superposición MUST evaluarse con los tramos, licencias, turnos y configuración reales del profesional (zona horaria, `slot_minutes`, `min_notice_hours`) y con el instante actual del reloj del sistema. El pedido MUST rechazarse con un único motivo, el del primer control incumplido en este orden: paciente inexistente (`PATIENT_NOT_FOUND`), profesional inexistente (`PROFESSIONAL_NOT_FOUND`), paciente inactivo (`PATIENT_INACTIVE`), profesional inactivo (`PROFESSIONAL_INACTIVE`, P-5), inicio con segundos o fracciones de segundo (`OFF_GRID`), los motivos de `validate_appointment` en su orden propio (`INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF`; la superposición se informa como `SLOT_TAKEN`) y paciente con otro turno superpuesto (`PATIENT_DOUBLE_BOOKED`, P-3). Un pedido rechazado MUST NOT escribir nada (ni turno ni notificación). Si la base rechaza la escritura por superposición (otro pedido ganó la carrera), el resultado MUST ser `SLOT_TAKEN`, igual que la superposición detectada por el dominio.

#### Scenario: Agendar en un slot libre (esperado)
- **WHEN** recepción agenda a Juan Pérez con la Dra. A el próximo lunes a las 10:00 (hora del consultorio), dentro de su horario de 09:00 a 13:00, sin licencias ni turnos, con `slot_minutes = 30`
- **THEN** se guarda un turno `scheduled` de 10:00 a 10:30 (guardado en UTC) con recepción como creadora
- **AND** el resultado incluye el identificador del turno

#### Scenario: Slot ya ocupado (error de negocio)
- **WHEN** la Dra. A ya tiene un turno `scheduled` de 10:00 a 10:30 y recepción intenta agendar a Ana Gómez a las 10:00
- **THEN** se rechaza con `SLOT_TAKEN` y no se escribe ningún turno ni notificación

#### Scenario: Fuera del horario de trabajo (error de negocio)
- **WHEN** la Dra. A atiende de 09:00 a 13:00, el consultorio tiene `slot_minutes = 45` y se pide un turno a las 12:45 (en la grilla, pero terminaría 13:30)
- **THEN** se rechaza con `OUTSIDE_WORKING_HOURS`

#### Scenario: Inicio en el pasado o sin anticipación suficiente (error de negocio)
- **WHEN** son las 08:00 y se pide un turno para hoy a las 10:00 con `min_notice_hours = 6`
- **THEN** se rechaza con `INSUFFICIENT_NOTICE` (cubre también un inicio en el pasado, RN-TU-04)

#### Scenario: Inicio exactamente en el límite de anticipación (borde)
- **WHEN** son las 04:00 y se pide un turno para hoy a las 10:00 con `min_notice_hours = 6`, dentro del horario y libre
- **THEN** se acepta (RN-TU-12: el límite exacto se acepta)

#### Scenario: Día de licencia (error de negocio)
- **WHEN** la Dra. A tiene licencia el próximo lunes y se pide un turno ese día a las 10:00
- **THEN** se rechaza con `PROFESSIONAL_TIME_OFF`

#### Scenario: Inicio fuera de la grilla (error de negocio)
- **WHEN** el tramo empieza a las 09:00 con `slot_minutes = 30` y se pide un turno a las 10:10
- **THEN** se rechaza con `OFF_GRID`

#### Scenario: Inicio con segundos (borde)
- **WHEN** se pide un turno a las 10:00:30, que por minutos caería en la grilla
- **THEN** se rechaza con `OFF_GRID` y no se guarda un turno de 10:00:30 a 10:30:30

#### Scenario: Paciente inactivo (error de negocio)
- **WHEN** se intenta agendar a una paciente desactivada en un slot libre
- **THEN** se rechaza con `PATIENT_INACTIVE` (RN-PA-04)

#### Scenario: Profesional con ficha inactiva (error de negocio)
- **WHEN** se intenta agendar con un profesional cuya ficha está desactivada (DD-59), en un horario que antes era válido
- **THEN** se rechaza con `PROFESSIONAL_INACTIVE`

#### Scenario: Paciente o profesional inexistente (error de negocio)
- **WHEN** se intenta agendar con un identificador de paciente que no existe, o con uno bien formado de profesional que no existe
- **THEN** se rechaza con `PATIENT_NOT_FOUND` o `PROFESSIONAL_NOT_FOUND` respectivamente

#### Scenario: Paciente inexistente e inicio inválido a la vez (borde)
- **WHEN** se pide un turno con un paciente inexistente y un inicio fuera de la grilla
- **THEN** el único motivo informado es `PATIENT_NOT_FOUND` (orden fijo)

#### Scenario: Turnos pegados (borde)
- **WHEN** la Dra. A tiene un turno de 10:00 a 10:30 y se pide otro a las 10:30
- **THEN** se acepta (rango semiabierto, RN-TU-01)

#### Scenario: Slot liberado por una cancelación (borde)
- **WHEN** la Dra. A tuvo un turno de 10:00 a 10:30 que fue cancelado y se pide otro a las 10:00
- **THEN** se acepta (RN-TU-05)

#### Scenario: La duración sale de la configuración (borde)
- **WHEN** el consultorio tiene `slot_minutes = 20`, el tramo es de 09:00 a 13:00 y se pide un turno a las 09:40
- **THEN** se guarda de 09:40 a 10:00

### Requirement: Un paciente no tiene dos turnos superpuestos (P-3, SU-05)

Un paciente MUST NOT quedar con dos turnos `scheduled` cuyos horarios se superponen, aunque sean con profesionales distintos: agendar o reprogramar en esa situación MUST rechazarse con `PATIENT_DOUBLE_BOOKED`. Varios turnos del mismo paciente el mismo día en horarios distintos MUST seguir permitiéndose (RN-TU-08). Esta regla la garantiza la aplicación, no la base de datos (ver design, riesgos).

#### Scenario: Mismo horario con otro profesional (error de negocio)
- **WHEN** Juan Pérez tiene un turno `scheduled` con la Dra. A de 10:00 a 10:30 y se le pide otro con el Dr. B a las 10:00
- **THEN** se rechaza con `PATIENT_DOUBLE_BOOKED`

#### Scenario: Mismo día en otro horario (esperado)
- **WHEN** Juan Pérez tiene un turno con la Dra. A de 10:00 a 10:30 y se le pide otro con el Dr. B a las 11:00
- **THEN** se acepta (RN-TU-08)

#### Scenario: Turno anterior cancelado o pegado (borde)
- **WHEN** Juan Pérez tiene un turno cancelado de 10:00 a 10:30 con la Dra. A y otro `scheduled` de 09:30 a 10:00 con el Dr. B, y se le pide uno con el Dr. B a las 10:00
- **THEN** se acepta (solo cuentan los `scheduled` que se superponen)

### Requirement: Cancelar un turno (US-008, RN-TU-05, DD-21)

Cancelar SHALL recibir el turno y un motivo obligatorio (P-7): sin espacios al principio y al final, entre 1 y 500 caracteres. MUST pasar el turno a `cancelled` guardando el motivo, sin borrarlo, y el horario MUST quedar libre para otro turno. Las reglas de transición son las de `appointment-status-transitions`: un turno ya iniciado se rechaza con `ALREADY_STARTED`, uno cancelado con `CANCELLED_IS_FINAL`, uno con asistencia registrada con `ATTENDANCE_ALREADY_RECORDED`. Un turno inexistente se rechaza con `APPOINTMENT_NOT_FOUND`. Un rechazo MUST NOT cambiar nada. Cancelar es posible aunque el paciente o la ficha del profesional estén inactivos.

#### Scenario: Cancelar con motivo (esperado)
- **WHEN** recepción cancela un turno `scheduled` de mañana a las 10:00 con el motivo "El paciente avisó por teléfono"
- **THEN** el turno queda `cancelled` con ese motivo
- **AND** agendar otro turno de ese profesional a las 10:00 se acepta

#### Scenario: Turno ya iniciado (error de negocio)
- **WHEN** son las 10:05 y se intenta cancelar el turno de hoy de 10:00 a 10:30
- **THEN** se rechaza con `ALREADY_STARTED` y el turno sigue `scheduled`

#### Scenario: Turno ya cancelado (error de negocio)
- **WHEN** se intenta cancelar un turno que ya está `cancelled`
- **THEN** se rechaza con `CANCELLED_IS_FINAL` y el motivo original no cambia

#### Scenario: Turno de un profesional desactivado (borde)
- **WHEN** se cancela un turno futuro de un profesional cuya ficha fue desactivada
- **THEN** se acepta (DD-59: recepción debe poder resolverlos)

#### Scenario: Turno inexistente (error de negocio)
- **WHEN** se intenta cancelar un identificador que no existe
- **THEN** se rechaza con `APPOINTMENT_NOT_FOUND`

### Requirement: Reprogramar un turno (US-009, RN-TU-06, DD-24, DD-25)

Reprogramar SHALL recibir el turno y un nuevo inicio, y MUST mover el turno a ese inicio con la duración `slot_minutes` vigente, conservando identificador, paciente, profesional y creador (no cambia de profesional, P-6). El orden de rechazo es: turno inexistente (`APPOINTMENT_NOT_FOUND`), elegibilidad del turno (`CANCELLED_IS_FINAL`, `ATTENDANCE_ALREADY_RECORDED`, `ALREADY_STARTED`), mismo inicio que el actual (`RESCHEDULE_SAME_TIME`, P-12), paciente inactivo (`PATIENT_INACTIVE`, DD-25), profesional inactivo (`PROFESSIONAL_INACTIVE`, P-5), y después las mismas reglas que agendar sobre el nuevo inicio, en el mismo orden. El propio turno MUST NOT contar como ocupación del nuevo horario (se puede mover solapando su horario anterior). Si cualquier control falla, el turno original MUST quedar exactamente igual (no se ejecuta parcialmente).

#### Scenario: Reprogramar a un slot libre (esperado)
- **WHEN** recepción mueve el turno de Juan Pérez de mañana 10:00 a mañana 11:00, libre y dentro del horario
- **THEN** el turno queda de 11:00 a 11:30 con el mismo identificador
- **AND** el horario de 10:00 queda libre

#### Scenario: Nuevo slot ocupado (error de negocio)
- **WHEN** se intenta mover el turno de Juan Pérez a las 11:00, donde la Dra. A ya tiene otro turno `scheduled`
- **THEN** se rechaza con `SLOT_TAKEN` y el turno de Juan Pérez sigue de 10:00 a 10:30

#### Scenario: Nuevo inicio sin anticipación suficiente (error de negocio)
- **WHEN** son las 08:00 y se intenta mover un turno de mañana a hoy a las 10:00 con `min_notice_hours = 6`
- **THEN** se rechaza con `INSUFFICIENT_NOTICE` y el turno no cambia

#### Scenario: Mover solapando su propio horario anterior (borde)
- **WHEN** el turno se agendó de 10:00 a 10:30 con `slot_minutes = 30`, después el consultorio pasó a `slot_minutes = 20` (tramo desde 09:00) y se lo mueve a las 10:20
- **THEN** se acepta como 10:20 a 10:40, aunque se superpone con su propio horario anterior

#### Scenario: Mismo horario que el actual (borde)
- **WHEN** se pide reprogramar un turno de 10:00 a las 10:00
- **THEN** se rechaza con `RESCHEDULE_SAME_TIME` y no se registra ninguna notificación nueva

#### Scenario: Turno ya iniciado o con asistencia (error de negocio)
- **WHEN** se intenta reprogramar un turno que ya empezó, o uno `completed`
- **THEN** se rechaza con `ALREADY_STARTED` o `ATTENDANCE_ALREADY_RECORDED` respectivamente

#### Scenario: Paciente desactivado después de agendar (error de negocio)
- **WHEN** Ana Gómez tiene un turno futuro, fue desactivada y se intenta reprogramarlo
- **THEN** se rechaza con `PATIENT_INACTIVE` (DD-25) y el turno no cambia

### Requirement: Marcar atención (US-010, RN-TU-07, DD-22, DD-23)

Marcar atención SHALL recibir el turno y el estado `completed` o `no_show`, y MUST guardar ese estado solo si el turno está `scheduled` y ya inició (`now >= starts_at`). Antes del inicio se rechaza con `NOT_STARTED_YET`; un turno cancelado con `CANCELLED_IS_FINAL`; uno con asistencia ya registrada con `ATTENDANCE_ALREADY_RECORDED`. Un odontólogo solo puede marcar turnos de su propio profesional (RN-AU-04); un turno ajeno se rechaza con `FORBIDDEN` sin cambiar nada. Quién más puede marcar lo define la matriz de `appointment-api` (P-4). Se puede marcar aunque la ficha del profesional esté inactiva.

#### Scenario: Odontóloga marca atendido su turno en curso (esperado)
- **WHEN** son las 10:10 y la Dra. A marca `completed` su turno de 10:00 a 10:30
- **THEN** el turno queda `completed`

#### Scenario: Turno que todavía no empezó (error de negocio)
- **WHEN** son las 09:59 y la Dra. A marca `no_show` su turno de las 10:00
- **THEN** se rechaza con `NOT_STARTED_YET`

#### Scenario: Inicio exacto (borde)
- **WHEN** son exactamente las 10:00 y la Dra. A marca `no_show` su turno de las 10:00
- **THEN** se acepta (DD-23)

#### Scenario: Turno de otro profesional (error de negocio)
- **WHEN** la Dra. A intenta marcar `completed` un turno iniciado del Dr. B
- **THEN** se rechaza con `FORBIDDEN` y el turno sigue `scheduled`

#### Scenario: Corregir una asistencia ya registrada (error de negocio)
- **WHEN** un turno `no_show` se intenta marcar `completed`
- **THEN** se rechaza con `ATTENDANCE_ALREADY_RECORDED` (DD-22)

### Requirement: Consultar turnos

El sistema SHALL permitir leer un turno por identificador y listar los turnos de un profesional en un rango `[desde, hasta)` de instantes, en cualquier estado y ordenados por inicio (DD-31, DD-35). Cada turno leído o listado MUST venir acompañado del nombre y el apellido de su paciente, tal como están guardados en ese momento, aunque el paciente esté inactivo (P-1 de C-09, CONFIRMADA (2026-11-04)); MUST NOT incluir otros datos del paciente (email, teléfono, documento ni fecha de nacimiento). Un odontólogo MUST NOT leer turnos de otro profesional ni listarlos: se rechaza con `FORBIDDEN` (DD-53), sin revelar datos del paciente. Un turno inexistente se informa como `APPOINTMENT_NOT_FOUND`. Un listado con `desde` no anterior a `hasta`, o con un rango de más de 31 días, se rechaza como pedido inválido. Consultar MUST NOT modificar ningún turno, notificación ni paciente.

#### Scenario: Recepción lista la semana de la Dra. A (esperado)
- **WHEN** recepción lista los turnos de la Dra. A del lunes 00:00 al lunes siguiente 00:00 (hora del consultorio)
- **THEN** recibe todos los turnos de esa semana, incluidos cancelados y atendidos, ordenados por inicio, cada uno con el nombre y el apellido de su paciente

#### Scenario: Odontóloga lee un turno ajeno (error de negocio)
- **WHEN** la Dra. A pide el detalle de un turno del Dr. B
- **THEN** se rechaza con `FORBIDDEN` y no recibe ningún dato del paciente

#### Scenario: Turno que cruza el límite del rango (borde)
- **WHEN** se listan los turnos de un día y un turno empieza 15 minutos antes del inicio del rango y termina dentro
- **THEN** el turno aparece en el listado

#### Scenario: Paciente inactivo sigue nombrado (borde)
- **WHEN** Juan Perez tiene un turno `scheduled` con la Dra. A, se lo desactiva y recepción lista ese día
- **THEN** el turno aparece con "Juan" y "Perez" y sigue `scheduled`

#### Scenario: El nombre es el vigente (borde)
- **WHEN** se corrige el apellido de un paciente después de agendarle un turno y se vuelve a listar
- **THEN** el turno aparece con el apellido corregido

#### Scenario: Solo nombre y apellido (esperado)
- **WHEN** la Dra. A lista sus turnos de un día
- **THEN** cada turno trae nombre y apellido del paciente y ningún email, teléfono, documento ni fecha de nacimiento

#### Scenario: Consultar no cambia nada (borde)
- **WHEN** recepción lista los turnos de una semana y lee el detalle de uno
- **THEN** ningún turno, notificación ni paciente cambió (regla dura 6)

### Requirement: Franjas de un día de un profesional (P-9, US-006, Flujo 2)

El sistema SHALL devolver las franjas de un día local de un profesional calculadas con `compute_slots` sobre sus tramos, licencias, turnos y la configuración real del consultorio, con inicio y fin en UTC y estado libre, ocupado o fuera de horario. Una franja libre MUST ser coherente con agendar: si su inicio cumple la anticipación mínima, agendar en ese inicio se acepta. Las franjas no aplican la anticipación mínima (DD-17). Un odontólogo solo puede pedir las de su profesional (`FORBIDDEN`). Un profesional inexistente se rechaza con `PROFESSIONAL_NOT_FOUND`; uno con ficha inactiva devuelve sus franjas igual (para ver turnos pendientes, DD-59).

#### Scenario: Día con un turno (esperado)
- **WHEN** la Dra. A atiende de 09:00 a 11:00 y tiene un turno de 10:00 a 10:30, y recepción pide las franjas de ese día
- **THEN** recibe 09:00, 09:30 y 10:30 libres, 10:00 ocupada, y el resto del día fuera de horario

#### Scenario: Profesional inexistente (error de negocio)
- **WHEN** se piden las franjas de un profesional que no existe
- **THEN** se rechaza con `PROFESSIONAL_NOT_FOUND`

#### Scenario: Franja libre y agendar coinciden (borde)
- **WHEN** una franja aparece libre y su inicio está a más de `min_notice_hours` del momento actual
- **THEN** agendar en ese inicio con ese profesional y un paciente activo sin otros turnos se acepta

### Requirement: Turnos pendientes de confirmación en la recepción (DD-130, DD-133, P-3 y P-6 nuevas)

Un turno pendiente de confirmación SHALL ocupar su franja para todos los casos de uso de agenda. Para la recepción y el administrador:

- **Agendar**: no pueden agendar otro turno en su franja (`SLOT_TAKEN`).
- **Cancelar**: lo pueden cancelar con motivo como cualquier otro turno. Al cancelar, el token se borra, así que el enlace deja de servir.
- **Reprogramar**: MUST NOT poder reprogramarlo; se rechaza con `PENDING_CONFIRMATION`.
- **Confirmar**: no hay confirmación manual; solo lo confirma el paciente desde el enlace.
- **Marcar atención**: MUST rechazarse con `PENDING_CONFIRMATION`, porque un pendiente vence o se confirma antes de empezar. Si su inicio llegó y sigue pendiente, la tarea de vencimiento lo cancela.

#### Scenario: Recepción cancela un pendiente (esperado)
- **WHEN** la recepción cancela con motivo un turno online pendiente
- **THEN** queda `cancelled`, el token deja de servir y la franja se libera

#### Scenario: Recepción intenta agendar sobre un pendiente (error de negocio, regla dura 6)
- **WHEN** la recepción agenda a las 11:00 con la Dra. A y hay un turno pendiente a esa hora
- **THEN** se rechaza con `SLOT_TAKEN`

#### Scenario: Reprogramar un pendiente (error de negocio)
- **WHEN** la recepción reprograma un turno pendiente
- **THEN** se rechaza con `PENDING_CONFIRMATION` y el turno no cambia

#### Scenario: Turno online confirmado (borde)
- **WHEN** la recepción cancela o reprograma un turno online ya confirmado
- **THEN** se aplica lo mismo que a un turno de recepción

### Requirement: Tratamiento al agendar y al reprogramar (DD-142, DD-144, DD-148)

Agendar un turno SHALL exigir un tratamiento válido según `treatment-management`. El chequeo del tratamiento MUST hacerse después de comprobar que el paciente y el profesional existen y están activos, y antes de las reglas de horario: un tratamiento inexistente responde `TREATMENT_NOT_FOUND` y uno inactivo o no ofrecido por el profesional responde `TREATMENT_NOT_AVAILABLE`, sin escribir nada. El turno se guarda con el tratamiento en la misma transacción que su confirmación por email. Las reglas de horario, de grilla, de anticipación y de superposición (del profesional y del paciente) MUST ser las mismas que antes, y un choque con otro turno MUST seguir respondiendo `SLOT_TAKEN` por el constraint de la base.

Reprogramar MUST conservar el tratamiento del turno sin volver a validarlo (aunque se haya desactivado o quitado al profesional) y MUST NOT permitir cambiarlo. Un turno sin tratamiento se reprograma igual que antes. Ningún caso de uso cambia el tratamiento de un turno existente. Cancelar y marcar atención no cambian.

#### Scenario: Agendar con tratamiento (esperado)
- **WHEN** la recepción agenda a Juan Perez con la Dra. A el lunes a las 10:00 con "Limpieza dental"
- **THEN** el turno queda `scheduled` con ese tratamiento y se registra su confirmación

#### Scenario: Tratamiento no ofrecido (error de negocio)
- **WHEN** la recepción agenda con el Dr. B el tratamiento "Blanqueamiento", que él no ofrece
- **THEN** se rechaza con `TREATMENT_NOT_AVAILABLE` y no se guarda nada

#### Scenario: Tratamiento inexistente (error)
- **WHEN** la recepción agenda con un tratamiento que no existe
- **THEN** se rechaza con `TREATMENT_NOT_FOUND`

#### Scenario: Orden de los rechazos (borde)
- **WHEN** la recepción agenda con un tratamiento inactivo en un horario fuera de la grilla
- **THEN** se rechaza con `TREATMENT_NOT_AVAILABLE`, porque el tratamiento se chequea antes que el horario

#### Scenario: Dos recepcionistas, mismo horario, distinto tratamiento (regla dura 6)
- **WHEN** dos recepcionistas agendan al mismo tiempo el mismo horario de la Dra. A con tratamientos distintos
- **THEN** uno queda guardado y el otro recibe `SLOT_TAKEN`

#### Scenario: Reprogramar conserva el tratamiento (esperado)
- **WHEN** la recepción reprograma un turno de "Extracción" al día siguiente
- **THEN** el turno movido sigue con "Extracción"

#### Scenario: Reprogramar con el tratamiento desactivado (borde)
- **WHEN** se desactivó "Blanqueamiento" y la recepción reprograma un turno que lo tiene
- **THEN** se reprograma y conserva "Blanqueamiento"
