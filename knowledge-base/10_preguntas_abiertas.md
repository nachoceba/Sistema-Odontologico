# Preguntas Abiertas

## Inconsistencias detectadas

### IN-01 — Recordatorio "24 h antes" vs cron gratuito
**Discovery dice**: recordatorio 24 h antes del turno, con todo el stack gratuito.
**Restricción dice**: el cron gratuito puede limitarse a una ejecución diaria.
**Impacto**: el aviso saldría "el día anterior" y no exactamente 24 h antes.
**Resolución propuesta**: aceptar el envío diario para v1 (DD-06, SU-03) y validar límites reales antes de construir.

### IN-02 — Email en v1 vs integraciones "ninguna en v1"
**Discovery dice**: en un primer momento "ninguna integración en v1"; luego el email automático pasó a v1.
**Impacto**: Resend y el job programado entran al alcance de v1 y a la estimación.
**Resolución propuesta**: tratarlo como parte de v1 (ya reflejado en `01_vision_y_objetivos.md`).

## Preguntas abiertas (priorizadas)

| Prioridad | Pregunta | Bloquea | Decisor |
|-----------|----------|---------|---------|
| Alta | ¿Qué límites tiene hoy el plan gratuito de Resend sin dominio propio? (SU-02) | Recordatorios | Equipo técnico |
| Alta | ¿Vercel Cron o pg_cron permiten la frecuencia necesaria? (SU-03) | Recordatorios | Equipo técnico |
| Alta | ¿Quién define y edita los horarios de los profesionales? (SU-06) | Matriz RBAC, US-004 | Dueño / Product Owner |
| Media | Si cambia un horario y hay turnos afectados, ¿se avisa al paciente o solo a recepción? (RN-HO-04) | US-004 | Product Owner |
| Media | ¿Un paciente puede tener varios turnos el mismo día? (SU-05) | Validación de turnos | Product Owner |
| Media | ¿El recordatorio debe incluir dirección, teléfono u otra información del consultorio? | Plantilla de email | Dueño |
| Media | ¿Cuál es la zona horaria del consultorio? (SU-01) | Fechas y cron | Dueño |
| Baja | ¿Qué duración de slot usa el consultorio realmente: 15, 20, 30 min? | Configuración | Dueño |
| Baja | ¿Se necesita registrar quién canceló y por qué en más detalle? | Auditoría | Product Owner |
| Media | Sobreturnos: el informe no los evidencia en ningún sistema. ¿Los necesita el consultorio real? (RN-TU-11) | Regla de agenda | Dueño |
| Media | Sillones o boxes: no evidenciado como control de conflictos entre profesionales en los sistemas argentinos. ¿El consultorio tiene sillones compartidos? (RN-TU-09) | Modelo de agenda | Dueño |
| Media | Duración por prestación: ¿qué tratamientos necesitan más de un slot y con qué frecuencia? (RN-TU-10) | Modelo de agenda | Dueño |
| Media | Lista de espera con oferta de huecos liberados: solo evidenciada en Dentally (Reino Unido). ¿Se prioriza tras v1? | Backlog | Product Owner |
| Media | Exportación de datos: no evidenciada en ningún competidor. ¿Se ofrece como promesa de portabilidad? | Backlog | Product Owner |
| Media | Recordatorios por WhatsApp: estándar en el mercado pero incompatible con costo cero. ¿Alcanza el email o se suma un enlace `wa.me` manual? (DD-09) | Estrategia de recordatorios | Product Owner |
| Baja | Mercado Pago y seña atada al turno: evidenciado en DrApp y en sistemas genéricos, no en los odontológicos. ¿Se evalúa tras v1? | Backlog | Product Owner |
| Baja | Facturación ARCA y obras sociales: evidenciadas solo en algunos competidores (ClinIA, iAsistemas, DrApp, Bilog, Dentalink). ¿Son decisivas para el consultorio? | Backlog | Dueño |
| Baja | Precio de Dentalink (USD 29 según un tercero, sin respaldo del sitio oficial): no verificado. | Contexto de mercado | Equipo |
| Baja | Normativa: Ley 25.326 y Ley 27.706 no fueron contrastadas con su texto. ¿Hace falta revisión legal si el proyecto pasara a datos reales? | Cumplimiento | Dueño |
| Baja | Adopción: ¿cómo se hace que recepción abandone planilla y WhatsApp? | Éxito del proyecto | Dueño |
