# Proposal: agenda-views (C-09)

> **Gobernanza BAJA** (vistas de agenda de solo lectura sobre datos de C-07 y C-08, `CHANGES.md`). Las decisiones de dominio P-1 a P-11 de `design.md` fueron **CONFIRMADAS por la usuaria el 2026-11-04** (todas la opción recomendada) y quedaron como DD-79 a DD-83.

## Why

Después de iniciar sesión los tres roles caen en `/agenda`, que hoy es una página provisoria con el nombre y el rol (DD-51). La recepción y los odontólogos todavía no pueden **ver** la agenda de un profesional por día ni por semana, ni distinguir franjas libres, ocupadas y fuera de horario (US-006). El backend ya tiene casi todo lo necesario (turnos de un profesional por rango y franjas de un día de C-08, licencias y conflictos de C-07), pero el listado de turnos solo trae el identificador del paciente, así que la grilla no podría mostrar a quién corresponde cada turno. C-10 (agendar, cancelar, reprogramar y marcar desde la pantalla) se construye encima de esta vista.

## What Changes

- **Listado y detalle de turnos con el nombre del paciente** (P-1, opción recomendada): `GET /api/v1/appointments?professional_id&from&to` y `GET /api/v1/appointments/{id}` suman `patient_first_name` y `patient_last_name`. Es el único cambio de backend: sin endpoints nuevos, sin migraciones, sin variables de entorno, mismos permisos (DD-53) y mismo límite de 31 días. No se agregan email, teléfono ni documento.
- **Pantalla `/agenda`** que reemplaza a `AgendaPlaceholderPage`:
  - vista **día** y vista **semana** (lunes a domingo) de **un** profesional (P-2, P-6);
  - franjas **libres**, **ocupadas** y **fuera de horario** diferenciadas (US-006), en la hora del consultorio (RN-GL-01), mostrando solo la parte del día con atención (P-3);
  - los turnos con hora, apellido y nombre del paciente y su estado; cancelados, atendidos y ausentes con su etiqueta (P-4, P-7);
  - días de licencia marcados como "Licencia" y turnos agendados en conflicto con un aviso, sin botones (P-5);
  - selector de profesional para administración y recepción (activos e inactivos marcados); el odontólogo ve solo la suya y sin ficha ve un aviso (RN-AU-04, DD-53, P-8);
  - navegación anterior / siguiente / hoy y elección de fecha; profesional, fecha y vista quedan en la dirección para recargar sin perderlos;
  - botón "Actualizar"; **solo lectura**: no agenda, no cancela, no reprograma ni marca (P-9, P-10; eso es C-10);
  - barra de navegación con los enlaces que tenía la página provisoria (Pacientes, Profesionales, Usuarios para administración, Salir).
- **Funciones puras de grilla en el frontend** (`frontend/src/agenda/`): armar la columna de un día a partir de franjas y turnos, recortar fuera de horario, ubicar turnos que cruzan la medianoche, calcular "hoy" y la semana en la zona del consultorio. Reutilizables por C-10.
- Regla dura 6: la vista no escribe nada; el constraint de exclusión y las reglas de agenda no se tocan, y la suite de C-08 corre como red de seguridad.

## Capabilities

### New Capabilities
- `frontend-agenda`: pantalla `/agenda` con vistas de día y semana por profesional, estados de franjas y turnos, licencias, conflictos, filtro por rol, navegación de fechas y piezas reutilizables para C-10.

### Modified Capabilities
- `appointment-use-cases`: "Consultar turnos" devuelve además nombre y apellido del paciente de cada turno (P-1).
- `appointment-api`: el listado y el detalle de turnos incluyen `patient_first_name` y `patient_last_name` (P-1).
- `frontend-auth`: `/agenda` deja de ser una página provisoria y muestra la agenda.

## Impact

- **Backend**: `app/application/appointments.py` (consulta con datos del paciente, reusa `PatientRepository.get`), `app/api/appointments.py` (esquema de salida del listado y del detalle). Sin cambios en `domain/`, repositorios, migraciones ni configuración.
- **Frontend**: `frontend/src/api/appointments.ts` (cliente nuevo), `frontend/src/agenda/` (funciones puras y componentes de grilla, selector y navegación), `frontend/src/pages/AgendaPage.tsx` (reemplaza `AgendaPlaceholderPage.tsx`), componente de navegación compartido, `App.tsx`, estilos en `styles.css`. Reusa `api/professionals.ts` (fichas, licencias, conflictos) y `professionals/format.ts` (`CLINIC_TIMEZONE`).
- **Tests**: casos de uso en memoria, API con tabla de permisos por rol (listado y detalle), integración con el seed contra PostgreSQL, Vitest para funciones de grilla, filtro por rol, cambio de día y de semana.
- **Consumidores**: C-10 agrega acciones sobre las franjas libres y los turnos de esta grilla (y el panel de detalle); C-12 sigue siendo quien define el listado de todos los profesionales por rango (DD-66), que **no** entra acá.
