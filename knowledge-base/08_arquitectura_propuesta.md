# Arquitectura Propuesta

Prioridad de calidad definida: **mantenibilidad**. La arquitectura busca reglas de negocio aisladas y testeables, con la infraestructura reemplazable.

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| Capas (domain / application / infrastructure) | Todo el código de negocio | Aísla las reglas de Next.js y Supabase |
| Funciones puras de dominio | Cálculo de slots, validación de superposición y horarios | Testeables con Vitest sin base ni red |
| Repository | Acceso a Supabase | Permite tests con repos en memoria |
| Casos de uso (application services) | `agendarTurno`, `cancelarTurno`, `reprogramarTurno`, `enviarRecordatorios` | Un lugar por operación de negocio |
| Constraint de exclusión en BD | Tabla `appointments` | Garantiza la no superposición aun con concurrencia |
| Idempotencia por unique key | `email_notifications (appointment_id, kind)` | El cron puede reintentarse sin duplicar emails |

## Estructura de directorios

```
sistema-odontologico/
├── src/
│   ├── app/                    # rutas Next.js (UI, Server Actions, /api/cron)
│   │   ├── (auth)/login/
│   │   ├── agenda/
│   │   ├── pacientes/
│   │   ├── profesionales/
│   │   └── api/cron/reminders/
│   ├── domain/                 # reglas puras, sin imports de framework
│   │   ├── appointments/       # slots, superposición, validaciones
│   │   ├── schedules/          # working_hours, time_off
│   │   └── patients/
│   ├── application/            # casos de uso
│   ├── infrastructure/
│   │   ├── supabase/           # clientes y repositorios
│   │   └── email/              # cliente Resend y plantillas
│   └── shared/                 # tipos, fecha/zona horaria, errores
├── supabase/
│   ├── migrations/             # SQL versionado (tablas, constraints, RLS)
│   └── seed.sql                # datos ficticios
├── tests/                      # unit (domain) + integración
└── knowledge-base/
```

## Seguridad

- **Autenticación**: Supabase Auth, sesión por cookie gestionada en servidor.
- **Autorización**: chequeo de rol en cada caso de uso (application) más RLS por rol en Postgres como defensa en profundidad.
- **Validación de input**: esquemas (por ejemplo Zod) en el borde de cada Server Action y Route Handler.
- **Secrets management**: variables de entorno en Vercel; `SUPABASE_SERVICE_ROLE_KEY` y `RESEND_API_KEY` solo en servidor. El endpoint del cron exige `CRON_SECRET`.
- **Datos de pacientes**: ficticios; aun así se aplica mínimo privilegio (RN-PR-02).

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL del proyecto Supabase | `https://xxxx.supabase.co` | N |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clave pública anónima | `eyJ...` | N |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave de servicio (solo servidor) | `eyJ...` | Y |
| `RESEND_API_KEY` | API key de Resend | `re_...` | Y |
| `EMAIL_FROM` | Remitente de los emails | `turnos@ejemplo.com` | N |
| `CRON_SECRET` | Secreto del endpoint de recordatorios | cadena aleatoria larga | Y |
| `CLINIC_TIMEZONE` | Zona horaria por defecto | `America/Argentina/Buenos_Aires` | N |
