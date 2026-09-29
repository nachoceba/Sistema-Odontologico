# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|---|---|---|
| Administrador/dueño | Responsable del consultorio | Usa la app; gestiona usuarios, profesionales y horarios |
| Recepcionista | Atiende teléfono y mostrador | Usa la app; agenda turnos y gestiona pacientes |
| Odontólogo/a | Profesional que atiende | Usa la app; consulta su agenda y marca el estado de sus turnos |
| Paciente | Persona atendida | No inicia sesión; recibe emails |
| Sistema (cron) | Job programado | Llama a `/api/cron/reminders` con secreto |

## RBAC — Matriz de permisos

C = crear, R = leer, U = actualizar, D = eliminar. "propio" = solo registros del profesional asociado al usuario.

| Recurso | Administrador | Recepción | Odontólogo/a |
|---|---|---|---|
| Usuarios / roles | CRUD | — | — |
| Profesionales | CRUD | R | R (propio) |
| Horarios y licencias | CRUD | R | R (propio) |
| Pacientes | CRUD* | CRU | R |
| Turnos | CRUD* | CRU (cancelar = estado) | R propio; U estado propio (atendido / ausente) |
| Configuración (slot) | RU | — | — |
| Recordatorios enviados | R | R | — |

\* Los pacientes y turnos no se eliminan físicamente en el uso normal: se cancelan o se desactivan (RN-TU-05, RN-PA-03). El borrado físico es solo para el administrador.

Quién edita los horarios de los profesionales es una decisión abierta (ver `10_preguntas_abiertas.md`); esta matriz asume que solo el administrador.

## Rutas públicas

- `/login`
- Ninguna otra: la app completa requiere sesión. Los pacientes no tienen acceso.
