# notification-tasks Specification

## Purpose
Definir las tareas asincrónicas de notificaciones (envío de un email y reencolado de pendientes), su programación periódica y cómo se publican, de modo que los emails salgan fuera del pedido HTTP y que un Redis o un worker caído nunca afecten las operaciones de turno (DD-10, RN-NO-04).

## Requirements

### Requirement: Tareas de notificaciones registradas (DD-10, `11_recordatorios_email.md` §Tareas)

La aplicación de tareas SHALL registrar exactamente tres tareas propias: `enviar_email`, que recibe solo el id de una notificación y la procesa (spec `notification-sending`); `reencolar_pendientes`, que hace una pasada de reencolado; y `enviar_recordatorios` (C-12), que hace una pasada de recordatorios (spec `reminder-scheduling`) y no recibe argumentos salvo la opción de forzar la pasada. Los argumentos de las tareas MUST NOT llevar datos del paciente (ni email ni nombre).

#### Scenario: Tareas propias (esperado)
- **WHEN** se listan las tareas registradas en la aplicación de tareas
- **THEN** las únicas propias del sistema son `enviar_email`, `reencolar_pendientes` y `enviar_recordatorios`

#### Scenario: El mensaje en la cola no tiene datos personales (borde)
- **WHEN** se publica `enviar_email` para la confirmación de Juan Perez
- **THEN** el mensaje publicado contiene el id de la notificación y no contiene `juan.perez@example.com` ni `Perez`

#### Scenario: Id inexistente o mal formado (error)
- **WHEN** el worker recibe `enviar_email` con un id que no corresponde a ninguna notificación o que no es un id válido
- **THEN** la tarea termina sin enviar nada, sin reintentar y sin error que tumbe al worker

#### Scenario: Recordatorios en modo inmediato (esperado)
- **WHEN** con la aplicación de tareas en modo inmediato, el remitente falso y un reloj a las 09:00 hora local con `reminder_send_hour = 9` se ejecuta `enviar_recordatorios` con un turno `scheduled` para mañana
- **THEN** el remitente falso recibe un email de recordatorio y la notificación queda `sent`

#### Scenario: Error de base en la pasada (borde)
- **WHEN** la base no responde al empezar `enviar_recordatorios`
- **THEN** la tarea termina con el error registrado, sin datos del paciente, sin reintentar y sin tumbar al worker

### Requirement: Reencolado cada 10 minutos (`11_recordatorios_email.md` §Envío asincrónico)

El programador periódico SHALL disparar `reencolar_pendientes` cada 10 minutos. Además de esa entrada y de la de recordatorios (requirement "Recordatorios cada hora"), MUST NOT programar ninguna otra tarea propia.

#### Scenario: Programación (esperado)
- **WHEN** se inspecciona la programación periódica de la aplicación de tareas
- **THEN** tiene exactamente dos entradas propias: `reencolar_pendientes` cada 10 minutos y `enviar_recordatorios` cada hora

#### Scenario: Beat no envía emails (borde)
- **WHEN** corre `reencolar_pendientes`
- **THEN** la tarea solo publica `enviar_email` para las pendientes antiguas; los envíos los hace el worker

### Requirement: Encolar después del commit sin depender de Redis (RN-NO-04, `11_recordatorios_email.md` §Envío asincrónico)

Después de que la transacción de agendar o reprogramar se confirma, el sistema SHALL publicar una tarea `enviar_email` por cada notificación registrada, sin reintentar la publicación si falla y con un timeout de conexión con Redis de a lo sumo 2 segundos. Si la publicación falla (Redis caído o lento), la operación de turno MUST responder igual como exitosa, la notificación MUST quedar `pending` para que la tome `reencolar_pendientes`, y el fallo MUST registrarse en el log solo con el id del turno y el tipo de error. MUST NOT publicarse nada si la transacción se revirtió.

#### Scenario: Agendar con Redis disponible (esperado)
- **WHEN** se agenda un turno válido con Redis disponible
- **THEN** la API responde 201 y en la cola hay una tarea `enviar_email` con el id de la confirmación recién registrada

#### Scenario: Agendar con Redis caído (borde)
- **WHEN** Redis no está disponible y se agenda un turno válido
- **THEN** la API responde 201 con el turno en menos de 5 segundos, el turno y su confirmación `pending` quedan guardados y el log registra el fallo de publicación con el id del turno y sin datos del paciente

#### Scenario: Reprogramar con Redis caído (borde)
- **WHEN** Redis no está disponible y se reprograma un turno
- **THEN** la API responde 200, el turno queda en el nuevo horario y la confirmación del nuevo horario queda `pending`

#### Scenario: Agendar rechazado no publica (error de negocio)
- **WHEN** agendar se rechaza con `SLOT_TAKEN`
- **THEN** no se publica ninguna tarea

#### Scenario: Cancelar no publica (borde)
- **WHEN** se cancela un turno
- **THEN** no se publica ninguna tarea ni se envía ningún email (RN-NO-05)

### Requirement: Sin endpoints nuevos (regla dura 4)

C-11 y C-12 SHALL NOT agregar ni cambiar endpoints HTTP: el envío, el reencolado y los recordatorios solo se disparan desde la agenda, desde el programador periódico o desde la consola del contenedor. Como no hay rutas nuevas, no hay chequeo de rol nuevo: el inventario de rutas y la matriz de permisos por rol MUST quedar iguales.

#### Scenario: Inventario de rutas sin cambios (esperado)
- **WHEN** se compara el inventario de rutas de la API con el de C-10
- **THEN** es el mismo y cada endpoint mantiene su test de permisos por rol

#### Scenario: No hay forma HTTP de disparar envíos (borde)
- **WHEN** se busca en la documentación OpenAPI una ruta de notificaciones, emails, recordatorios o tareas
- **THEN** no existe ninguna

### Requirement: Recordatorios cada hora (`11_recordatorios_email.md` §Programación del recordatorio)

El programador periódico SHALL disparar `enviar_recordatorios` una vez por hora, al comienzo de cada hora en la zona de la programación, sin forzar la pasada. La decisión de actuar o no la toma la propia pasada con la hora local del consultorio (spec `reminder-scheduling`), de modo que la hora configurada se respeta sin reiniciar el programador. La aplicación de tareas MUST seguir con la zona horaria del consultorio y los instantes internos en UTC.

#### Scenario: Entrada horaria (esperado)
- **WHEN** se inspecciona la entrada de `enviar_recordatorios` en la programación periódica
- **THEN** se dispara en el minuto 0 de cada hora y sin argumentos

#### Scenario: Pasada fuera de hora disparada por el programador (borde)
- **WHEN** el programador dispara `enviar_recordatorios` a las 14:00 hora local con `reminder_send_hour = 9`
- **THEN** la tarea termina sin enviar ningún email

### Requirement: Email de verificación de una reserva online (DD-130, DD-131)

Después de guardar una reserva pendiente, el caso de uso SHALL encolar una tarea de envío del email de verificación con el identificador del turno y el token en claro. El token viaja solo en el mensaje de la cola; nunca se guarda en la base ni en el log. La tarea MUST enviar el email solo si el turno sigue pendiente, no venció y el hash del token coincide con el guardado. En cualquier otro caso termina sin enviar. Reintenta los fallos temporales del servidor SMTP como la confirmación (DD-89). No crea filas en `email_notifications` y `reencolar_pendientes` MUST NOT tomarla. Un fallo al encolar MUST NOT deshacer la reserva: el turno queda pendiente hasta su vencimiento. El log de la tarea lleva solo el identificador del turno y el resultado.

#### Scenario: Envío de la verificación (esperado)
- **WHEN** se guarda una reserva pendiente y el worker procesa la tarea
- **THEN** sale un email al email de la ficha con el enlace de confirmación

#### Scenario: Turno ya cancelado o vencido (borde)
- **WHEN** el worker procesa la tarea de un turno que la recepción ya canceló
- **THEN** no sale ningún email

#### Scenario: Token en el log (borde)
- **WHEN** la tarea registra su resultado
- **THEN** el log no contiene el token ni el email
