# database-schema Specification

## Purpose
Definir el esquema de PostgreSQL del sistema (tablas, tipos, constraints e índices) y la migración que lo crea y lo revierte, de modo que la base de datos sea la segunda barrera de las reglas del dominio: en particular, que un profesional nunca tenga dos turnos `scheduled` superpuestos aunque la aplicación no lo valide (DD-02, DD-04, regla dura 3 y 6).

## Requirements

### Requirement: La migración crea y revierte el esquema completo

La migración inicial SHALL crear, sobre una base vacía, la extensión `btree_gist`, los tipos enumerados `user_role` (`admin`, `receptionist`, `dentist`), `appointment_status` (`scheduled`, `cancelled`, `completed`, `no_show`), `notification_kind` (`confirmation`, `reminder`) y `notification_status` (`pending`, `sent`, `failed`), y las tablas `users`, `professionals`, `working_hours`, `time_off`, `patients`, `appointments`, `email_notifications` y `clinic_settings` con las columnas, claves foráneas, CHECK, UNIQUE e índices de `04_modelo_de_datos.md`. Revertirla MUST dejar la base sin tablas ni tipos propios del sistema. La migración MUST poder aplicarse, revertirse y volver a aplicarse sin errores. El esquema que crea la migración MUST coincidir con el que describen los modelos de la aplicación.

#### Scenario: Aplicar la migración en una base limpia (esperado)
- **DADO** una base PostgreSQL vacía
- **CUANDO** se aplica la migración hasta la última versión
- **ENTONCES** existen las 8 tablas, los 4 tipos enumerados, la extensión `btree_gist` y el constraint de exclusión de `appointments`

#### Scenario: Revertir y volver a aplicar (borde)
- **DADO** una base con la migración aplicada y sin datos
- **CUANDO** se revierte la migración hasta el principio y después se vuelve a aplicar
- **ENTONCES** al revertir no queda ninguna tabla ni tipo enumerado del sistema, y al volver a aplicar el esquema queda igual que la primera vez

#### Scenario: Aplicar dos veces seguidas (borde)
- **DADO** una base con la migración ya aplicada
- **CUANDO** se pide aplicar la migración otra vez
- **ENTONCES** no cambia nada y no hay error

#### Scenario: Modelos y migración coinciden (esperado)
- **DADO** una base con la migración aplicada
- **CUANDO** se comparan las tablas, columnas, tipos y constraints de la base con los modelos de la aplicación
- **ENTONCES** no hay diferencias

### Requirement: La base rechaza dos turnos scheduled superpuestos del mismo profesional (RN-TU-01, DD-04)

La tabla de turnos SHALL rechazar cualquier inserción o actualización que deje dos turnos en estado `scheduled` del mismo profesional cuyos rangos semiabiertos `[inicio, fin)` se superpongan, aunque la escritura no pase por el dominio. Los turnos `cancelled`, `completed` y `no_show` MUST NOT bloquear. Turnos de profesionales distintos MUST NOT bloquearse entre sí. Tocarse en el borde (uno termina cuando empieza el otro) MUST NOT considerarse superposición. El rechazo MUST dejar la tabla como estaba.

#### Scenario: Superposición directa en la base (error de negocio)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se inserta directo en la base otro turno `scheduled` de la Dra. A de 10:15 a 10:45
- **ENTONCES** la base rechaza la inserción por el constraint de exclusión
- **Y** la Dra. A sigue teniendo un único turno

#### Scenario: Mismo horario exacto con otro paciente (error de negocio)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30 para Juan Pérez
- **CUANDO** se inserta directo en la base un turno `scheduled` de la Dra. A de 10:00 a 10:30 para Ana Gómez
- **ENTONCES** la base rechaza la inserción

#### Scenario: Turnos pegados (borde)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se inserta un turno `scheduled` de la Dra. A de 10:30 a 11:00 y otro de 09:30 a 10:00
- **ENTONCES** la base acepta los dos

#### Scenario: Un turno cancelado no bloquea (esperado)
- **DADO** un turno `cancelled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se inserta un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **ENTONCES** la base lo acepta

#### Scenario: Atendidos y ausentes no bloquean (borde)
- **DADO** un turno `completed` de la Dra. A de 10:00 a 10:30 y uno `no_show` de 11:00 a 11:30
- **CUANDO** se insertan turnos `scheduled` de la Dra. A en esos mismos horarios
- **ENTONCES** la base acepta los dos

#### Scenario: Profesionales distintos a la misma hora (esperado)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se inserta un turno `scheduled` del Dr. B de 10:00 a 10:30
- **ENTONCES** la base lo acepta

#### Scenario: Volver a agendar un turno cancelado cuyo horario ya se ocupó (error de negocio)
- **DADO** un turno `cancelled` de la Dra. A de 10:00 a 10:30 y otro `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se actualiza directo en la base el turno cancelado a `scheduled`
- **ENTONCES** la base rechaza la actualización y el turno sigue `cancelled`

#### Scenario: Mover un turno encima de otro (error de negocio)
- **DADO** dos turnos `scheduled` de la Dra. A, de 10:00 a 10:30 y de 11:00 a 11:30
- **CUANDO** se actualiza directo en la base el segundo para que vaya de 10:15 a 10:45
- **ENTONCES** la base rechaza la actualización y el segundo turno conserva su horario

#### Scenario: Turno que cruza la medianoche (borde)
- **DADO** un turno `scheduled` de la Dra. A del lunes 23:45 al martes 00:15
- **CUANDO** se inserta un turno `scheduled` de la Dra. A del martes 00:00 a 00:30
- **ENTONCES** la base lo rechaza (misma comparación de instantes que DD-19)

### Requirement: Integridad de los datos de un turno

La tabla de turnos SHALL guardar inicio y fin como instantes con zona horaria, MUST rechazar un inicio igual o posterior al fin, MUST asignar `scheduled` como estado por defecto y MUST rechazar un estado fuera de `scheduled`, `cancelled`, `completed` y `no_show`. Paciente y profesional MUST existir. El usuario creador es opcional (C-15): nulo significa que el turno se reservó online; si tiene valor, ese usuario MUST existir. Una migración nueva (`0003`) MUST volver opcional la columna sin tocar los turnos existentes, y su reversión MUST fallar sin cambiar nada si hay turnos sin usuario creador. Un instante escrito con otra zona horaria MUST leerse como el mismo instante.

#### Scenario: Inicio igual o posterior al fin (error de negocio)
- **CUANDO** se inserta directo en la base un turno de 10:30 a 10:30, o de 10:30 a 10:00
- **ENTONCES** la base rechaza la inserción por el CHECK de inicio anterior al fin

#### Scenario: El instante se conserva entre zonas (esperado)
- **CUANDO** se guarda un turno con inicio `2026-10-05T10:00-03:00`
- **ENTONCES** al leerlo, su inicio es el instante `2026-10-05T13:00Z`

#### Scenario: Estado por defecto (esperado)
- **CUANDO** se inserta un turno sin indicar el estado
- **ENTONCES** queda `scheduled`

#### Scenario: Estado inválido (error de negocio)
- **CUANDO** se inserta un turno con estado `pending`
- **ENTONCES** la base lo rechaza

#### Scenario: Paciente o profesional inexistente (error de negocio)
- **CUANDO** se inserta un turno con un paciente, un profesional o un usuario creador (no nulo) que no existen
- **ENTONCES** la base lo rechaza por clave foránea

#### Scenario: Turno online sin usuario creador (esperado)
- **CUANDO** se inserta un turno con usuario creador nulo
- **ENTONCES** la base lo acepta y el constraint de no superposición lo cubre igual que a los demás

#### Scenario: Revertir con turnos online guardados (borde)
- **CUANDO** se revierte la migración `0003` y hay turnos con usuario creador nulo
- **ENTONCES** la reversión falla y el esquema queda como estaba

### Requirement: Un email por tipo, turno y horario del turno (RN-NO-03)

La tabla de notificaciones SHALL rechazar una segunda notificación con el mismo turno, el mismo tipo (`confirmation` o `reminder`) y el mismo inicio del turno copiado. MUST aceptar otra notificación del mismo tipo si el inicio copiado es distinto (turno reprogramado). El estado por defecto MUST ser `pending`.

#### Scenario: Recordatorio duplicado (error de negocio)
- **DADO** una notificación `reminder` del turno T con inicio copiado 10:00
- **CUANDO** se inserta otra `reminder` del turno T con inicio copiado 10:00
- **ENTONCES** la base la rechaza

#### Scenario: Turno reprogramado recibe una notificación nueva (borde)
- **DADO** una notificación `confirmation` del turno T con inicio copiado 10:00
- **CUANDO** se inserta una `confirmation` del turno T con inicio copiado 11:00
- **ENTONCES** la base la acepta

#### Scenario: Tipos distintos del mismo turno (esperado)
- **DADO** una notificación `confirmation` del turno T con inicio copiado 10:00
- **CUANDO** se inserta una `reminder` del turno T con inicio copiado 10:00
- **ENTONCES** la base la acepta con estado `pending`

### Requirement: Horarios y licencias bien formados (RN-HO-01, RN-HO-02, DD-26, DD-29)

La tabla de tramos de horario SHALL guardar el día de la semana (0 = lunes a 6 = domingo) y las horas locales de inicio y fin, y MUST rechazar un día fuera de 0 a 6 y un inicio igual o posterior al fin. La base MUST rechazar horas con segundos. La no superposición entre tramos del mismo día NO la verifica la base: la valida el dominio antes de guardar (`schedule-validation`). La tabla de licencias MUST rechazar una licencia que termina antes de empezar y MUST aceptar una licencia de un solo día.

#### Scenario: Tramo válido (esperado)
- **CUANDO** se inserta un tramo de la Dra. A para el lunes (0) de 09:00 a 13:00
- **ENTONCES** la base lo acepta

#### Scenario: Tramo invertido o vacío (error de negocio)
- **CUANDO** se inserta un tramo de 13:00 a 09:00, o de 09:00 a 09:00
- **ENTONCES** la base lo rechaza

#### Scenario: Día de la semana fuera de rango (error de negocio)
- **CUANDO** se inserta un tramo con día 7 o día −1
- **ENTONCES** la base lo rechaza

#### Scenario: Último fin posible del día (borde)
- **CUANDO** se inserta un tramo de 18:00 a 23:59
- **ENTONCES** la base lo acepta (un tramo no cruza la medianoche, DD-26)

#### Scenario: Hora con segundos (borde)
- **CUANDO** se inserta un tramo de 09:00:30 a 13:00
- **ENTONCES** la base lo rechaza

#### Scenario: Licencia que termina antes de empezar (error de negocio)
- **CUANDO** se inserta una licencia del 10 al 9 de octubre
- **ENTONCES** la base la rechaza

#### Scenario: Licencia de un solo día (borde)
- **CUANDO** se inserta una licencia del 9 al 9 de octubre
- **ENTONCES** la base la acepta

### Requirement: Identidad única de pacientes, usuarios y profesionales (RN-PA-01, RN-PA-02, RN-AU-02)

La base SHALL rechazar dos pacientes con el mismo número de documento y un paciente sin email. MUST rechazar dos usuarios con el mismo email, sin distinguir mayúsculas de minúsculas, y un rol fuera de `admin`, `receptionist` y `dentist`. Un usuario MUST tener como máximo un profesional asociado. Pacientes, usuarios y profesionales MUST quedar activos por defecto.

#### Scenario: Documento repetido (error de negocio)
- **DADO** el paciente Juan Pérez con documento 30111222
- **CUANDO** se inserta otro paciente con documento 30111222
- **ENTONCES** la base lo rechaza

#### Scenario: Paciente sin email (error de negocio)
- **CUANDO** se inserta un paciente sin email
- **ENTONCES** la base lo rechaza

#### Scenario: Email de usuario repetido con otras mayúsculas (borde)
- **DADO** un usuario con email `recepcion@example.com`
- **CUANDO** se inserta otro usuario con email `Recepcion@Example.com`
- **ENTONCES** la base lo rechaza

#### Scenario: Rol inexistente (error de negocio)
- **CUANDO** se inserta un usuario con rol `patient`
- **ENTONCES** la base lo rechaza

#### Scenario: Dos profesionales para el mismo usuario (error de negocio)
- **DADO** la Dra. A asociada a su usuario
- **CUANDO** se inserta otro profesional asociado al mismo usuario
- **ENTONCES** la base lo rechaza

#### Scenario: Activo por defecto (esperado)
- **CUANDO** se inserta un paciente, un usuario o un profesional sin indicar si está activo
- **ENTONCES** queda activo

### Requirement: Lo que tiene historia no se borra (RN-PA-03, DD-05)

La base SHALL rechazar el borrado de un paciente, un profesional o un usuario que tenga turnos asociados (como paciente, profesional o creador); la baja se hace marcándolo inactivo. Borrar un turno con notificaciones MUST rechazarse. Ningún borrado MUST propagarse en cascada a los turnos.

#### Scenario: Borrar un paciente con turnos (error de negocio)
- **DADO** Juan Pérez con un turno `cancelled`
- **CUANDO** se intenta borrar a Juan Pérez directo en la base
- **ENTONCES** la base lo rechaza y el turno sigue existiendo

#### Scenario: Borrar un paciente sin turnos (borde)
- **DADO** un paciente cargado por error, sin turnos
- **CUANDO** se lo borra directo en la base
- **ENTONCES** la base lo permite

### Requirement: Una sola configuración del consultorio (RN-GL-01, DD-03, DD-14)

La tabla de configuración SHALL admitir como máximo una fila, con duración del slot por defecto 30 minutos, zona `America/Argentina/Buenos_Aires`, hora del recordatorio 9 y anticipación mínima 6 horas. MUST rechazar una duración de slot menor o igual a cero, una anticipación negativa y una hora del recordatorio fuera de 0 a 23.

#### Scenario: Valores por defecto (esperado)
- **CUANDO** se inserta la fila de configuración con solo nombre y dirección del consultorio
- **ENTONCES** queda con slot de 30 minutos, zona `America/Argentina/Buenos_Aires`, recordatorio a las 9 y anticipación de 6 horas

#### Scenario: Segunda fila de configuración (error de negocio)
- **DADO** la fila de configuración cargada
- **CUANDO** se inserta otra fila
- **ENTONCES** la base la rechaza

#### Scenario: Valores fuera de rango (borde)
- **CUANDO** se guarda un slot de 0 minutos, una anticipación de −1 horas o un recordatorio a las 24
- **ENTONCES** la base lo rechaza

### Requirement: Antigüedad de cada notificación (P-3)

Una migración posterior a la inicial SHALL agregar a `email_notifications` la columna `created_at` (`timestamptz`, NOT NULL, con el instante de la inserción como valor por defecto) y un índice que permita buscar las `pending` por antigüedad. Al aplicarla sobre una base con filas, las filas existentes MUST quedar con el instante de la migración. Revertirla MUST quitar la columna y el índice sin tocar las demás columnas ni filas. Aplicar, revertir y volver a aplicar MUST funcionar sin errores, y el esquema MUST seguir coincidiendo con los modelos de la aplicación.

#### Scenario: Aplicar sobre una base con notificaciones (esperado)
- **DADO** una base con la migración inicial y dos notificaciones `pending` registradas en C-08
- **CUANDO** se aplica la migración hasta la última versión
- **ENTONCES** las dos filas conservan todos sus datos y tienen `created_at` con el instante de la migración

#### Scenario: Valor por defecto al insertar (esperado)
- **DADO** la migración aplicada
- **CUANDO** se inserta una notificación sin indicar `created_at`
- **ENTONCES** queda con el instante de la inserción

#### Scenario: Revertir y volver a aplicar (borde)
- **DADO** la base con la última migración aplicada
- **CUANDO** se revierte un paso y se vuelve a aplicar
- **ENTONCES** al revertir `email_notifications` no tiene `created_at` y conserva sus filas, y al volver a aplicar el esquema queda igual que antes

#### Scenario: Modelos y migración coinciden (esperado)
- **DADO** una base con todas las migraciones aplicadas
- **CUANDO** se comparan las tablas, columnas, tipos, índices y constraints de la base con los modelos de la aplicación
- **ENTONCES** no hay diferencias

### Requirement: Datos de la reserva pendiente en el turno (DD-130, DD-131)

La migración `0003` SHALL agregar a `appointments` dos columnas opcionales: `pending_until` (instante con zona) y `confirmation_token_hash` (texto). Un turno está pendiente de confirmación cuando `pending_until` no es nulo. La base MUST garantizar:

- las dos columnas son nulas juntas o no nulas juntas;
- solo un turno sin usuario creador puede estar pendiente;
- un hash de token no se repite: índice único parcial sobre `confirmation_token_hash` cuando no es nulo;
- un índice parcial sobre `pending_until` cuando no es nulo, para la tarea de vencimiento.

El estado del turno pendiente es `scheduled`, así que el constraint `ex_appointments_no_overlap` lo cubre sin cambios. La migración MUST NOT modificar el tipo `appointment_status` ni el constraint de exclusión.

#### Scenario: Pendiente bien formado (esperado)
- **CUANDO** se inserta un turno sin usuario creador con `pending_until` y `confirmation_token_hash`
- **ENTONCES** la base lo acepta

#### Scenario: Pendiente con solo una de las columnas (error de negocio)
- **CUANDO** se inserta un turno con `pending_until` y sin `confirmation_token_hash`
- **ENTONCES** la base lo rechaza por CHECK

#### Scenario: Pendiente creado por la recepción (error de negocio)
- **CUANDO** se inserta un turno con usuario creador y `pending_until`
- **ENTONCES** la base lo rechaza por CHECK

#### Scenario: Pendiente contra confirmado superpuestos (borde, regla dura 6)
- **CUANDO** se inserta un turno pendiente que se superpone con un turno `scheduled` confirmado del mismo profesional
- **ENTONCES** la base lo rechaza por `ex_appointments_no_overlap`

#### Scenario: Hash repetido (borde)
- **CUANDO** dos turnos pendientes tienen el mismo `confirmation_token_hash`
- **ENTONCES** la base rechaza el segundo

### Requirement: Tipo de notificación del aviso de vencimiento (DD-140)

La migración `0004` SHALL agregar el valor `booking_expired` al tipo `notification_kind`, sin tocar las notificaciones existentes ni el `UNIQUE (appointment_id, kind, appointment_starts_at)`. Su reversión MUST fallar sin cambiar nada si hay notificaciones `booking_expired`; si no las hay, MUST volver el tipo a `confirmation` y `reminder`.

#### Scenario: Aviso de vencimiento guardado (esperado)
- **CUANDO** se inserta una notificación `booking_expired` `pending`
- **ENTONCES** la base la acepta

#### Scenario: Aviso duplicado (error de negocio)
- **CUANDO** se inserta un segundo `booking_expired` para el mismo turno e inicio
- **ENTONCES** la base lo rechaza por el `UNIQUE`

#### Scenario: Revertir con avisos guardados (borde)
- **CUANDO** se revierte la migración `0004` y hay notificaciones `booking_expired`
- **ENTONCES** la reversión falla y el esquema queda como estaba
