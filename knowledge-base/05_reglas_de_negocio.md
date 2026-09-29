# Reglas de Negocio

Cada regla tiene un código único `RN-{DOMINIO}-{NN}` para trazabilidad.

## Dominio: Autenticación y acceso (RN-AU)
- **RN-AU-01**: Toda ruta salvo `/login` requiere sesión válida.
- **RN-AU-02**: Cada usuario tiene exactamente un rol (`admin`, `receptionist`, `dentist`) y los permisos salen de `03_actores_y_roles.md`.
- **RN-AU-03**: Un usuario con `active = false` no puede iniciar sesión.
- **RN-AU-04**: Un odontólogo solo ve sus propios turnos y horarios.

## Dominio: Pacientes (RN-PA)
- **RN-PA-01**: `document_number` es único entre pacientes.
- **RN-PA-02**: El `email` es obligatorio porque es el canal de recordatorio.
- **RN-PA-03**: Un paciente con turnos asociados no se elimina; se desactiva (`active = false`).
- **RN-PA-04**: Un paciente inactivo no puede recibir turnos nuevos.

## Dominio: Horarios de profesionales (RN-HO)
- **RN-HO-01**: Cada profesional tiene sus propios horarios de atención por día de la semana.
- **RN-HO-02**: Los tramos horarios de un mismo día no se superponen y `start_time < end_time`.
- **RN-HO-03**: Los días cubiertos por una licencia (`time_off`) no admiten turnos.
- **RN-HO-04**: Modificar horarios o cargar una licencia no cancela turnos existentes; el sistema los marca como conflicto para que recepción los resuelva (ver `10_preguntas_abiertas.md`).

## Dominio: Turnos (RN-TU)
- **RN-TU-01**: Un profesional no puede tener dos turnos `scheduled` superpuestos. Se valida en el dominio y se garantiza con el constraint de exclusión.
- **RN-TU-02**: La duración de un turno es siempre `slot_minutes` (30 por defecto) y el inicio cae en la grilla de slots del horario del profesional.
- **RN-TU-03**: Un turno debe quedar completo dentro de un tramo de `working_hours` del profesional y fuera de sus licencias.
- **RN-TU-04**: No se puede agendar un turno con inicio en el pasado.
- **RN-TU-05**: Cancelar un turno cambia su estado a `cancelled`, no lo borra, y libera el slot.
- **RN-TU-06**: Reprogramar aplica las mismas validaciones que agendar (RN-TU-01 a RN-TU-04) y no se ejecuta parcialmente.
- **RN-TU-07**: Solo los estados `completed` y `no_show` se marcan desde el turno ya iniciado; un turno `cancelled` no cambia de estado.
- **RN-TU-08**: Un paciente puede tener varios turnos el mismo día (suposición SU-05, a validar).

## Dominio: Notificaciones (RN-NO)
- **RN-NO-01**: Al agendar un turno se envía un email de confirmación.
- **RN-NO-02**: Antes del turno se envía un recordatorio, solo para turnos `scheduled` (detalle en `11_recordatorios_email.md`).
- **RN-NO-03**: Se envía como máximo un email por tipo y turno (constraint `UNIQUE (appointment_id, kind)`).
- **RN-NO-04**: Un fallo de envío se registra (`status = failed`) y nunca impide agendar, cancelar ni reprogramar.
- **RN-NO-05**: Un turno reprogramado genera un nuevo recordatorio para la nueva fecha; uno cancelado no genera ninguno.

## Dominio: Datos y privacidad (RN-PR)
- **RN-PR-01**: En este proyecto solo se usan datos de pacientes ficticios.
- **RN-PR-02**: Los datos de pacientes solo son accesibles a usuarios autenticados según su rol (RLS + chequeo de aplicación).
- **RN-PR-03**: Ningún secreto (service role key, API key de email) llega al navegador.

## Dominio: Excepciones globales
- **RN-GL-01**: Todas las fechas se guardan en UTC (`timestamptz`) y se muestran en la zona horaria del consultorio (`clinic_settings.timezone`).
