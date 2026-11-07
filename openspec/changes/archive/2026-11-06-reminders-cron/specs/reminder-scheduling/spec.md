# Spec Delta

## Purpose

Definir la pasada periódica que crea y envía los recordatorios del día siguiente: cuándo actúa según la hora del consultorio, qué turnos reciben recordatorio, cómo evita reenvíos y cómo registra el resultado sin que un fallo corte el lote (RN-NO-02, RN-NO-03, RN-NO-04, US-011).

## ADDED Requirements

### Requirement: La pasada solo actúa a la hora configurada (`11_recordatorios_email.md` §Programación del recordatorio, SU-03)

Cada pasada SHALL calcular la hora local del consultorio a partir del instante actual y de la zona horaria vigente en la configuración del consultorio (`clinic_settings.timezone`, RN-GL-01) y MUST actuar solo si esa hora es igual a `reminder_send_hour` de la configuración vigente al momento de la pasada. En cualquier otra hora la pasada MUST terminar sin leer turnos, sin registrar notificaciones y sin enviar emails. Cambiar `reminder_send_hour` en la base MUST tener efecto en la pasada siguiente sin reiniciar ningún servicio. Una hora perdida (programador o worker caídos durante toda la hora configurada) MUST NOT recuperarse en otra hora del mismo día.

#### Scenario: Hora configurada (esperado)
- **WHEN** `reminder_send_hour` es 9, la zona es `America/Argentina/Buenos_Aires` y la pasada corre el domingo 08/11/2026 a las 09:00 hora local (12:00 UTC)
- **THEN** la pasada actúa y procesa los turnos del lunes 09/11/2026

#### Scenario: Cualquier minuto de la hora configurada (borde)
- **WHEN** `reminder_send_hour` es 9 y la pasada corre a las 09:59:59 hora local
- **THEN** la pasada actúa

#### Scenario: Fuera de la hora configurada (error de negocio)
- **WHEN** `reminder_send_hour` es 9 y la pasada corre a las 08:59:59 o a las 10:00:00 hora local
- **THEN** la pasada no lee turnos, no registra ninguna notificación y no envía ningún email

#### Scenario: La hora se mide en la zona del consultorio, no en UTC (borde)
- **WHEN** `reminder_send_hour` es 9 y la pasada corre a las 09:00 UTC (06:00 hora local)
- **THEN** la pasada no actúa

#### Scenario: Cambio de hora sin reiniciar (borde)
- **WHEN** se cambia `reminder_send_hour` de 9 a 10 en la configuración y la siguiente pasada corre a las 10:00 hora local
- **THEN** la pasada actúa, y la de las 09:00 del día siguiente no actúa

#### Scenario: Hora perdida (borde)
- **WHEN** `reminder_send_hour` es 9, ninguna pasada corrió entre las 09:00 y las 09:59 y la siguiente corre a las 10:00 hora local
- **THEN** esa pasada no actúa y ese día no se crean recordatorios; los turnos conservan su confirmación

### Requirement: Turnos que reciben recordatorio (RN-NO-02, Flujo 4, DD-76)

Cuando la pasada actúa SHALL tomar los turnos en estado `scheduled` cuyo inicio cae en el día local siguiente al de la pasada, en la zona del consultorio (desde las 00:00 incluidas hasta las 00:00 del día posterior excluidas), de todos los profesionales. MUST NOT tomar turnos `cancelled`, `completed` ni `no_show`, ni turnos que empiezan otro día aunque terminen o se superpongan con ese día. Los turnos de pacientes inactivos (DD-76) y los de profesionales inactivos o con turnos en conflicto por horario o licencia (RN-HO-04, DD-68) MUST recibir recordatorio igual mientras sigan `scheduled`.

#### Scenario: Turnos de mañana de todos los profesionales (esperado)
- **WHEN** la pasada actúa el domingo 08/11/2026 a las 09:00 y hay turnos `scheduled` el lunes 09/11 a las 10:00 con la Dra. A y a las 15:00 con el Dr. B
- **THEN** ambos turnos reciben recordatorio

#### Scenario: Turno cancelado excluido (error de negocio)
- **WHEN** la pasada actúa y un turno del lunes 09/11 a las 11:00 está `cancelled`
- **THEN** ese turno no recibe recordatorio y no se registra ninguna notificación para él

#### Scenario: Límites del día en la zona del consultorio (borde)
- **WHEN** la pasada actúa el domingo 08/11/2026 a las 09:00 hora local y hay turnos `scheduled` el lunes 09/11 a las 00:00 hora local (03:00 UTC del lunes), el domingo 08/11 a las 23:30 hora local (02:30 UTC del lunes) y el martes 10/11 a las 00:00 hora local
- **THEN** solo el del lunes 09/11 a las 00:00 recibe recordatorio

#### Scenario: Turno que cruza la medianoche (borde)
- **WHEN** la pasada actúa el domingo y hay un turno `scheduled` del domingo 23:45 al lunes 00:15 hora local
- **THEN** ese turno no recibe recordatorio (empieza el domingo)

#### Scenario: Paciente inactivo con turno vigente (borde)
- **WHEN** la pasada actúa y el paciente de un turno `scheduled` del lunes fue desactivado
- **THEN** ese turno recibe recordatorio (DD-76)

#### Scenario: Profesional inactivo o turno en conflicto (borde)
- **WHEN** la pasada actúa y un turno `scheduled` del lunes es de un profesional inactivo, o cae en un día de licencia cargada después de agendarlo
- **THEN** ese turno recibe recordatorio igual

#### Scenario: Sin turnos mañana (borde)
- **WHEN** la pasada actúa y no hay turnos `scheduled` el día siguiente
- **THEN** no se registra ninguna notificación y el registro de la pasada informa cero en todas las cantidades

### Requirement: Un solo recordatorio por turno y horario (RN-NO-03, US-011)

Para cada turno elegido la pasada SHALL registrar un `reminder` `pending` con el horario actual del turno y procesarlo, salvo que ya exista un `reminder` de ese turno con ese horario en cualquier estado (`pending`, `sent` o `failed`), en cuyo caso MUST NOT registrar otro ni enviar nada. El `reminder` MUST registrarse solo si, en ese momento, el turno sigue `scheduled` y con el mismo horario que se leyó; si cambió, MUST NOT registrarse. Dos pasadas simultáneas o sucesivas sobre el mismo día MUST producir a lo sumo un recordatorio por turno y horario.

#### Scenario: Doble ejecución no reenvía (esperado)
- **WHEN** la pasada actúa dos veces en la misma hora y la primera ya envió el recordatorio del turno del lunes 10:00
- **THEN** la segunda no registra ninguna notificación nueva ni envía ningún email

#### Scenario: Dos pasadas a la vez (borde)
- **WHEN** dos pasadas actúan al mismo tiempo sobre los mismos turnos
- **THEN** cada turno recibe exactamente un email de recordatorio

#### Scenario: Turno reprogramado después de su recordatorio (borde)
- **WHEN** el turno del lunes 10:00 recibió su recordatorio en la pasada del domingo a las 09:00 y el domingo a las 12:00 se reprograma al lunes 11:00
- **THEN** sale solo la confirmación del nuevo horario y ningún recordatorio para las 11:00 (`11_recordatorios_email.md` §Programación del recordatorio); el `reminder` `sent` de las 10:00 queda como historial

#### Scenario: Turno cancelado o reprogramado durante la pasada (borde)
- **WHEN** la pasada leyó el turno del lunes 10:00 y, antes de registrar su recordatorio, recepción lo cancela o lo mueve a las 11:00
- **THEN** no se registra un `reminder` para las 10:00 y no sale ningún email con ese horario

#### Scenario: Turno agendado antes de la pasada para mañana (borde)
- **WHEN** a las 08:00 del domingo se agenda un turno para el lunes 10:00 y la pasada actúa a las 09:00
- **THEN** el paciente recibe la confirmación y también el recordatorio (son tipos distintos, RN-NO-03)

#### Scenario: Turno agendado después de la pasada (borde)
- **WHEN** a las 11:00 del domingo se agenda un turno para el lunes
- **THEN** recibe solo la confirmación; ningún recordatorio sale ese día

### Requirement: Fallo parcial no corta el lote (RN-NO-04, US-011)

La pasada SHALL procesar cada recordatorio por separado: un fallo de envío (permanente o temporal), un turno sin datos de paciente o profesional, o un error inesperado al procesar un turno MUST registrarse y la pasada MUST seguir con el turno siguiente. Un fallo permanente deja la notificación `failed` con el error sin datos personales; un fallo temporal la deja `pending` para el reencolado. Ningún fallo MUST modificar el turno.

#### Scenario: Fallo parcial (esperado)
- **WHEN** la pasada actúa sobre tres turnos y el servidor rechaza con 550 el email del segundo
- **THEN** el primero y el tercero quedan `sent`, el segundo queda `failed` con `error = SMTP_PERMANENT 550` y los tres turnos siguen `scheduled`

#### Scenario: Fallo temporal en la pasada (borde)
- **WHEN** el servidor SMTP no responde al enviar el recordatorio de un turno
- **THEN** la notificación queda `pending` y la pasada sigue con los demás; el reencolado la vuelve a pedir pasados 5 minutos

#### Scenario: Error inesperado en un turno (borde)
- **WHEN** procesar el recordatorio de un turno lanza un error que no es de envío
- **THEN** la pasada registra solo el id del turno y la clase del error y sigue con el turno siguiente

### Requirement: Registro de la pasada sin datos personales (`11_recordatorios_email.md` §Tareas, DD-77)

Cuando la pasada actúa SHALL registrar en el log una sola línea de resumen con las cantidades `processed` (recordatorios registrados en esta pasada), `sent`, `failed` y `pending`, donde `processed = sent + failed + pending`. Cuando no actúa MUST registrar solo que no es la hora configurada. Ningún registro de la pasada MUST contener emails, nombres ni documentos de pacientes.

#### Scenario: Resumen de la pasada (esperado)
- **WHEN** la pasada registra cuatro recordatorios, envía tres y uno falla de forma permanente
- **THEN** el log contiene `processed=4`, `sent=3`, `failed=1` y `pending=0`

#### Scenario: Sin datos del paciente en el log (borde)
- **WHEN** la pasada envía el recordatorio de Juan Perez (`juan.perez@example.com`)
- **THEN** ninguna línea del log contiene `juan.perez@example.com` ni `Perez`

### Requirement: Disparo manual fuera de la hora

La pasada SHALL poder ejecutarse a pedido desde la consola del contenedor indicando que se fuerce, y en ese caso MUST actuar sin importar la hora local, con todas las demás reglas iguales (día siguiente, solo `scheduled`, un recordatorio por turno y horario). La programación periódica MUST NOT forzar nunca. No existe ninguna ruta HTTP para dispararla.

#### Scenario: Forzar para la demo (esperado)
- **WHEN** a las 15:00 hora local se ejecuta la pasada forzada con un turno `scheduled` para mañana
- **THEN** el recordatorio llega a Mailpit y la notificación queda `sent`

#### Scenario: Forzar dos veces (borde)
- **WHEN** se fuerza la pasada dos veces seguidas
- **THEN** la segunda no envía ningún email nuevo

#### Scenario: Sin forma HTTP de disparar (error de negocio)
- **WHEN** se busca en la documentación OpenAPI una ruta de recordatorios o de tareas
- **THEN** no existe ninguna
