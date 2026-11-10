# frontend-appointment-management Specification

## Purpose
Permitir que recepción y administración agenden, cancelen y reprogramen turnos desde la agenda `/agenda`, que el odontólogo, recepción y administración marquen atendido o ausente, y que recepción resuelva los turnos en conflicto, usando los casos de uso de C-08 con mensajes de error claros y sin datos de otros pacientes.

## Requirements

### Requirement: Qué acciones ve cada rol según el estado y la hora del turno (RN-AU-02, RN-AU-04, DD-48, DD-64, P-5)

La agenda SHALL ofrecer solo las acciones que el rol puede hacer sobre esa franja o ese turno en ese momento, según esta tabla ("ahora" es la hora actual; el servidor sigue siendo quien decide):

| Acción | Quién la ve | Cuándo |
|---|---|---|
| "Agendar" en una franja | Administración y recepción | Franja "Libre" cuyo inicio es posterior a ahora y profesional activo (P-1) |
| "Cancelar" | Administración y recepción | Turno "Agendado" cuyo inicio es posterior a ahora (DD-21) |
| "Reprogramar" | Administración y recepción | Turno "Agendado" cuyo inicio es posterior a ahora (DD-24) y profesional activo (DD-64) |
| "Atendido" y "Ausente" | Odontólogo (solo sus turnos), recepción y administración | Turno "Agendado" cuyo inicio es igual o anterior a ahora (DD-23) |

Un turno "Cancelado", "Atendido" o "Ausente" MUST NOT ofrecer ninguna acción (DD-22, RN-TU-07). El odontólogo MUST NOT ver "Agendar", "Cancelar" ni "Reprogramar". Una acción que no corresponde MUST ocultarse, no mostrarse deshabilitada. Cancelar y marcar MUST seguir disponibles para un profesional inactivo (DD-59, DD-64).

#### Scenario: Recepción ve agendar, cancelar y reprogramar (esperado)
- **WHEN** la recepcionista mira el día de mañana de la Dra. A, con una franja libre a las 09:00 y un turno agendado de Juan Perez a las 10:00
- **THEN** la franja de las 09:00 ofrece "Agendar" y el turno de las 10:00 ofrece "Cancelar" y "Reprogramar", sin "Atendido" ni "Ausente"

#### Scenario: Odontóloga solo marca (esperado)
- **WHEN** la Dra. A mira su día de hoy a las 10:10, con un turno agendado de 10:00 a 10:30 y una franja libre a las 11:00
- **THEN** el turno ofrece "Atendido" y "Ausente", y no ve "Agendar", "Cancelar" ni "Reprogramar" en ninguna parte

#### Scenario: Franja libre que ya empezó (borde)
- **WHEN** son las 10:05 y la franja de 10:00 a 10:30 de hoy dice "Libre"
- **THEN** sigue diciendo "Libre" (DD-17) pero no ofrece "Agendar"

#### Scenario: Turno en su hora exacta de inicio (borde)
- **WHEN** son exactamente las 10:00 y la recepcionista mira el turno agendado de las 10:00
- **THEN** ofrece "Atendido" y "Ausente" y no ofrece "Cancelar" ni "Reprogramar" (DD-23)

#### Scenario: Profesional inactivo (error de negocio)
- **WHEN** la recepcionista mira la agenda de un profesional con ficha inactiva que tiene un turno agendado mañana y franjas libres
- **THEN** ninguna franja ofrece "Agendar", el turno ofrece "Cancelar" y no ofrece "Reprogramar" (DD-64)

#### Scenario: Turnos terminados sin acciones (borde)
- **WHEN** el día tiene un turno "Cancelado", uno "Atendido" y uno "Ausente"
- **THEN** ninguno de los tres ofrece acciones; elegirlos muestra solo su detalle

### Requirement: Agendar desde una franja libre (US-007, Flujo 2, RN-TU-01 a RN-TU-04, RN-TU-12)

"Agendar" en una franja libre SHALL abrir un panel con la fecha y la hora local de la franja (`Lun 09/11 10:00–10:30`) y el nombre del profesional, donde se elige o se crea el paciente. El botón "Agendar turno" MUST estar habilitado solo con un paciente elegido y MUST enviar un único `POST /api/v1/appointments` con el paciente, el profesional y el inicio de la franja tal como lo devolvió el servidor; mientras espera MUST quedar deshabilitado (un doble clic envía un solo pedido). Con 201, el panel MUST cerrarse, mostrarse "Turno agendado: <Apellido, Nombre>, <día> <HH:MM>. Se enviará la confirmación por email al paciente." y la agenda MUST volver a pedirse, con la franja ahora "Ocupado". Con un rechazo, el panel MUST quedar abierto con el mensaje del código (requirement "Mensajes de error por código"), el paciente elegido MUST conservarse y la agenda MUST volver a pedirse detrás. El aviso de éxito MUST NOT decir que el email ya se envió ni mostrar la dirección del paciente: el envío es posterior y lo hace el servidor (C-11, P-8).

#### Scenario: Agendar en una franja libre (esperado)
- **WHEN** la recepcionista elige "Agendar" en la franja de las 10:00 del lunes 09/11 de la Dra. A, busca y elige a Juan Perez y aprieta "Agendar turno"
- **THEN** se envía `POST /api/v1/appointments` con Juan Perez, la Dra. A y el inicio de esa franja, se ve "Turno agendado: Perez, Juan, Lun 09/11 10:00. Se enviará la confirmación por email al paciente." y la franja de las 10:00 pasa a "Ocupado" con "10:00–10:30 Perez, Juan"

#### Scenario: Otra recepcionista ocupó el horario (error de negocio)
- **WHEN** la franja de las 10:00 se ve "Libre" pero otra recepcionista acaba de agendar ahí, y se aprieta "Agendar turno"
- **THEN** la API responde 409 `SLOT_TAKEN`, el panel muestra "Ese horario se acaba de ocupar. Elegí otro horario" y la franja de las 10:00 pasa a "Ocupado" al volver a pedir la agenda

#### Scenario: Franja libre sin anticipación suficiente (error de negocio)
- **WHEN** faltan 2 horas para una franja libre, el consultorio pide 6 horas de anticipación y se intenta agendar
- **THEN** la API responde 400 `INSUFFICIENT_NOTICE` y el panel muestra "Ese horario ya pasó o no respeta la anticipación mínima del consultorio"

#### Scenario: Paciente con otro turno a esa hora (error de negocio)
- **WHEN** Juan Perez ya tiene un turno a las 10:00 con el Dr. B y se lo intenta agendar a las 10:00 con la Dra. A
- **THEN** el panel muestra "El paciente ya tiene otro turno en ese horario" sin ningún dato del otro turno ni de otro paciente

#### Scenario: Sin paciente elegido (borde)
- **WHEN** se abre el panel de agendar y todavía no se eligió paciente
- **THEN** "Agendar turno" está deshabilitado y no se envía ningún pedido

#### Scenario: Doble clic (borde)
- **WHEN** se aprieta dos veces seguidas "Agendar turno"
- **THEN** se envía un solo `POST /api/v1/appointments`

#### Scenario: Cerrar el panel sin agendar (borde)
- **WHEN** se abre el panel, se elige a un paciente y se aprieta "Cerrar"
- **THEN** no se envía ningún pedido de escritura y la franja sigue "Libre"

#### Scenario: El aviso no muestra el email del paciente (borde)
- **WHEN** se agenda a Juan Perez, cuyo email es `juan.perez@example.com`
- **THEN** el aviso de éxito no contiene `juan.perez@example.com`

### Requirement: Buscar o crear el paciente al agendar (DD-74, DD-78, RN-PA-04, P-6)

El panel de agendar SHALL usar el buscador de pacientes activos de `frontend-patient-management` y mostrar debajo del cuadro el aviso "La búsqueda distingue tildes: si el apellido lleva tilde, escribilo con tilde (por ejemplo, Pérez)". Elegir un paciente MUST mostrarlo como elegido ("Paciente: Perez, Juan") con la opción "Cambiar". "Nuevo paciente" MUST abrir el formulario de alta de `frontend-patient-management` dentro del panel; al guardarse, el paciente creado MUST quedar elegido sin volver a buscarlo, y "Cancelar" en el formulario MUST volver a la búsqueda. El panel MUST NOT ofrecer pacientes inactivos (RN-PA-04). Un paciente creado desde el panel MUST quedar guardado aunque el turno después se rechace.

#### Scenario: Elegir un paciente existente (esperado)
- **WHEN** en el panel se escribe `torres` y se elige a Lucía Torres
- **THEN** el panel muestra "Paciente: Torres, Lucía" con "Cambiar" y habilita "Agendar turno"

#### Scenario: Crear el paciente en el momento (esperado)
- **WHEN** en el panel se aprieta "Nuevo paciente", se completan los datos obligatorios de Laura Ruiz y se guarda
- **THEN** se envía `POST /api/v1/patients`, el panel muestra "Paciente: Ruiz, Laura" y "Agendar turno" queda habilitado

#### Scenario: Buscar sin tilde (borde)
- **WHEN** se escribe `perez` y la única paciente es Pérez, Ana
- **THEN** se ve "No se encontraron pacientes" y el aviso de las tildes sigue visible debajo del cuadro (DD-74)

#### Scenario: Paciente inactivo no aparece (error de negocio)
- **WHEN** se escribe `gomez` y Ana Gómez está inactiva
- **THEN** el buscador muestra "No se encontraron pacientes" y no se la puede elegir

#### Scenario: Documento repetido al crear (error de negocio)
- **WHEN** al crear el paciente en el panel la API responde 409 `DOCUMENT_TAKEN`
- **THEN** el formulario muestra "Ya existe un paciente con ese documento" con los datos escritos, y ningún paciente queda elegido

#### Scenario: Paciente creado y turno rechazado (borde)
- **WHEN** se crea a Laura Ruiz desde el panel y al agendar la API responde `SLOT_TAKEN`
- **THEN** Laura Ruiz queda guardada y elegida en el panel, y se ve el mensaje del horario ocupado

### Requirement: Detalle del turno (P-5)

Elegir un turno en la grilla SHALL abrir un panel de detalle con la fecha y la hora local, "Apellido, Nombre" del paciente, el profesional, el estado ("Agendado", "Atendido", "Ausente" o "Cancelado"), el motivo de cancelación si está cancelado y el aviso de conflicto si lo tiene, más las acciones de la tabla de acciones. El detalle MUST NOT mostrar email, teléfono ni documento del paciente. Abrir el detalle MUST NOT enviar ningún pedido de escritura.

#### Scenario: Detalle de un turno agendado (esperado)
- **WHEN** la recepcionista elige el turno de Juan Perez del martes 10/11 a las 10:00
- **THEN** ve "Mar 10/11 10:00–10:30", "Perez, Juan", "Agendado", "Cancelar" y "Reprogramar"

#### Scenario: Detalle de un turno cancelado (esperado)
- **WHEN** elige un turno cancelado con el motivo "El paciente avisó por teléfono"
- **THEN** ve "Cancelado" y "Motivo: El paciente avisó por teléfono", sin acciones

#### Scenario: Sin datos de contacto (borde)
- **WHEN** se abre el detalle de cualquier turno
- **THEN** no aparece ningún email, teléfono ni documento del paciente

### Requirement: Cancelar con motivo (US-008, Flujo 3, RN-TU-05, DD-21, DD-65, P-2)

"Cancelar" SHALL abrir un diálogo "Cancelar el turno de <Apellido, Nombre> del <día> <HH:MM>" con un campo "Motivo" obligatorio. Un motivo vacío o solo con espacios MUST mostrar "Escribí el motivo de la cancelación" sin llamar a la API; el campo MUST aceptar hasta 500 caracteres. "Cancelar turno" MUST enviar un único `POST /api/v1/appointments/{id}/cancel` con el motivo; con 200 MUST cerrarse el diálogo, mostrarse "Turno cancelado" y la agenda MUST volver a pedirse, con la franja otra vez "Libre" y el turno tachado como "Cancelado". "Volver" MUST cerrar el diálogo sin llamar a la API.

#### Scenario: Cancelar libera la franja (esperado)
- **WHEN** la recepcionista cancela el turno de Juan Perez de mañana a las 10:00 con el motivo "El paciente avisó por teléfono"
- **THEN** se envía `POST /api/v1/appointments/{id}/cancel` con ese motivo, se ve "Turno cancelado", la franja de las 10:00 dice "Libre" con "Agendar" y al lado el turno tachado "Cancelado"

#### Scenario: Motivo vacío (error)
- **WHEN** se aprieta "Cancelar turno" con el motivo "   "
- **THEN** se ve "Escribí el motivo de la cancelación" y no se llama a la API

#### Scenario: El turno empezó mientras el diálogo estaba abierto (error de negocio)
- **WHEN** se abre el diálogo a las 09:59 para el turno de las 10:00 y se confirma a las 10:01
- **THEN** la API responde 409 `ALREADY_STARTED`, se ve "El turno ya empezó: no se puede cancelar ni reprogramar" y la agenda vuelve a pedirse

#### Scenario: Otro usuario ya lo canceló (borde)
- **WHEN** la API responde 409 `CANCELLED_IS_FINAL`
- **THEN** se ve "El turno ya estaba cancelado" y la agenda vuelve a pedirse, con el turno tachado

#### Scenario: Paciente inactivo se puede cancelar (borde)
- **WHEN** Ana Gómez fue desactivada con un turno agendado mañana y la recepcionista lo cancela con un motivo
- **THEN** la API responde 200 y el turno queda "Cancelado" (DD-76)

#### Scenario: Volver sin cancelar (borde)
- **WHEN** se abre el diálogo y se aprieta "Volver"
- **THEN** no se llama a la API y el turno sigue "Agendado"

### Requirement: Reprogramar a otra franja libre del mismo profesional (US-009, Flujo 3, RN-TU-06, DD-24, DD-25, DD-64, DD-67, P-3)

"Reprogramar" SHALL abrir un diálogo con un campo de fecha (al abrir, la fecha del turno) y las franjas "Libre" de ese día del mismo profesional cuyo inicio es posterior a ahora, pedidas a `GET /api/v1/professionals/{id}/slots`. Sin franjas para ofrecer MUST mostrarse "No hay horarios libres este día". Elegir una franja MUST mostrar "Mover de <día> <HH:MM> a <día> <HH:MM>" y "Reprogramar turno", que envía un único `POST /api/v1/appointments/{id}/reschedule` con el inicio de esa franja. Con 200 MUST cerrarse el diálogo, mostrarse "Turno reprogramado: <día> <HH:MM>. Se enviará la confirmación por email al paciente." y la agenda MUST volver a pedirse. Con un rechazo, el diálogo MUST mostrar el mensaje del código y el turno MUST verse sin cambios al volver a pedir la agenda (RN-TU-06). El profesional no cambia (DD-64): para cambiarlo se cancela y se agenda de nuevo.

#### Scenario: Reprogramar a otro día (esperado)
- **WHEN** la recepcionista reprograma el turno de Juan Perez del lunes 09/11 10:00, cambia la fecha al martes 10/11, elige 11:00 y aprieta "Reprogramar turno"
- **THEN** se envía `POST /api/v1/appointments/{id}/reschedule` con ese inicio, se ve "Turno reprogramado: Mar 10/11 11:00. Se enviará la confirmación por email al paciente.", y la franja del lunes a las 10:00 vuelve a "Libre"

#### Scenario: La nueva franja se ocupó (error de negocio)
- **WHEN** se elige las 11:00 y antes de confirmar otra recepcionista agenda ahí
- **THEN** la API responde 409 `SLOT_TAKEN`, el diálogo muestra "Ese horario se acaba de ocupar. Elegí otro horario" y el turno de Juan Perez sigue el lunes a las 10:00

#### Scenario: Paciente desactivado (error de negocio)
- **WHEN** Ana Gómez fue desactivada después de agendar y se intenta reprogramar su turno
- **THEN** se ve "El paciente está inactivo: reactivalo desde Pacientes para darle o moverle turnos" y el turno no cambia (DD-25)

#### Scenario: Día sin horarios libres (borde)
- **WHEN** se elige en el diálogo un domingo sin atención, o un día de licencia del profesional
- **THEN** se ve "No hay horarios libres este día" y no hay franjas para elegir

#### Scenario: El horario actual no se ofrece (borde)
- **WHEN** se abre el diálogo en la fecha del turno
- **THEN** la franja del propio turno no aparece entre las opciones (está "Ocupado"), así que no se puede pedir el mismo horario (DD-67)

#### Scenario: Volver sin reprogramar (borde)
- **WHEN** se elige una franja y se aprieta "Volver"
- **THEN** no se envía ningún pedido de escritura y el turno sigue igual

### Requirement: Marcar atendido o ausente (US-010, RN-TU-07, DD-22, DD-23, DD-64, P-4)

"Atendido" y "Ausente" SHALL pedir confirmación: "¿Marcar a <Apellido, Nombre> como atendido?" (o "ausente") con el aviso "Después no se puede cambiar". Confirmar MUST enviar un único `POST /api/v1/appointments/{id}/attendance` con `completed` o `no_show`; con 200 MUST mostrarse "Asistencia registrada" y la agenda MUST volver a pedirse con el turno "Atendido" o "Ausente". Cancelar la confirmación MUST NOT llamar a la API.

#### Scenario: Odontóloga marca atendido (esperado)
- **WHEN** son las 10:10 y la Dra. A marca "Atendido" su turno de las 10:00 de Juan Perez y confirma
- **THEN** se envía `POST /api/v1/appointments/{id}/attendance` con `completed`, se ve "Asistencia registrada" y el turno dice "Atendido" sin acciones

#### Scenario: Recepción marca ausente (esperado)
- **WHEN** son las 10:40 y la recepcionista marca "Ausente" el turno de las 10:00 de la Dra. A y confirma
- **THEN** se envía `no_show` y el turno dice "Ausente"

#### Scenario: Ya estaba registrada (error de negocio)
- **WHEN** la Dra. A confirma "Atendido" y la API responde 409 `ATTENDANCE_ALREADY_RECORDED` porque recepción lo marcó antes
- **THEN** se ve "Este turno ya tiene la asistencia registrada" y la agenda vuelve a pedirse

#### Scenario: Reloj del navegador adelantado (borde)
- **WHEN** el navegador cree que ya son las 10:00 pero en el servidor son las 09:58, y se confirma "Ausente"
- **THEN** la API responde 409 `NOT_STARTED_YET` y se ve "El turno todavía no empezó: la asistencia se marca desde su hora de inicio"

#### Scenario: Cancelar la confirmación (borde)
- **WHEN** se aprieta "Atendido" y después "Cancelar" en la confirmación
- **THEN** no se llama a la API y el turno sigue "Agendado"

### Requirement: Mensajes de error por código (spec appointment-api, error-model, P-7)

Cada rechazo de una acción SHALL mostrarse con este texto, según `error.code`:

| Código | Mensaje |
|---|---|
| `SLOT_TAKEN` | Ese horario se acaba de ocupar. Elegí otro horario |
| `OUTSIDE_WORKING_HOURS` | Ese horario está fuera del horario de atención del profesional |
| `PROFESSIONAL_TIME_OFF` | El profesional está de licencia ese día |
| `INSUFFICIENT_NOTICE` | Ese horario ya pasó o no respeta la anticipación mínima del consultorio |
| `OFF_GRID` | Ese horario no coincide con la grilla de turnos del profesional |
| `PATIENT_INACTIVE` | El paciente está inactivo: reactivalo desde Pacientes para darle o moverle turnos |
| `PROFESSIONAL_INACTIVE` | El profesional está inactivo: no se le pueden dar ni mover turnos |
| `PATIENT_DOUBLE_BOOKED` | El paciente ya tiene otro turno en ese horario |
| `ALREADY_STARTED` | El turno ya empezó: no se puede cancelar ni reprogramar |
| `CANCELLED_IS_FINAL` | El turno ya estaba cancelado |
| `ATTENDANCE_ALREADY_RECORDED` | Este turno ya tiene la asistencia registrada |
| `NOT_STARTED_YET` | El turno todavía no empezó: la asistencia se marca desde su hora de inicio |
| `RESCHEDULE_SAME_TIME` | El turno ya está en ese horario |
| `APPOINTMENT_NOT_FOUND` | El turno ya no existe |
| `PATIENT_NOT_FOUND` | El paciente ya no existe |
| `PROFESSIONAL_NOT_FOUND` | El profesional ya no existe |

Un 403 MUST mostrar "No tenés permiso para esta acción" sin cerrar la sesión; un 422, "Revisá los datos ingresados"; un error de red o un 5xx, "No se pudo conectar con el servidor"; un 401 cierra la sesión como en `frontend-auth`. Un código que no está en la tabla MUST mostrar el mensaje en castellano que trae la API. Ningún mensaje MUST incluir datos de otro paciente. Después de cualquier rechazo con código de la tabla, la agenda MUST volver a pedirse.

#### Scenario: Fuera de horario (error de negocio)
- **WHEN** al agendar la API responde 400 `OUTSIDE_WORKING_HOURS`
- **THEN** se ve "Ese horario está fuera del horario de atención del profesional"

#### Scenario: Sin permiso (borde)
- **WHEN** la API responde 403 al cancelar
- **THEN** se ve "No tenés permiso para esta acción" y la sesión sigue abierta

#### Scenario: Servidor caído (error)
- **WHEN** el pedido de agendar falla por red
- **THEN** se ve "No se pudo conectar con el servidor", el panel sigue abierto con el paciente elegido y se puede volver a intentar

#### Scenario: Código desconocido (borde)
- **WHEN** la API responde 409 con un código que no está en la tabla y el mensaje "No se pudo completar la operación"
- **THEN** se ve "No se pudo completar la operación"

### Requirement: Turnos en conflicto con acceso a resolverlos (RN-HO-04, Flujo 5, DD-68, P-8)

Para administración y recepción, cuando `GET /api/v1/professionals/{id}/conflicts` del profesional elegido trae turnos, la agenda SHALL mostrar el aviso "N turnos en conflicto" (o "1 turno en conflicto") con la lista de todos, aunque estén fuera del día o la semana a la vista, ordenados por inicio: fecha y hora local, "Apellido, Nombre" del paciente (leído con `GET /api/v1/appointments/{id}`), el motivo ("En conflicto: fuera del horario" o "En conflicto: en licencia") y los botones "Reprogramar" y "Cancelar", que abren los mismos diálogos que en el detalle, y "Ver en la agenda", que abre la vista "Día" de esa fecha. Sin conflictos MUST NOT mostrarse el aviso. Con el profesional inactivo MUST ofrecerse solo "Cancelar" (DD-64). El odontólogo MUST NOT ver el aviso ni la lista (sigue viendo la marca de conflicto en cada turno). Resolver un turno MUST volver a pedir la lista; un turno reprogramado a un horario válido o cancelado MUST dejar de figurar.

#### Scenario: Licencia con dos turnos afectados (esperado)
- **WHEN** la Dra. A tiene una licencia el 12/11 con dos turnos agendados a las 09:00 y 10:00, y la recepcionista abre la agenda de la Dra. A en la semana del 02/11
- **THEN** ve "2 turnos en conflicto" con "Jue 12/11 09:00–09:30" y "Jue 12/11 10:00–10:30", el nombre de cada paciente, "En conflicto: en licencia" y los botones "Reprogramar", "Cancelar" y "Ver en la agenda"

#### Scenario: Cancelar desde la lista (esperado)
- **WHEN** la recepcionista cancela desde la lista el turno de las 09:00 del 12/11 con el motivo "La profesional está de licencia"
- **THEN** el turno se cancela, el aviso pasa a "1 turno en conflicto" y solo queda el de las 10:00

#### Scenario: Reprogramar desde la lista (esperado)
- **WHEN** la recepcionista reprograma desde la lista el turno de las 10:00 del 12/11 al lunes 16/11 a las 10:00, libre y dentro del horario
- **THEN** el turno deja de figurar en la lista y aparece el 16/11 a las 10:00 sin marca de conflicto

#### Scenario: Reprogramar a otro día de licencia (error de negocio)
- **WHEN** desde la lista se intenta mover un turno a un horario que el servidor rechaza con `PROFESSIONAL_TIME_OFF`
- **THEN** se ve "El profesional está de licencia ese día" y el turno sigue en la lista sin cambios

#### Scenario: Sin conflictos (borde)
- **WHEN** el profesional elegido no tiene turnos en conflicto
- **THEN** no se ve ningún aviso de conflictos

#### Scenario: Odontóloga con turnos en conflicto (borde)
- **WHEN** la Dra. A abre su agenda y tiene un turno en conflicto
- **THEN** ve la marca "En conflicto: en licencia" en ese turno y no ve el aviso ni los botones para resolverlo

#### Scenario: Profesional inactivo con conflictos (borde)
- **WHEN** la recepcionista mira un profesional inactivo con un turno en conflicto
- **THEN** la lista ofrece "Cancelar" y "Ver en la agenda", y no "Reprogramar"

### Requirement: Acciones sobre un turno pendiente de confirmación (DD-133)

En el detalle de un turno pendiente de confirmación, la recepción y el administrador SHALL ver "Pendiente de confirmación hasta las HH:MM" (hora local) y solo la acción "Cancelar", con el mismo diálogo de motivo. Nunca MUST ver "Reprogramar" ni "Marcar atendido o ausente". El odontólogo ve el detalle sin acciones. Ante un `PENDING_CONFIRMATION` de la API, la pantalla MUST mostrar "Este turno espera la confirmación del paciente." y recargar el turno.

#### Scenario: Detalle de un pendiente para la recepción (esperado)
- **WHEN** la recepción abre un turno pendiente que vence a las 13:00
- **THEN** ve "Pendiente de confirmación hasta las 13:00" y solo "Cancelar"

#### Scenario: Pendiente para el odontólogo (borde)
- **WHEN** el odontólogo abre un turno propio pendiente
- **THEN** ve el detalle sin acciones

#### Scenario: Se venció mientras estaba abierto (error)
- **WHEN** la recepción cancela un pendiente que la tarea ya canceló
- **THEN** ve el mensaje de turno ya cancelado de siempre y el turno recargado
