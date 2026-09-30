# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — Stack Next.js + Supabase + Resend
**Decisión**: Next.js (App Router) con Supabase (Postgres y Auth) y Resend, en Vercel.
**Contexto**: presupuesto cero, plazo de cursada y necesidad de auth con roles.
**Alternativas consideradas**: FastAPI + React + Postgres; Node/Express + React + SQLite.
**Justificación**: un solo repo, auth y Postgres listos y tiers gratuitos.
**Trade-offs aceptados**: dependencia de Supabase; límites de los planes gratuitos.

### DD-02 — Reglas en dominio, refuerzo en base de datos
**Decisión**: las reglas viven en `domain/` como funciones puras; Postgres las refuerza con constraints y RLS.
**Contexto**: la prioridad de calidad elegida es la mantenibilidad.
**Alternativas consideradas**: dejar la lógica en RLS y funciones SQL.
**Justificación**: la lógica en TypeScript se testea y evoluciona mejor que en SQL.
**Trade-offs aceptados**: hay que mantener coherentes dominio y constraints (mitigado con tests de integración).

### DD-03 — Slots fijos de duración única
**Decisión**: todos los turnos duran `slot_minutes` (30 por defecto).
**Contexto**: bloquea el modelo de datos y el algoritmo de disponibilidad.
**Alternativas consideradas**: duración por tipo de tratamiento; duración libre.
**Justificación**: menor complejidad para el MVP y sin catálogo de prestaciones.
**Trade-offs aceptados**: los tratamientos largos requieren varios turnos consecutivos.

### DD-04 — Constraint de exclusión para no superposición
**Decisión**: `EXCLUDE USING gist` sobre `(professional_id, tstzrange)` para turnos `scheduled`.
**Justificación**: es la única garantía sólida ante concurrencia entre recepcionistas.
**Trade-offs aceptados**: requiere la extensión `btree_gist`.

### DD-05 — Cancelar no borra
**Decisión**: cancelar es un cambio de estado (`cancelled`).
**Justificación**: conserva el historial y libera el slot al salir del constraint.

### DD-06 — Emails al agendar y recordatorio previo
**Decisión**: confirmación inmediata y un recordatorio antes del turno, ambos informativos.
**Alternativas consideradas**: recordatorio con confirmar/cancelar mediante token.
**Trade-offs aceptados**: el paciente no puede actuar desde el email; se consume más cuota de email.

### DD-07 — El MVP se aparta del MVP recomendado por el informe de Discovery
**Decisión**: v1 incluye pacientes, agenda por profesional, login con roles y recordatorios por email. El informe de Discovery (sección D.3) recomendaba como imprescindibles, además: agenda multi-sillón con duración por prestación, reserva online por enlace, recordatorios por WhatsApp, ficha con odontograma, exportación de datos y registro de auditoría de accesos.
**Contexto**: presupuesto cero, plazo de cursada y alcance de un único ciclo de desarrollo por change.
**Alternativas consideradas**: seguir el MVP del informe completo.
**Justificación**: el producto queda enfocado en el caso de uso principal (agendar sin superposiciones) y se puede terminar y defender. Los sistemas competidores relevados con precio publicado cobran desde ARS 32.800 por profesional al mes hasta ARS 222.999 (plan de hasta 10 profesionales); un sistema gratuito y acotado ocupa el hueco de consultorios chicos.
**Trade-offs aceptados**: v1 no alcanza la paridad de mercado en ficha clínica, reserva online ni WhatsApp. Ver `10_preguntas_abiertas.md`.

### DD-08 — Sillones o boxes y duración por prestación quedan fuera de v1
**Decisión**: se agenda por profesional con slot único (RN-TU-09, RN-TU-10).
**Contexto**: el informe marca la agenda real por sillón, con duración por prestación y sobreturnos controlados, como una oportunidad de innovación poco evidenciada en el mercado argentino.
**Justificación**: modelar sillones y prestaciones cambia el esquema, el algoritmo de disponibilidad y el roadmap. Se deja como primera mejora posterior.
**Trade-offs aceptados**: no se detectan conflictos de sillón entre profesionales.

### DD-09 — Recordatorios por email en lugar de WhatsApp
**Decisión**: v1 envía recordatorios por email (Resend) y no por WhatsApp.
**Contexto**: el informe muestra que el recordatorio por WhatsApp ya es estándar en el mercado argentino (Bilog, ClinIA, Livio, iAsistemas, DrApp, Dentalink, Dentiqa y otros). La API oficial de WhatsApp Business cobra por conversación y exige aprobación de plantillas.
**Justificación**: la restricción de costo cero descarta la API oficial.
**Trade-offs aceptados**: menor alcance que los competidores. Se evalúa un enlace `wa.me` manual como complemento posterior.

## Supuestos inferidos

### SU-01 — Zona horaria única
**Supuesto**: el consultorio opera en `America/Argentina/Buenos_Aires`.
**Origen**: contexto de la cursada y mención de normativa de datos personales; no fue confirmado.
**Riesgo si es falso**: horarios y recordatorios corridos.
**Cómo validar**: confirmar la zona con el usuario.

### SU-02 — Límite de Resend sin dominio propio
**Supuesto**: el plan gratuito sin dominio verificado solo envía a la cuenta dueña.
**Origen**: conocimiento general del servicio; no verificado.
**Riesgo si es falso o verdadero**: si es verdadero, los recordatorios solo se pueden probar hacia buzones controlados por el equipo.
**Cómo validar**: revisar la documentación vigente de Resend antes de construir.

### SU-03 — Cron gratuito y precisión del aviso
**Supuesto**: un cron diario gratuito alcanza. El recordatorio sale una vez al día para los turnos del día siguiente, no exactamente 24 h antes.
**Origen**: los planes gratuitos suelen limitar la frecuencia de cron; no verificado.
**Riesgo si es falso**: si se exige envío exacto a 24 h se necesita cron horario (pg_cron u otro).
**Cómo validar**: revisar los límites de Vercel Cron y pg_cron.

### SU-04 — Un solo consultorio
**Supuesto**: no hay multi-tenant; una sola sede.
**Origen**: Discovery (escala de un consultorio).
**Riesgo si es falso**: rediseño del modelo y de RLS.

### SU-05 — Varios turnos por paciente el mismo día
**Supuesto**: se permiten (RN-TU-08).
**Riesgo si es falso**: agregar una regla y una validación más.
**Cómo validar**: preguntar al usuario.

### SU-06 — Solo el administrador edita horarios
**Supuesto**: recepción solo consulta horarios.
**Riesgo si es falso**: cambiar la matriz RBAC.
**Cómo validar**: preguntar al usuario.
