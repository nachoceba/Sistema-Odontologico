# Discovery — Sistema Odontológico

**Fecha**: 2026-09-29
**Fuentes investigadas**: ninguna (Discovery por Q&A pura, sin scraping de competidores)

## 1. Problema que resuelve

Los turnos de un consultorio odontológico se gestionan hoy con planillas y
WhatsApp: hay superposiciones, ausencias sin aviso y no hay una agenda
centralizada por profesional.

## 2. Usuarios / roles

- **Odontólogo/a**: consulta su agenda y sus horarios de atención.
- **Recepcionista/secretaria**: agenda, cancela y reprograma turnos; gestiona pacientes.
- **Administrador/dueño**: gestiona usuarios y los horarios de los profesionales.
- **Paciente**: recibe recordatorios de sus turnos por email (en v1 no inicia sesión).

## 3. Casos de uso

1. Como recepcionista, quiero agendar y gestionar turnos por profesional para
   evitar superposiciones (caso principal, bloquea el MVP).
2. Como recepcionista, quiero dar de alta y modificar pacientes para asociarlos a un turno.
3. Como odontólogo/a, quiero ver mi agenda para saber qué pacientes atiendo y cuándo.
4. Como paciente, quiero recibir un recordatorio por email para no olvidar mi turno.

## 4. Competidores / soluciones existentes

| Solución actual | Problema que resuelve | Pricing | Diferenciadores |
|---|---|---|---|
| Planillas (Excel/Sheets) | Listado manual de turnos | Gratis | Flexibles, pero sin validación de superposiciones |
| WhatsApp | Coordinación y confirmación con el paciente | Gratis | Canal ya adoptado por los pacientes, pero manual y desordenado |

**Notas**: no se investigaron sistemas odontológicos comerciales; queda como
tarea opcional si se quiere posicionar el producto.

## 5. Funcionalidades necesarias

- ABM de pacientes.
- Agenda por profesional (alta, cancelación y reprogramación de turnos).
- Recordatorios de turno por email automático.
- Login con roles (odontólogo, recepción, administrador).

## 6. Funcionalidades opcionales

- Historia clínica y odontograma.
- Presupuestos y cobros.
- Turnos online para pacientes.
- Reportes y estadísticas (ausentismo, ocupación).
- Sincronización con Google Calendar.

## 7. Reglas de negocio

- Cada profesional tiene sus propios horarios de atención (días, horarios y licencias).
- Un profesional no puede tener dos turnos superpuestos.

## 8. Integraciones

- Servicio de email gratuito para recordatorios de turno (v1).
- Google Calendar: opcional, post-v1.

## 9. Restricciones

- Todo gratuito: hosting, email y base de datos.
- Datos de pacientes ficticios.
- Entrega dentro del plazo de la cursada.

## 10. Riesgos

- **Riesgo**: la recepcionista no adopta el sistema y sigue con planilla/WhatsApp.
- **Riesgo**: conflictos de agenda por licencias y cambios de último momento.
- **Riesgo**: privacidad de datos de pacientes, aun siendo ficticios.
- **Supuesto sin probar**: los límites del email gratuito alcanzan para los recordatorios de v1.

## 11. Preguntas abiertas

- ¿Cuánto antes se envía el recordatorio y el paciente puede confirmar o cancelar?
- ¿La duración de un turno es fija o depende del tipo de tratamiento?
- ¿Un paciente puede tener varios turnos el mismo día?
- ¿Quién define y edita los horarios de los profesionales?
- ¿El paciente tiene login en v1 o solo recibe emails?
- ¿Cuál es el stack y el hosting gratuito?
