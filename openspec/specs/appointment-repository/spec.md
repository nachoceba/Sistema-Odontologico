# appointment-repository Specification

## Purpose
Definir el contrato para guardar, buscar, cambiar de estado, reprogramar y listar turnos sin depender de la base de datos, de modo que cualquier implementación (en memoria hoy, PostgreSQL después) garantice que un profesional nunca tenga dos turnos `scheduled` superpuestos.

## Requirements

### Requirement: Contrato único para todas las implementaciones

Toda implementación del repositorio de turnos SHALL cumplir los escenarios de esta spec. La batería de pruebas de contrato MUST poder ejecutarse sin cambios contra cada implementación (la de memoria en este change; la de PostgreSQL en C-02/C-08) y MUST partir de un repositorio vacío en cada escenario.

#### Scenario: La misma batería corre contra cada implementación (esperado)
- **DADO** la batería de contrato del repositorio de turnos y la lista de implementaciones registradas
- **CUANDO** se ejecuta la batería
- **ENTONCES** cada escenario corre una vez por implementación, con un repositorio vacío, y todos pasan

### Requirement: Guardar un turno nuevo

Guardar un turno nuevo SHALL recibir paciente, profesional, inicio y fin (instantes con zona horaria), y quién lo crea, y MUST devolver el turno guardado con un identificador nuevo y único y estado `scheduled`. El turno guardado MUST poder recuperarse por su identificador con los mismos datos. Inicio y fin se guardan como instantes: el mismo instante expresado en otra zona horaria MUST recuperarse igual. Un inicio o fin sin zona horaria, o un inicio que no es anterior al fin, MUST rechazarse como error de programación (`ValueError`), equivalente al `CHECK (starts_at < ends_at)` de la base.

#### Scenario: Guardar y recuperar un turno (esperado)
- **DADO** un repositorio vacío
- **CUANDO** recepción (`rec-1`) guarda un turno de Juan Pérez con la Dra. A de 10:00 a 10:30
- **ENTONCES** se devuelve un turno con identificador, estado `scheduled` y sin motivo de cancelación
- **Y** buscarlo por ese identificador devuelve los mismos paciente, profesional, inicio, fin y creador

#### Scenario: Dos turnos guardados reciben identificadores distintos (esperado)
- **DADO** un repositorio vacío
- **CUANDO** se guardan un turno de la Dra. A de 10:00 a 10:30 y otro de 10:30 a 11:00
- **ENTONCES** los dos identificadores son distintos

#### Scenario: Inicio sin zona horaria (borde)
- **DADO** un repositorio vacío
- **CUANDO** se intenta guardar un turno cuyo inicio no tiene zona horaria
- **ENTONCES** se lanza `ValueError` y el repositorio sigue vacío

#### Scenario: Inicio igual o posterior al fin (borde)
- **DADO** un repositorio vacío
- **CUANDO** se intenta guardar un turno de 10:30 a 10:30, o de 10:30 a 10:00
- **ENTONCES** se lanza `ValueError` y el repositorio sigue vacío

### Requirement: El repositorio nunca guarda dos turnos scheduled superpuestos del mismo profesional (RN-TU-01, regla dura 6)

Toda operación que deje un turno en estado `scheduled` (guardar, reprogramar, cambiar estado) SHALL rechazarse si su rango `[inicio, fin)` se superpone con el de otro turno `scheduled` del mismo profesional, igual que el constraint de exclusión `EXCLUDE ... WHERE (status = 'scheduled')` de `04_modelo_de_datos.md`. El rechazo MUST expresarse con el error de dominio de turno ocupado (`SLOT_TAKEN`), que indica profesional e inicio pedidos, y MUST dejar el repositorio exactamente como estaba. Los rangos son semiabiertos: tocarse en el borde no es superponerse. Los turnos `cancelled`, `completed` y `no_show` no bloquean. Turnos de profesionales distintos no se bloquean entre sí.

#### Scenario: Segundo turno superpuesto del mismo profesional (error de negocio)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se intenta guardar otro turno de la Dra. A de 10:15 a 10:45
- **ENTONCES** se rechaza con el error `SLOT_TAKEN` para la Dra. A a las 10:15
- **Y** el listado de la Dra. A sigue teniendo un único turno

#### Scenario: Mismo horario exacto (error de negocio)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30 para Juan Pérez
- **CUANDO** se intenta guardar un turno de la Dra. A de 10:00 a 10:30 para Ana Gómez
- **ENTONCES** se rechaza con el error `SLOT_TAKEN`

#### Scenario: Turno que contiene a otro (error de negocio)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se intenta guardar un turno de la Dra. A de 09:30 a 11:00
- **ENTONCES** se rechaza con el error `SLOT_TAKEN`

#### Scenario: Turnos pegados no se superponen (borde)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se guardan turnos de la Dra. A de 09:30 a 10:00 y de 10:30 a 11:00
- **ENTONCES** ambos se guardan

#### Scenario: Otro profesional en el mismo horario (esperado)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se guarda un turno del Dr. B de 10:00 a 10:30
- **ENTONCES** se guarda

#### Scenario: Mismo paciente con dos profesionales a la misma hora (borde)
- **DADO** un turno `scheduled` de Juan Pérez con la Dra. A de 10:00 a 10:30
- **CUANDO** se guarda un turno de Juan Pérez con el Dr. B de 10:00 a 10:30
- **ENTONCES** se guarda: el repositorio, como el constraint de la base, solo protege al profesional (si el paciente debe protegerse es una regla de C-08, ver `design.md` §Fuera de C-05d)

#### Scenario: Un turno cancelado no bloquea (esperado)
- **DADO** un turno de la Dra. A de 10:00 a 10:30 que fue cancelado
- **CUANDO** se guarda otro turno de la Dra. A de 10:00 a 10:30
- **ENTONCES** se guarda, y el listado de la Dra. A muestra los dos (uno `cancelled` y uno `scheduled`)

#### Scenario: Turnos atendidos o ausentes no bloquean (borde)
- **DADO** un turno de la Dra. A de 10:00 a 10:30 marcado `completed` y otro de 10:30 a 11:00 marcado `no_show`
- **CUANDO** se guarda un turno de la Dra. A de 10:15 a 10:45
- **ENTONCES** se guarda

#### Scenario: Turno que cruza la medianoche choca por instantes (borde)
- **DADO** un turno `scheduled` de la Dra. A del lunes 23:45 al martes 00:15 (hora local)
- **CUANDO** se intenta guardar un turno de la Dra. A del martes 00:00 a 00:30
- **ENTONCES** se rechaza con el error `SLOT_TAKEN` (misma comparación de instantes que DD-19)

### Requirement: Buscar un turno por identificador

Buscar un turno SHALL devolver el turno guardado con ese identificador, o un valor "no encontrado" si no existe; un identificador inexistente no es un error.

#### Scenario: Turno existente (esperado)
- **DADO** un turno guardado de Juan Pérez con la Dra. A
- **CUANDO** se lo busca por su identificador
- **ENTONCES** se devuelve ese turno

#### Scenario: Identificador inexistente (borde)
- **DADO** un repositorio con un turno guardado
- **CUANDO** se busca un identificador que nunca se guardó
- **ENTONCES** el resultado es "no encontrado", sin error

### Requirement: Cambiar el estado de un turno

Cambiar el estado SHALL guardar el nuevo estado y, al cancelar, el motivo de cancelación (`cancel_reason`), y MUST devolver el turno actualizado. El repositorio no decide si la transición es válida: eso lo hace `appointment-status-transitions` en el caso de uso (C-08). El repositorio MUST igualmente rechazar con `SLOT_TAKEN` un cambio a `scheduled` que deje dos turnos `scheduled` superpuestos, como la base. Cambiar el estado de un identificador inexistente MUST rechazarse con el error de dominio de turno inexistente (`APPOINTMENT_NOT_FOUND`).

#### Scenario: Cancelar con motivo libera el horario (esperado)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se cambia a `cancelled` con el motivo "El paciente avisó por teléfono"
- **ENTONCES** buscarlo devuelve estado `cancelled` y ese motivo
- **Y** guardar después otro turno de la Dra. A de 10:00 a 10:30 se acepta (RN-TU-05)

#### Scenario: Marcar atendido (esperado)
- **DADO** un turno `scheduled` de la Dra. A
- **CUANDO** se cambia a `completed`
- **ENTONCES** buscarlo devuelve estado `completed` y sin motivo de cancelación

#### Scenario: Volver a scheduled sobre un horario ya tomado (borde)
- **DADO** un turno cancelado de la Dra. A de 10:00 a 10:30 y otro `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se intenta cambiar el cancelado a `scheduled`
- **ENTONCES** se rechaza con `SLOT_TAKEN` y el turno sigue `cancelled` (el repositorio no permite saltear la base aunque el caso de uso fallara)

#### Scenario: Cambiar el estado de un turno inexistente (error de negocio)
- **DADO** un repositorio vacío
- **CUANDO** se intenta cancelar un identificador que nunca se guardó
- **ENTONCES** se rechaza con `APPOINTMENT_NOT_FOUND`

### Requirement: Reprogramar un turno en una sola operación (RN-TU-06)

Reprogramar SHALL cambiar inicio y fin de un turno existente en una sola operación y MUST devolver el turno actualizado, con el mismo identificador, paciente y profesional. Si el nuevo rango se superpone con otro turno `scheduled` del mismo profesional, MUST rechazarse con `SLOT_TAKEN` y el turno original MUST quedar sin cambios (no se ejecuta parcialmente). El turno no choca consigo mismo: moverlo a un rango que se superpone con su propio horario anterior se acepta. Inicio y fin inválidos siguen la misma regla que al guardar (`ValueError`). Un identificador inexistente MUST rechazarse con `APPOINTMENT_NOT_FOUND`.

#### Scenario: Reprogramar a un horario libre (esperado)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30
- **CUANDO** se lo reprograma a 11:00 a 11:30
- **ENTONCES** buscarlo devuelve 11:00 a 11:30 con el mismo identificador y paciente
- **Y** guardar otro turno de la Dra. A de 10:00 a 10:30 se acepta

#### Scenario: Reprogramar sobre un turno ocupado no cambia el original (error de negocio)
- **DADO** turnos `scheduled` de la Dra. A de 10:00 a 10:30 (Juan Pérez) y de 11:00 a 11:30 (Ana Gómez)
- **CUANDO** se intenta reprogramar el de Juan Pérez a 11:00 a 11:30
- **ENTONCES** se rechaza con `SLOT_TAKEN`
- **Y** el turno de Juan Pérez sigue de 10:00 a 10:30

#### Scenario: Reprogramar solapando su propio horario anterior (borde)
- **DADO** un turno `scheduled` de la Dra. A de 10:00 a 10:30 y ningún otro
- **CUANDO** se lo reprograma a 10:15 a 10:45
- **ENTONCES** se acepta (el turno no choca consigo mismo)

#### Scenario: Reprogramar un turno inexistente (error de negocio)
- **DADO** un repositorio vacío
- **CUANDO** se intenta reprogramar un identificador que nunca se guardó
- **ENTONCES** se rechaza con `APPOINTMENT_NOT_FOUND`

### Requirement: Listar los turnos de un profesional en un rango de tiempo

Listar SHALL recibir un profesional y un rango `[desde, hasta)` de instantes con zona horaria, con `hasta` opcional (sin límite superior), y MUST devolver todos los turnos de ese profesional cuyo rango se superpone con el pedido, en cualquier estado, ordenados por inicio. El rango es semiabierto: un turno que termina exactamente en `desde` o empieza exactamente en `hasta` no se incluye. Un turno que cruza un límite del rango (por ejemplo la medianoche local) se incluye. Este listado alimenta `validate_appointment` y `compute_slots` (C-08, C-09) y los conflictos de RN-HO-04 (C-07). Instantes sin zona horaria, o `desde` no anterior a `hasta`, MUST lanzar `ValueError`.

#### Scenario: Turnos del día local de un profesional (esperado)
- **DADO** turnos de la Dra. A el lunes a las 10:00 (`scheduled`) y a las 11:00 (`cancelled`), un turno de la Dra. A el martes a las 10:00, y un turno del Dr. B el lunes a las 10:00
- **CUANDO** se listan los turnos de la Dra. A desde el inicio hasta el fin del lunes local (convertidos a UTC)
- **ENTONCES** se devuelven los dos turnos del lunes de la Dra. A, el de las 10:00 primero, incluido el cancelado

#### Scenario: Límites semiabiertos del rango (borde)
- **DADO** turnos de la Dra. A de 09:30 a 10:00, de 10:00 a 10:30 y de 11:00 a 11:30
- **CUANDO** se listan los turnos de la Dra. A desde las 10:00 hasta las 11:00
- **ENTONCES** se devuelve solo el de 10:00 a 10:30

#### Scenario: Turno que cruza la medianoche aparece en ambos días (borde)
- **DADO** un turno de la Dra. A del lunes 23:45 al martes 00:15 (hora local)
- **CUANDO** se listan los turnos de la Dra. A del martes local completo
- **ENTONCES** ese turno se incluye (DD-19)

#### Scenario: Turnos futuros sin límite superior (esperado)
- **DADO** turnos de la Dra. A el lunes 5, el viernes 9 y el lunes 12 de octubre
- **CUANDO** se listan los turnos de la Dra. A desde el martes 6 a las 00:00 sin límite superior
- **ENTONCES** se devuelven los del viernes 9 y el lunes 12, en ese orden

#### Scenario: Profesional sin turnos (borde)
- **DADO** un repositorio con turnos solo del Dr. B
- **CUANDO** se listan los turnos de la Dra. A del lunes
- **ENTONCES** se devuelve una lista vacía

#### Scenario: Rango inválido (borde)
- **DADO** un repositorio cualquiera
- **CUANDO** se listan turnos con `desde` sin zona horaria, o con `desde` igual o posterior a `hasta`
- **ENTONCES** se lanza `ValueError`

### Requirement: Listar los turnos de un paciente en un rango de tiempo

Listar por paciente SHALL seguir las mismas reglas de rango, estados y orden que el listado por profesional, filtrando por paciente en lugar de profesional. Lo usa C-06/C-08 para mostrar los turnos futuros de un paciente que se desactiva (DD-25).

#### Scenario: Turnos futuros de un paciente con varios profesionales (esperado)
- **DADO** turnos de Juan Pérez con la Dra. A el lunes 10:00 y con el Dr. B el lunes 15:00, y un turno de Ana Gómez el lunes 11:00
- **CUANDO** se listan los turnos de Juan Pérez desde el lunes 00:00 sin límite superior
- **ENTONCES** se devuelven los dos turnos de Juan Pérez ordenados por inicio

#### Scenario: Paciente sin turnos (borde)
- **DADO** un repositorio con turnos solo de Ana Gómez
- **CUANDO** se listan los turnos de Juan Pérez
- **ENTONCES** se devuelve una lista vacía

### Requirement: Conversión al dato que consumen las reglas de agenda

Cada turno guardado SHALL poder convertirse, sin pérdida de profesional, inicio, fin ni estado, al dato de turno existente que ya reciben `validate_appointment` y `compute_slots`, de modo que el listado del repositorio se les pase directamente sin cambiar esas capabilities.

#### Scenario: El listado alimenta la validación de un turno nuevo (esperado)
- **DADO** un turno `scheduled` guardado de la Dra. A de 10:00 a 10:30
- **CUANDO** el listado del lunes de la Dra. A, convertido, se pasa a la validación de un turno de la Dra. A a las 10:00 (con su horario de 09:00 a 13:00 y anticipación suficiente)
- **ENTONCES** la validación rechaza con `OVERLAPS_EXISTING`, igual que si el dato se hubiera armado a mano
