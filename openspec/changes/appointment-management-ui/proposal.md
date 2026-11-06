# Proposal: appointment-management-ui (C-10)

> **Gobernanza MEDIA** (pantalla de gestión de turnos sobre los casos de uso de C-08, `CHANGES.md`). Las decisiones de dominio y de pantalla P-1 a P-9 de `design.md` están **CONFIRMADAS** por la usuaria con la opción recomendada en todas (DD-84 a DD-86).

## Why

La agenda `/agenda` de C-09 ya muestra por día y por semana las franjas libres, ocupadas y fuera de horario, los turnos con su estado y los turnos en conflicto, pero es de solo lectura (DD-83). Recepción todavía no puede agendar, cancelar ni reprogramar desde la pantalla, y nadie puede marcar atendido o ausente: todo eso existe solo en la API de C-08. Sin estas acciones el sistema no reemplaza la planilla y el WhatsApp de recepción (riesgo de adopción, `01_vision_y_objetivos.md`), y los conflictos que deja un cambio de horario o una licencia (RN-HO-04, Flujo 5) se ven pero no se pueden resolver.

## What Changes

- **Agendar desde una franja libre** (US-007, Flujo 2): en la vista "Día" y en la "Semana", cada franja "Libre" que todavía no empezó ofrece "Agendar" a administración y recepción (P-1). Se abre un panel con el día, la hora y el profesional, el buscador de pacientes activos de C-06 (`PatientSearch`) con el aviso de los acentos (DD-74, P-6) y "Nuevo paciente" con el formulario de C-06 (`PatientForm`), que deja al paciente creado ya elegido (DD-78). "Agendar turno" envía `POST /api/v1/appointments`.
- **Detalle del turno**: al elegir un turno de la grilla se abre un panel con la hora, el paciente, el estado, el motivo de cancelación y el aviso de conflicto, y solo las acciones que ese rol puede hacer sobre ese turno en ese momento (P-5).
- **Cancelar con motivo** (US-008, Flujo 3, DD-65): diálogo con motivo obligatorio de 1 a 500 caracteres (P-2); la franja vuelve a "Libre" y el turno se ve tachado.
- **Reprogramar** (US-009, Flujo 3, DD-64): diálogo con una fecha y las franjas libres de ese día del mismo profesional (P-3); confirmar muestra el horario anterior y el nuevo. Si se rechaza, el turno no cambia (RN-TU-06).
- **Marcar atendido o ausente** (US-010, DD-22, DD-23, DD-64): en turnos agendados que ya empezaron, para el odontólogo (solo los suyos) y para recepción y administración, con confirmación porque no se puede corregir (P-4).
- **Mensajes de error claros** para cada código de C-08 (slot ocupado, fuera de horario, sin anticipación o en el pasado, licencia, paciente o profesional inactivo, doble turno del paciente, turno ya iniciado, etc.), sin datos de otros pacientes; tras un rechazo que indica que la agenda cambió, la grilla se vuelve a pedir (P-7).
- **Indicador de turnos en conflicto** (RN-HO-04, DD-68): para administración y recepción, un aviso "N turnos en conflicto" con la lista de todos los turnos futuros en conflicto del profesional (fecha, hora, paciente y motivo) y acceso directo a "Reprogramar" y "Cancelar" de cada uno, usando `GET /api/v1/professionals/{id}/conflicts` de C-07 (P-8).
- **La agenda deja de ser de solo lectura**: se reemplaza el requirement "Solo lectura" de `frontend-agenda` por las reglas de qué pedidos de escritura puede enviar la pantalla y cuándo se actualiza.
- **Sin cambios en el backend**: se usan los siete endpoints de turnos de `appointment-api` y el de conflictos tal como están, con sus permisos (DD-48, DD-53, DD-64). Sin endpoints, migraciones, variables de entorno ni dependencias nuevas. Regla dura 6: la no superposición la siguen garantizando el dominio y el constraint; la pantalla solo traduce los rechazos.

## Capabilities

### New Capabilities
- `frontend-appointment-management`: acciones sobre la agenda (agendar desde una franja libre con buscar o crear paciente, detalle del turno, cancelar con motivo, reprogramar, marcar atención), qué acción ve cada rol según el estado y la hora del turno, mensajes por código de error, actualización tras cada acción e indicador de conflictos con acceso a resolverlos.

### Modified Capabilities
- `frontend-agenda`: la pantalla deja de ser de solo lectura (se reemplaza "Solo lectura" por "Pedidos y actualización de la agenda") y los turnos en conflicto pasan a tener acceso a resolverlos (se modifica "Licencias y turnos en conflicto"); el propósito se actualiza.

## Impact

- **Frontend**: `frontend/src/api/appointments.ts` (suma `bookAppointment`, `cancelAppointment`, `rescheduleAppointment`, `recordAttendance`, `getAppointment`), carpeta nueva `frontend/src/appointments/` (reglas puras de qué acción está disponible, mensajes por código, paneles y diálogos de agendar, detalle, cancelar, reprogramar y marcar, panel de conflictos), `frontend/src/agenda/DayColumn.tsx` y `WeekView.tsx` (acciones opcionales sobre franjas libres y turnos), `frontend/src/agenda/useAgendaData.ts` (conflictos expuestos a la página), `frontend/src/pages/AgendaPage.tsx`, estilos en `styles.css`. Reusa sin cambios `patients/PatientSearch.tsx`, `patients/PatientForm.tsx`, `patients/ConfirmDialog.tsx` y `api/professionals.ts`.
- **Backend**: sin cambios. La suite de C-08 corre como red de seguridad (regla dura 6).
- **Tests**: Vitest para las reglas puras, el cliente de escritura, cada panel y diálogo con `fetch` simulado, y los flujos de la página: agendar, choque de slot, cancelar libera la franja, reprogramar, marcar atención y resolver un conflicto.
- **Consumidores**: C-11 (confirmación por email al agendar o reprogramar) no cambia la pantalla: hasta C-11 el aviso de éxito no menciona emails. C-12 sigue con el listado de todos los profesionales (DD-66).
