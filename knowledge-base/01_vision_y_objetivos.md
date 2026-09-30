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

## Contexto de mercado (informe de Discovery)

El informe `docs/discovery/informe-discovery.md` relevó 19 sistemas de gestión odontológica (fecha de consulta 2026-09-30).

- **Competidores principales:** ClinIA, Livio, iAsistemas, Bilog, DrApp y Dentalink. Entre los que publican precio, van desde ARS 32.800 por profesional al mes (DrApp) hasta ARS 222.999 (plan de hasta 10 profesionales de iAsistemas); Livio cobra ARS 99.000.
- **Estándar de mercado:** agenda multi-profesional en la nube, recordatorios por WhatsApp, odontograma, historia clínica y presupuestos.
- **Vacíos relevantes (no evidenciados en los sistemas argentinos):** sobreturnos, lista de espera con oferta de huecos, exportación de datos, agenda por sillón con duración por prestación y reactivación de pacientes.
- **Oportunidad del proyecto:** precio cero y entrada simple para consultorios chicos, con agenda sin superposiciones garantizada por la base.
- **Límite:** toda la evidencia es documental y sale de las páginas de cada proveedor; no se probó ninguna demo.

Cómo se aparta este proyecto del MVP recomendado: ver DD-07, DD-08 y DD-09.

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
