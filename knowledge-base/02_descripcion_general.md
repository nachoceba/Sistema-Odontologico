# Descripción General

## Stack tecnológico

| Capa | Tecnología | Nota |
|---|---|---|
| Frontend + Backend | Next.js (App Router) + TypeScript | Un solo repo; Server Actions y Route Handlers |
| Base de datos | PostgreSQL (Supabase, tier gratuito) | Constraint de exclusión para superposición |
| Autenticación | Supabase Auth | Email + contraseña; rol en `profiles` |
| Autorización de datos | RLS de Supabase (defensa en profundidad) + chequeo de rol en la capa de aplicación | Ver DD-02 |
| Email | Resend (tier gratuito) | Ver SU-02 sobre restricciones del plan gratuito |
| Tareas programadas | Vercel Cron o pg_cron de Supabase | Ver SU-03 |
| Hosting | Vercel (tier gratuito) | Todo el stack en planes gratuitos |
| Tests | Vitest | Foco en la capa de dominio |

**Restricción**: todo gratuito, con datos de pacientes ficticios.

## Arquitectura general

```
Navegador (recepción / odontólogo / admin)
        │  HTTPS
        ▼
Next.js en Vercel
  ├─ app/            UI + Server Actions + Route Handlers
  ├─ application/    casos de uso (agendar, cancelar, reprogramar...)
  ├─ domain/         reglas puras: disponibilidad, superposición, slots
  └─ infrastructure/ repositorios Supabase, cliente Resend
        │                         │
        ▼                         ▼
Supabase (Postgres + Auth)      Resend (email)
        ▲
        │
Cron diario ──► /api/cron/reminders (protegido con CRON_SECRET)
```

Decisión de fondo: las reglas de negocio viven en `domain/` como funciones puras y testeables. La base de datos las refuerza con constraints, pero no es la única que las conoce.

## Integraciones externas

| Servicio | Propósito | Tipo |
|---|---|---|
| Supabase | Base de datos y autenticación | SDK / SQL |
| Resend | Envío de emails de confirmación y recordatorio | REST / SDK |
| Vercel Cron (o pg_cron) | Disparar el job de recordatorios | HTTP programado |

Google Calendar queda como integración opcional posterior a v1.

## API

No hay una API pública separada. Las operaciones de la UI usan Server Actions. Los únicos Route Handlers son:

| Ruta | Método | Descripción |
|---|---|---|
| `/api/cron/reminders` | GET/POST | Envía los recordatorios pendientes; exige `Authorization: Bearer $CRON_SECRET` |
