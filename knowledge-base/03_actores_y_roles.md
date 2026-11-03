# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|---|---|---|
| Administrador/dueño | Responsable del consultorio | Usa la app; gestiona usuarios, profesionales y horarios |
| Recepcionista | Atiende teléfono y mostrador | Usa la app; agenda turnos y gestiona pacientes |
| Odontólogo/a | Profesional que atiende | Usa la app; consulta su agenda y marca el estado de sus turnos |
| Paciente | Persona atendida | No inicia sesión; recibe emails |
| Sistema (tarea programada) | Celery Beat | Dispara cada día el envío de recordatorios; no expone ninguna ruta HTTP |

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

Matriz confirmada por el usuario el 2026-11-03 (C-03, DD-48): solo el administrador edita horarios y licencias (SU-06 resuelto). Un odontólogo sin ficha de profesional puede iniciar sesión pero no accede a datos de ningún profesional (DD-53).

## Rutas públicas

- Pantalla `/login` del frontend y `POST /api/v1/auth/login` en la API.
- Ninguna otra: toda pantalla y todo endpoint requieren sesión (JWT válido). Los pacientes no tienen acceso.
