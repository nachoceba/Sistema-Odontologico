# frontend-agenda Specification

## Purpose
Darle a recepción, administración y odontólogos una pantalla `/agenda` para ver la agenda de un profesional por día y por semana, con franjas libres, ocupadas y fuera de horario diferenciadas, en la hora del consultorio (US-006, RN-AU-04, RN-GL-01). La pantalla también permite agendar, cancelar, reprogramar y marcar atención, según las acciones que corresponden a cada rol (spec `frontend-appointment-management`, C-10).

## Requirements

### Requirement: Acceso y profesional mostrado según el rol (RN-AU-04, DD-53, P-6, P-8)

La ruta protegida `/agenda` SHALL estar disponible para los tres roles. Administración y recepción MUST ver un selector con las fichas que devuelve `GET /professionals` (las inactivas marcadas "(inactivo)") y ver la agenda de **un** profesional por vez; al entrar sin profesional elegido MUST mostrarse el primer profesional activo de la lista. Un odontólogo con ficha MUST ver solo su propia agenda, sin selector; si la dirección pide otro profesional, MUST mostrarse igual la suya. Un odontólogo sin ficha MUST ver "No tenés una ficha de profesional asociada" sin pedir turnos ni franjas. Si no hay ningún profesional, MUST mostrarse "Todavía no hay profesionales cargados". Al mirar un profesional con ficha inactiva MUST mostrarse el aviso "Profesional inactivo: no se le pueden dar turnos nuevos" junto con su agenda (DD-59, DD-64). Sin sesión, `/agenda` lleva a `/login`.

#### Scenario: Recepción elige profesional (esperado)
- **WHEN** la recepcionista abre `/agenda` y elige al Dr. B en el selector
- **THEN** ve la agenda del Dr. B y la dirección indica al Dr. B

#### Scenario: Primer profesional activo por defecto (esperado)
- **WHEN** el administrador abre `/agenda` sin profesional en la dirección y la lista tiene primero una ficha inactiva y después a la Dra. A
- **THEN** ve la agenda de la Dra. A y la ficha inactiva aparece en el selector como "(inactivo)"

#### Scenario: Profesional inactivo (borde)
- **WHEN** recepción elige una ficha inactiva que tiene turnos agendados la semana próxima
- **THEN** ve esos turnos, sus franjas y el aviso "Profesional inactivo: no se le pueden dar turnos nuevos"

#### Scenario: Odontóloga ve solo la suya (esperado)
- **WHEN** la Dra. A abre `/agenda`
- **THEN** ve su agenda, no ve el selector y la pantalla no pide datos de ningún otro profesional

#### Scenario: Odontóloga con la dirección de otro profesional (borde)
- **WHEN** la Dra. A abre `/agenda?profesional={Dr. B}`
- **THEN** ve su propia agenda y no se pide la agenda del Dr. B

#### Scenario: Odontólogo sin ficha (borde)
- **WHEN** un odontólogo sin ficha abre `/agenda`
- **THEN** ve "No tenés una ficha de profesional asociada" y no se pide ningún turno ni franja

#### Scenario: Sin sesión (error)
- **WHEN** alguien sin token abre `/agenda`
- **THEN** el frontend lo lleva a `/login`

### Requirement: Vista del día (US-006, P-2, P-3)

La vista "Día" SHALL mostrar, para el profesional y la fecha elegidos, las franjas del día con tres estados diferenciados por texto y no solo por color: "Libre", "Ocupado" (el turno que la ocupa) y "Fuera de horario". MUST mostrarse solo desde la primera franja libre u ocupada (o el primer turno, si es anterior) hasta la última franja libre u ocupada (o el último turno, si es posterior); las franjas fuera de horario anteriores y posteriores MUST omitirse y las contiguas que queden en medio MUST juntarse en una sola banda "Fuera de horario HH:MM–HH:MM" (incluido el resto de un tramo que no alcanza para un slot, DD-15, DD-30). Un turno que cae fuera de horario MUST mostrarse igual en su hora. Un turno que no coincide con el inicio de una franja MUST mostrarse en su propia hora de inicio y fin, y las franjas que ocupa MUST decir "Ocupado". Un día sin ningún tramo ni turno MUST mostrar "Sin atención este día". Todas las horas MUST mostrarse en la zona del consultorio con formato `HH:MM` de 24 horas (RN-GL-01). Una franja libre cuyo inicio ya pasó MUST seguir diciendo "Libre" (DD-17); la vista no aplica la anticipación mínima.

#### Scenario: Día de la Dra. A con un turno (esperado)
- **WHEN** la Dra. A atiende de 09:00 a 13:00 y de 14:00 a 18:00, tiene un turno de Juan Perez a las 10:00 y se abre la vista "Día" de ese lunes
- **THEN** se ven las franjas de 09:00 a 18:00, la de 10:00 dice "Ocupado" con "10:00–10:30 Perez, Juan", las demás dentro de tramos dicen "Libre" y entre 13:00 y 14:00 hay una sola banda "Fuera de horario 13:00–14:00"

#### Scenario: Día sin atención (borde)
- **WHEN** se abre la vista "Día" de un domingo sin tramos ni turnos
- **THEN** se ve "Sin atención este día"

#### Scenario: Hora local y no UTC (borde)
- **WHEN** la API devuelve una franja con inicio `2026-11-09T12:00:00Z`
- **THEN** la pantalla la muestra como 09:00

#### Scenario: Resto de tramo que no alcanza para un slot (borde)
- **WHEN** el tramo del día es de 09:00 a 10:45 con slots de 30 minutos
- **THEN** se ven libres 09:00, 09:30 y 10:00 y la vista termina a las 10:30, sin banda de 10:30 a 10:45 al final

#### Scenario: Turno desalineado con la grilla (borde)
- **WHEN** un turno agendado va de 09:15 a 09:45 y las franjas son 09:00, 09:30 y 10:00
- **THEN** el turno se ve como "09:15–09:45", las franjas de 09:00 y 09:30 dicen "Ocupado" y la de 10:00 "Libre"

#### Scenario: Turno que cruza la medianoche (borde)
- **WHEN** un turno empieza a las 23:45 del lunes y termina a las 00:15 del martes (hora del consultorio)
- **THEN** aparece en el lunes y también en el martes (DD-19)

### Requirement: Vista de la semana (US-006, P-2)

La vista "Semana" SHALL mostrar los siete días de lunes a domingo de la semana que contiene la fecha elegida, cada uno con su nombre y fecha (`Lun 09/11`) y con las mismas reglas que la vista del día. Cada día MUST armarse con sus propias franjas; las filas de días distintos no tienen que coincidir en hora (DD-15). El día de hoy MUST estar destacado. Elegir un día de la semana MUST abrir la vista "Día" de esa fecha.

#### Scenario: Semana con días sin atención (esperado)
- **WHEN** se abre la semana del lunes 09/11/2026 de la Dra. A, que atiende de lunes a viernes
- **THEN** se ven siete columnas de lunes 09/11 a domingo 15/11, y sábado y domingo dicen "Sin atención este día"

#### Scenario: Fecha a mitad de semana (borde)
- **WHEN** la dirección pide la vista "Semana" con fecha jueves 12/11/2026
- **THEN** la semana mostrada va del lunes 09/11 al domingo 15/11

#### Scenario: De la semana al día (esperado)
- **WHEN** en la vista "Semana" se elige el miércoles 11/11
- **THEN** se abre la vista "Día" del 11/11 del mismo profesional

### Requirement: Navegación entre fechas y estado en la dirección

La pantalla SHALL ofrecer "Anterior", "Siguiente" y "Hoy", un campo de fecha y la elección entre "Día" y "Semana". "Anterior" y "Siguiente" MUST mover un día en la vista "Día" y siete días en la vista "Semana". "Hoy" MUST usar la fecha actual en la zona del consultorio, no la del navegador. Profesional, fecha y vista MUST quedar en la dirección (`/agenda?profesional=…&fecha=AAAA-MM-DD&vista=dia|semana`) para que recargar la página muestre lo mismo; una fecha o una vista inválidas en la dirección MUST reemplazarse por hoy y "Día". Al entrar sin parámetros MUST mostrarse la vista "Día" de hoy.

#### Scenario: Siguiente semana (esperado)
- **WHEN** en la vista "Semana" del 09/11/2026 se aprieta "Siguiente"
- **THEN** se muestra la semana del lunes 16/11/2026

#### Scenario: Hoy según el consultorio (borde)
- **WHEN** en el navegador son las 01:00 UTC del martes 10/11/2026 (las 22:00 del lunes en el consultorio) y se aprieta "Hoy"
- **THEN** se muestra el lunes 09/11/2026

#### Scenario: Fecha inválida en la dirección (error)
- **WHEN** se abre `/agenda?fecha=2026-02-30`
- **THEN** se muestra la vista "Día" de hoy, sin error

#### Scenario: Recargar mantiene la vista (borde)
- **WHEN** la recepcionista está en la semana del 16/11 del Dr. B y recarga la página
- **THEN** sigue viendo la semana del 16/11 del Dr. B

### Requirement: Turnos y sus estados en la grilla (P-4, P-7)

Cada turno SHALL mostrarse con su hora de inicio y fin, el apellido y el nombre del paciente y su estado: "Agendado", "Atendido", "Ausente" o "Cancelado". Los turnos cancelados MUST verse atenuados y tachados junto a la franja, que sigue diciendo "Libre" (RN-TU-05). Los turnos atendidos y ausentes MUST mostrarse con su etiqueta en su hora (DD-16). La grilla MUST NOT mostrar email, teléfono ni documento del paciente.

#### Scenario: Turno cancelado deja la franja libre (esperado)
- **WHEN** un turno de las 11:00 de la Dra. A está cancelado y la franja de las 11:00 está libre
- **THEN** se ve "Libre" en las 11:00 y al lado el turno tachado con la etiqueta "Cancelado"

#### Scenario: Turno atendido y turno ausente (esperado)
- **WHEN** el día tiene un turno `completed` a las 09:00 y uno `no_show` a las 09:30
- **THEN** se ven con "Atendido" y "Ausente" en sus horas

#### Scenario: Cancelado y nuevo turno en la misma hora (borde)
- **WHEN** a las 11:00 hay un turno cancelado de Ana Gomez y uno agendado de Juan Perez
- **THEN** la franja dice "Ocupado" con Juan Perez y el turno de Ana Gomez se ve tachado como "Cancelado"

#### Scenario: Sin datos de contacto (borde)
- **WHEN** se muestra la grilla de cualquier día
- **THEN** no aparece ningún email, teléfono ni documento de paciente

### Requirement: Licencias y turnos en conflicto (RN-HO-03, RN-HO-04, DD-68, P-5)

Un día cubierto por una licencia del profesional SHALL mostrarse como "Licencia" con su motivo si lo tiene, en lugar de "Sin atención este día" o de las franjas fuera de horario. Los turnos que figuran en `GET /professionals/{id}/conflicts` MUST mostrarse con el aviso "En conflicto: fuera del horario" o "En conflicto: en licencia", según el motivo. Para administración y recepción, elegir un turno en conflicto MUST abrir su detalle con "Reprogramar" y "Cancelar", y la lista completa de conflictos con acceso a resolverlos la define `frontend-appointment-management`; el odontólogo ve el aviso sin acciones para resolverlo. Los turnos `scheduled` que no figuran en esa lista (por ejemplo, porque ya empezaron) MUST mostrarse sin aviso.

#### Scenario: Día de licencia (esperado)
- **WHEN** la Dra. A tiene una licencia del 12/11 al 13/11 con motivo "Congreso" y se abre su semana del 09/11
- **THEN** el jueves y el viernes dicen "Licencia: Congreso"

#### Scenario: Turno agendado en un día de licencia (error de negocio)
- **WHEN** la Dra. A tenía un turno agendado el 12/11 a las 10:00 antes de cargar la licencia
- **THEN** el jueves dice "Licencia: Congreso" y además muestra ese turno con "En conflicto: en licencia"

#### Scenario: Turno fuera del horario nuevo (error de negocio)
- **WHEN** se acortó el horario de la Dra. A y su turno futuro de las 17:30 quedó fuera
- **THEN** el turno se ve a las 17:30 con "En conflicto: fuera del horario"

#### Scenario: Recepción abre un turno en conflicto (esperado)
- **WHEN** la recepcionista elige en la grilla el turno en conflicto del 12/11 a las 10:00
- **THEN** se abre su detalle con "En conflicto: en licencia", "Reprogramar" y "Cancelar"

#### Scenario: Odontóloga ve el conflicto sin resolverlo (borde)
- **WHEN** la Dra. A elige su turno en conflicto del 12/11 a las 10:00 antes de que empiece
- **THEN** ve el detalle con "En conflicto: en licencia" y sin "Reprogramar" ni "Cancelar"

#### Scenario: Licencia sin motivo (borde)
- **WHEN** la licencia no tiene motivo
- **THEN** el día dice "Licencia"

#### Scenario: Turno pasado en un día de licencia (borde)
- **WHEN** se mira una semana pasada con una licencia cargada después de que ocurrió un turno `scheduled` de ese día
- **THEN** el día dice "Licencia" y el turno se ve sin aviso de conflicto, porque ya empezó (DD-68)

### Requirement: Carga, errores y navegación de la app

Mientras carga, la pantalla SHALL mostrar "Cargando…". Ante un error de red o un 5xx MUST mostrar "No se pudo conectar con el servidor" con la opción "Reintentar"; ante un 403 MUST mostrar "No tenés permiso para esta acción" sin cerrar la sesión; un 401 cierra la sesión como en `frontend-auth`. La pantalla MUST tener una barra de navegación con el nombre y el rol de la cuenta y los enlaces "Pacientes", "Profesionales", "Usuarios" (solo administración) y "Salir".

#### Scenario: Servidor caído (error)
- **WHEN** el pedido de franjas falla por red
- **THEN** se ve "No se pudo conectar con el servidor" y "Reintentar" vuelve a pedirlas

#### Scenario: Respuesta 403 (borde)
- **WHEN** la API responde 403 al pedir los turnos
- **THEN** se ve "No tenés permiso para esta acción" y la sesión sigue abierta

#### Scenario: Enlaces según el rol (esperado)
- **WHEN** la recepcionista abre `/agenda`
- **THEN** ve "Pacientes", "Profesionales" y "Salir" y no ve "Usuarios"

### Requirement: Pedidos y actualización de la agenda (regla dura 6, DD-83)

La pantalla `/agenda` SHALL enviar solo pedidos `GET` y estos pedidos de escritura: `POST /appointments`, `POST /appointments/{id}/cancel`, `POST /appointments/{id}/reschedule`, `POST /appointments/{id}/attendance` y `POST /patients` (alta de paciente desde el panel de agendar), cada uno solo como resultado de una acción confirmada por la persona según `frontend-appointment-management`. MUST NOT enviar `PUT`, `PATCH` ni `DELETE`. La pantalla del odontólogo MUST enviar como escritura solo `POST /appointments/{id}/attendance`. La información MUST volver a pedirse al cambiar profesional, fecha o vista, al apretar "Actualizar", después de cada acción correcta y después de cada rechazo con código de la API; no hay actualización automática por tiempo.

#### Scenario: Mirar no escribe (esperado)
- **WHEN** la recepcionista recorre la semana de la Dra. A y abre el detalle de dos turnos sin confirmar ninguna acción
- **THEN** la pantalla solo hizo pedidos `GET`

#### Scenario: Actualizar trae lo nuevo (esperado)
- **WHEN** otra recepcionista agendó un turno a las 15:00 y se aprieta "Actualizar"
- **THEN** la franja de las 15:00 pasa a "Ocupado" con ese turno

#### Scenario: Después de agendar se vuelve a pedir (esperado)
- **WHEN** la recepcionista agenda un turno a las 10:00
- **THEN** la agenda se vuelve a pedir y la franja de las 10:00 dice "Ocupado" sin apretar "Actualizar"

#### Scenario: Odontóloga solo marca atención (borde)
- **WHEN** la Dra. A usa su agenda durante un día y marca dos turnos
- **THEN** los únicos pedidos que no son `GET` fueron dos `POST /appointments/{id}/attendance`

### Requirement: Etiquetas de turnos online (DD-133)

En la grilla del día, en la vista de la semana y en el detalle del turno, cada turno `scheduled` con `pending_until` no nulo SHALL mostrar la etiqueta "Pendiente de confirmación", y su franja MUST verse ocupada. Cada turno con `origin = "online"` y sin `pending_until` MUST mostrar la etiqueta "Online" junto a su estado. Los turnos de recepción no llevan etiqueta. Las etiquetas MUST distinguirse por texto, no solo por color.

#### Scenario: Turno pendiente en la grilla (esperado)
- **WHEN** la Dra. A tiene a las 10:30 una reserva online sin confirmar
- **THEN** la grilla muestra la franja ocupada con el turno y la etiqueta "Pendiente de confirmación"

#### Scenario: Turno online confirmado (esperado)
- **WHEN** el paciente confirmó la reserva de las 10:30
- **THEN** la grilla muestra el turno con "Agendado" y la etiqueta "Online"

#### Scenario: Turno de recepción (borde)
- **WHEN** un turno lo agendó la recepción
- **THEN** no muestra ninguna de las dos etiquetas
