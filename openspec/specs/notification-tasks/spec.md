# notification-tasks Specification

## Purpose
Definir las tareas asincrónicas de notificaciones (envío de un email y reencolado de pendientes), su programación periódica y cómo se publican, de modo que los emails salgan fuera del pedido HTTP y que un Redis o un worker caído nunca afecten las operaciones de turno (DD-10, RN-NO-04).

## Requirements

### Requirement: Tareas de notificaciones registradas (DD-10, `11_recordatorios_email.md` §Tareas)

La aplicación de tareas SHALL registrar exactamente dos tareas propias en C-11: `enviar_email`, que recibe solo el id de una notificación y la procesa (spec `notification-sending`), y `reencolar_pendientes`, que hace una pasada de reencolado. Los argumentos de las tareas MUST NOT llevar datos del paciente (ni email ni nombre): solo el id. La tarea `enviar_recordatorios` MUST NOT existir todavía (es de C-12).

#### Scenario: Tareas propias (esperado)
- **WHEN** se listan las tareas registradas en la aplicación de tareas
- **THEN** las únicas propias del sistema son `enviar_email` y `reencolar_pendientes`

#### Scenario: El mensaje en la cola no tiene datos personales (borde)
- **WHEN** se publica `enviar_email` para la confirmación de Juan Perez
- **THEN** el mensaje publicado contiene el id de la notificación y no contiene `juan.perez@example.com` ni `Perez`

#### Scenario: Id inexistente o mal formado (error)
- **WHEN** el worker recibe `enviar_email` con un id que no corresponde a ninguna notificación o que no es un id válido
- **THEN** la tarea termina sin enviar nada, sin reintentar y sin error que tumbe al worker

### Requirement: Reencolado cada 10 minutos (`11_recordatorios_email.md` §Envío asincrónico)

El programador periódico SHALL disparar `reencolar_pendientes` cada 10 minutos. MUST NOT programar ninguna otra tarea propia en C-11.

#### Scenario: Programación (esperado)
- **WHEN** se inspecciona la programación periódica de la aplicación de tareas
- **THEN** tiene una sola entrada propia: `reencolar_pendientes` cada 10 minutos

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

C-11 SHALL NOT agregar ni cambiar endpoints HTTP: el envío y el reencolado solo se disparan desde la agenda y desde el programador periódico. El inventario de rutas y la matriz de permisos por rol MUST quedar iguales.

#### Scenario: Inventario de rutas sin cambios (esperado)
- **WHEN** se compara el inventario de rutas de la API con el de C-10
- **THEN** es el mismo y cada endpoint mantiene su test de permisos por rol

#### Scenario: No hay forma HTTP de disparar envíos (borde)
- **WHEN** se busca en la documentación OpenAPI una ruta de notificaciones, emails o tareas
- **THEN** no existe ninguna
