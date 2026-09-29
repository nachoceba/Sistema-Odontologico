# Funcionalidades

Organizadas por **épica** y luego por **historia de usuario** (formato US-NNN).

## Épica 1: Acceso y roles

### US-001 — Iniciar sesión
**Como** usuario del consultorio
**Quiero** iniciar sesión con email y contraseña
**Para** acceder solo a lo que mi rol permite

**Criterios de aceptación**:
- [ ] Credenciales inválidas muestran un error genérico.
- [ ] Un usuario inactivo no puede entrar.
- [ ] Tras el login, cada rol ve su pantalla de inicio (agenda).

**Reglas relacionadas**: RN-AU-01, RN-AU-02, RN-AU-03

### US-002 — Gestionar usuarios
**Como** administrador
**Quiero** crear usuarios y asignarles rol
**Para** dar acceso a recepción y odontólogos

**Criterios de aceptación**:
- [ ] Crear, editar y desactivar usuarios.
- [ ] Al crear un usuario `dentist` se crea su profesional asociado.

**Reglas relacionadas**: RN-AU-02, RN-AU-03

## Épica 2: Pacientes

### US-003 — ABM de pacientes
**Como** recepcionista
**Quiero** dar de alta, buscar, editar y desactivar pacientes
**Para** asociarlos a turnos

**Criterios de aceptación**:
- [ ] Alta con nombre, apellido, documento y email obligatorios.
- [ ] No se puede repetir el documento.
- [ ] Búsqueda por apellido y por documento.
- [ ] Un paciente con turnos se desactiva, no se borra.

**Reglas relacionadas**: RN-PA-01, RN-PA-02, RN-PA-03, RN-PA-04

## Épica 3: Profesionales y horarios

### US-004 — Definir horarios de atención
**Como** administrador
**Quiero** cargar los días y horarios de cada profesional
**Para** que la agenda ofrezca solo slots válidos

**Criterios de aceptación**:
- [ ] Varios tramos por día, sin superposición entre ellos.
- [ ] Cambios reflejados de inmediato en la disponibilidad.
- [ ] Si un cambio afecta turnos existentes, se listan para revisión.

**Reglas relacionadas**: RN-HO-01, RN-HO-02, RN-HO-04

### US-005 — Cargar licencias
**Como** administrador
**Quiero** registrar rangos de licencia de un profesional
**Para** bloquear turnos en esos días

**Criterios de aceptación**:
- [ ] Rango de fechas con motivo opcional.
- [ ] Los días de licencia no ofrecen slots.

**Reglas relacionadas**: RN-HO-03, RN-HO-04

## Épica 4: Agenda de turnos (MVP)

### US-006 — Ver agenda por profesional
**Como** recepcionista u odontólogo
**Quiero** ver la agenda diaria y semanal de un profesional
**Para** saber qué slots están libres y cuáles ocupados

**Criterios de aceptación**:
- [ ] Vista por día y por semana.
- [ ] Slots libres, ocupados y fuera de horario diferenciados.
- [ ] El odontólogo solo ve su propia agenda.

**Reglas relacionadas**: RN-AU-04, RN-TU-02, RN-TU-03

### US-007 — Agendar un turno
**Como** recepcionista
**Quiero** elegir paciente, profesional y slot libre
**Para** registrar el turno sin superposiciones

**Criterios de aceptación**:
- [ ] Solo se puede elegir un slot libre y dentro del horario.
- [ ] Dos recepcionistas agendando el mismo slot: uno recibe error claro.
- [ ] Al guardar se envía el email de confirmación.
- [ ] No se permite un inicio en el pasado.

**Reglas relacionadas**: RN-TU-01, RN-TU-02, RN-TU-03, RN-TU-04, RN-NO-01

### US-008 — Cancelar un turno
**Como** recepcionista
**Quiero** cancelar un turno indicando un motivo
**Para** liberar el slot

**Criterios de aceptación**:
- [ ] El turno queda `cancelled` y el slot vuelve a estar libre.
- [ ] No se envían recordatorios de turnos cancelados.

**Reglas relacionadas**: RN-TU-05, RN-NO-05

### US-009 — Reprogramar un turno
**Como** recepcionista
**Quiero** mover un turno a otro slot
**Para** atender un cambio pedido por el paciente

**Criterios de aceptación**:
- [ ] Aplica todas las validaciones de agendar.
- [ ] Si falla, el turno original no cambia.
- [ ] Se genera un nuevo recordatorio para la nueva fecha.

**Reglas relacionadas**: RN-TU-06, RN-NO-05

### US-010 — Marcar atención
**Como** odontólogo
**Quiero** marcar un turno como atendido o ausente
**Para** mantener el estado real de la agenda

**Criterios de aceptación**:
- [ ] Solo turnos propios, `scheduled` y ya iniciados.

**Reglas relacionadas**: RN-TU-07, RN-AU-04

## Épica 5: Recordatorios por email

### US-011 — Enviar recordatorio previo
**Como** paciente
**Quiero** recibir un email antes de mi turno
**Para** no olvidarlo

**Criterios de aceptación**:
- [ ] El job diario envía el recordatorio de los turnos `scheduled` del día siguiente.
- [ ] No se envía dos veces el mismo recordatorio.
- [ ] Un fallo queda registrado y no rompe el resto del lote.

**Reglas relacionadas**: RN-NO-02, RN-NO-03, RN-NO-04

## Backlog posterior a v1

Historia clínica y odontograma, presupuestos y cobros, turnos online para pacientes, reportes, confirmar/cancelar desde el email y Google Calendar.
