# Spec Delta: appointment-api

## MODIFIED Requirements

### Requirement: Endpoints de turnos

La API SHALL ofrecer, todos bajo `/api/v1` y con JWT obligatorio:

| Método y ruta | Uso | Respuesta correcta |
|---|---|---|
| `POST /appointments` (paciente, profesional, inicio) | Agendar | 201 con el turno |
| `GET /appointments/{id}` | Detalle | 200 con el turno y el nombre del paciente |
| `GET /appointments?professional_id=…&from=…&to=…` | Turnos de un profesional en `[from, to)` | 200 con la lista, cada turno con el nombre del paciente |
| `POST /appointments/{id}/cancel` (motivo) | Cancelar | 200 con el turno |
| `POST /appointments/{id}/reschedule` (nuevo inicio) | Reprogramar | 200 con el turno |
| `POST /appointments/{id}/attendance` (`completed` o `no_show`) | Marcar atención | 200 con el turno |
| `GET /professionals/{professional_id}/slots?date=AAAA-MM-DD` | Franjas de un día local | 200 con la lista |

Un turno en la respuesta MUST contener identificador, paciente, profesional, inicio, fin, estado, motivo de cancelación (o nulo) y creador. En el detalle y en el listado cada turno MUST contener además `patient_first_name` y `patient_last_name` con los datos vigentes del paciente (P-1 de C-09, CONFIRMADA (2026-11-04)); las respuestas de agendar, cancelar, reprogramar y marcar atención MUST seguir con la forma anterior. Ninguna respuesta de turnos MUST incluir email, teléfono, documento ni fecha de nacimiento del paciente. No existe endpoint de borrado de turnos (RN-TU-05, DD-39).

#### Scenario: Agendar devuelve el turno creado (esperado)
- **WHEN** recepción envía `POST /api/v1/appointments` con un paciente activo, la Dra. A y un inicio libre válido
- **THEN** la respuesta es 201 con el turno en estado `scheduled`, su identificador y su fin calculado

#### Scenario: Borrar no existe (borde)
- **WHEN** el administrador envía `DELETE /api/v1/appointments/{id}`
- **THEN** la respuesta es 405 y el turno no cambia

#### Scenario: Turno inexistente (error de negocio)
- **WHEN** se pide `GET /api/v1/appointments/{id}` con un identificador que no existe
- **THEN** la respuesta es 404 con `error.code = "APPOINTMENT_NOT_FOUND"`

#### Scenario: Listado con nombre del paciente (esperado)
- **WHEN** recepción pide `GET /api/v1/appointments?professional_id={Dra. A}&from=2026-11-09T00:00:00-03:00&to=2026-11-16T00:00:00-03:00` y Juan Perez tiene un turno ese martes
- **THEN** la respuesta es 200 y ese turno trae `patient_id`, `patient_first_name = "Juan"` y `patient_last_name = "Perez"`, sin `email`, `phone`, `document_number` ni `birth_date`

#### Scenario: Detalle con nombre del paciente (esperado)
- **WHEN** la Dra. A pide `GET /api/v1/appointments/{id}` de un turno suyo
- **THEN** la respuesta es 200 con `patient_first_name` y `patient_last_name`

#### Scenario: Odontóloga pide la agenda ajena (error de negocio)
- **WHEN** la Dra. A pide el listado del Dr. B
- **THEN** la respuesta es 403 `FORBIDDEN` y el cuerpo no contiene ningún nombre de paciente

#### Scenario: Agendar no cambia de forma (borde)
- **WHEN** recepción agenda un turno válido
- **THEN** la respuesta 201 tiene los mismos campos que antes de este change
