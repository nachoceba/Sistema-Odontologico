# Visión y Objetivos

## Propósito del sistema

Sistema web para gestionar los turnos de un consultorio odontológico: agenda por profesional sin superposiciones, ABM de pacientes y recordatorios automáticos por email.

Hoy los turnos se coordinan con planillas y WhatsApp, lo que produce superposiciones, ausencias sin aviso y ninguna agenda centralizada. El sistema reemplaza ese circuito por una única fuente de verdad.

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| Recepcionista | Agendar, cancelar y reprogramar turnos sin superposiciones | Alta y edición rápida de pacientes |
| Odontólogo/a | Ver su agenda del día y de la semana | Marcar turnos como atendidos o ausentes |
| Administrador/dueño | Definir los horarios de los profesionales y gestionar usuarios | Supervisar la ocupación de la agenda |
| Paciente | Recibir confirmación y recordatorio por email | (No inicia sesión en v1) |

## Alcance v1.0

- Login con roles (administrador, recepción, odontólogo).
- ABM de pacientes.
- Gestión de profesionales y de sus horarios de atención y licencias.
- Agenda por profesional con alta, cancelación y reprogramación de turnos en slots fijos.
- Validación de no superposición y de horarios de atención.
- Email al agendar y recordatorio previo al turno.

## Fuera de alcance

- Historia clínica y odontograma.
- Presupuestos, cobros y caja.
- Turnos online y login para pacientes.
- Confirmación o cancelación del turno desde el email.
- Reportes y estadísticas.
- Sincronización con Google Calendar.
- Multi-consultorio / multi-tenant.
- Turnos de duración variable por tipo de tratamiento.

## Métricas de éxito

- Cero turnos superpuestos para un mismo profesional (garantizado por constraint en la base).
- La recepcionista agenda un turno en menos de 1 minuto.
- Los recordatorios salen para el 100 % de los turnos activos del día siguiente.
- La recepción deja de usar la planilla y WhatsApp para agendar (riesgo de adopción, ver `10_preguntas_abiertas.md`).
