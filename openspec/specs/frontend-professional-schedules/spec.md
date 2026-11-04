# frontend-professional-schedules Specification

## Purpose
Darle al administrador una pantalla `/profesionales` para editar fichas, horarios semanales y licencias y ver qué turnos quedaron en conflicto, y a recepción y odontólogos una vista de solo lectura según la matriz de permisos (US-004, US-005, Flujo 5).

## Requirements

### Requirement: Acceso a la pantalla de profesionales (matriz RBAC)

El frontend SHALL ofrecer la ruta protegida `/profesionales` y el enlace "Profesionales" para los tres roles. El administrador MUST ver los controles de edición; recepción y odontólogo MUST ver la misma información sin botones ni formularios de edición. El odontólogo MUST ver solo su propia ficha; un odontólogo sin ficha MUST ver "No tenés una ficha de profesional asociada" sin errores. Sin sesión, `/profesionales` lleva a `/login`.

#### Scenario: Administrador ve los controles (esperado)
- **WHEN** el administrador abre `/profesionales` y elige a la Dra. A
- **THEN** ve el horario, las licencias y los botones "Editar ficha", "Guardar horario", "Agregar licencia" y "Borrar" en cada licencia

#### Scenario: Recepción en modo lectura (esperado)
- **WHEN** la recepcionista abre `/profesionales` y elige a la Dra. A
- **THEN** ve el horario y las licencias de la Dra. A y no ve ningún botón de edición

#### Scenario: Odontóloga ve solo lo suyo (esperado)
- **WHEN** la Dra. A abre `/profesionales`
- **THEN** ve solo su ficha, su horario y sus licencias, sin selector de otros profesionales

#### Scenario: Sin sesión (borde)
- **WHEN** alguien sin token abre `/profesionales`
- **THEN** el frontend lo lleva a `/login`

### Requirement: Listado de fichas y edición de la ficha

La pantalla SHALL listar las fichas que devuelve la API, con nombre a mostrar, matrícula y estado ("Activo" o "Inactivo"), en el orden recibido. El administrador MUST poder editar nombre a mostrar y matrícula; un nombre vacío MUST mostrar "El nombre a mostrar es obligatorio" sin llamar a la API. Mientras carga MUST mostrarse "Cargando…" y ante un error de red o un 5xx "No se pudo conectar con el servidor".

#### Scenario: Ficha inactiva marcada (esperado)
- **WHEN** la API devuelve dos fichas y la del Dr. B está inactiva
- **THEN** el listado muestra las dos y la del Dr. B con el estado "Inactivo"

#### Scenario: Nombre vacío (error)
- **WHEN** el administrador borra el nombre a mostrar y guarda
- **THEN** ve "El nombre a mostrar es obligatorio" y no se envía ningún pedido

### Requirement: Editor del horario semanal

El editor SHALL mostrar los siete días (lunes a domingo) con sus tramos y permitir al administrador agregar y quitar tramos, varios por día, con horas `HH:MM`, y guardar la semana completa de una vez. Un rechazo `INVALID_WORKING_HOURS` MUST mostrarse junto al día afectado con el mensaje de la API ("Los tramos se superponen", "El inicio debe ser anterior al fin"), sin perder lo escrito. Tras guardar, si la respuesta trae conflictos, MUST mostrarse "Estos turnos quedaron fuera del nuevo horario. Recepción debe reprogramarlos o cancelarlos." con la fecha y hora local de cada turno (RN-GL-01); sin conflictos, "Horario guardado".

#### Scenario: Guardar dos tramos el lunes (esperado)
- **WHEN** el administrador carga lunes 09:00–13:00 y 14:00–18:00 y guarda
- **THEN** se envía la semana completa y la pantalla muestra "Horario guardado" con los dos tramos

#### Scenario: Tramos superpuestos (error de negocio)
- **WHEN** la API responde 400 `INVALID_WORKING_HOURS` por superposición del lunes
- **THEN** la pantalla muestra el mensaje junto al lunes y conserva los tramos escritos

#### Scenario: Turnos en conflicto tras acortar (esperado)
- **WHEN** la respuesta del guardado trae un conflicto del lunes 5 de octubre a las 16:00 hora local
- **THEN** la pantalla muestra el aviso de conflictos con "lun 05/10 16:00"

### Requirement: Licencias en pantalla

La pantalla SHALL listar las licencias del profesional con fechas `DD/MM/AAAA` y motivo (o "Sin motivo"). El administrador MUST poder agregar una licencia con fecha de inicio, fecha de fin y motivo opcional, y borrar una licencia previa confirmación ("¿Borrar esta licencia?"). Una fecha de fin anterior al inicio MUST mostrar "La fecha de fin no puede ser anterior a la de inicio" sin llamar a la API. Tras agregar, los conflictos MUST mostrarse con el mismo aviso que el horario.

#### Scenario: Agregar una licencia sin conflictos (esperado)
- **WHEN** el administrador agrega una licencia del 12/10/2026 al 16/10/2026 con motivo "Congreso"
- **THEN** la licencia aparece en el listado con ese motivo

#### Scenario: Fechas invertidas (error)
- **WHEN** el administrador pone inicio 16/10/2026 y fin 12/10/2026
- **THEN** ve "La fecha de fin no puede ser anterior a la de inicio" y no se envía ningún pedido

#### Scenario: Cancelar el borrado (borde)
- **WHEN** el administrador pulsa "Borrar" en una licencia y responde que no a la confirmación
- **THEN** no se envía ningún pedido y la licencia sigue en el listado
