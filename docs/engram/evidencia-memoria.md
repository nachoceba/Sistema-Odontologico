# Etapa 7: memoria del agente (Engram)

Fecha de la consulta: 2026-10-06. Proyecto en Engram: `sistema-odontologico`.

## 1. Qué quedó guardado

Estadísticas que devolvió Engram (`mem_stats`): **1 sesión, 7 observaciones, 1 proyecto**.

| # | Tipo | Título | Qué guarda |
|---|---|---|---|
| 1 | Resumen de sesión | Session summary: sistema-odontologico | Fundación del proyecto (29/09): openspec, discovery, KB, roadmap, find-skill, skill-registry y agent-instruction |
| 2 | Configuración | Skill registry y skills instaladas | Skills instaladas (`supabase-postgres-best-practices`, `tdd`, `vercel-react-best-practices`), la desinstalación de `supabase` y dónde está el registro |
| 3 | Decisión | OPSX: propose completed for crear-turno-sin-solapamientos | Propose del change: 7 requisitos, escenarios dado/cuando/entonces, diseño y decisiones (6 h inclusivas, `now` inyectado, semana desde el lunes, grilla desde el inicio del tramo) |
| 4 | Resumen de sesión | Session summary: sistema-odontologico | Etapas 0 a 6, preferencias del usuario, hallazgos y próximos pasos |
| 5 | Decisión | Cambio de stack: de Next.js+Supabase al stack del profe | Stack final (FastAPI, SQLAlchemy, PostgreSQL, Redis/Celery, Docker; React, TypeScript, Vite) y sus consecuencias |
| 6 | Decisión | Regla RN-TU-12: anticipación mínima de 6 horas configurable | La regla, el motivo y dónde está en la KB y en el código |
| 7 | Preferencia | Convenciones y preferencias del usuario | Commits sin marca de IA, tono criollo, consulta antes de cada fase, revisión con subagentes |

Las decisiones y hallazgos importantes (stack, regla de anticipación, convenciones) tienen su propia observación, con el formato Qué / Por qué / Dónde / Aprendido.

## 2. Consulta real que recupera contexto de una sesión anterior

Se abrió una sesión nueva (el 06/10), sin haber leído nada de lo hecho el 30/09, y se consultó a la memoria.

**Consulta 1:** `mem_search("anticipacion minima turno", match_mode="any")`
Resultado: la observación **#3**, creada el **2026-09-30 21:15**, con el detalle completo del Propose: anticipación mínima de 6 h inclusiva y configurable, `now` inyectado, semana desde el lunes, grilla anclada al inicio del tramo, rangos semiabiertos, solo los turnos `scheduled` ocupan lugar y dónde están los archivos del change.

**Consulta 2:** `mem_search("por que 6 horas anticipacion", match_mode="any")`
Resultado: la observación **#6** con el motivo: dar tiempo al doctor y al consultorio; 6 h para consultorios tranquilos y 12 h para agenda llena.

**Contexto reciente:** `mem_context` devolvió las últimas sesiones y observaciones, entre ellas el resumen del 30/09 con el estado de las etapas 0 a 6 y lo que faltaba (la Etapa 7).

## 3. Cómo esto evita que el agente arranque de cero

Sin memoria, en una sesión nueva el agente no sabe nada de lo que pasó: habría que volver a leer todos los archivos del repositorio y preguntarle de nuevo al usuario cada decisión (por qué 6 horas, por qué ese stack, cómo prefiere los commits).

Con la memoria alcanza con una búsqueda corta. En la consulta de arriba, una sesión nueva recuperó en segundos una decisión de hace una semana, con su motivo y los archivos donde está. También recuperó las preferencias del usuario, así que no hace falta repetirlas. El agente retoma desde donde se quedó en vez de empezar de cero.

## 4. Límites y aclaraciones

- Engram guarda lo que el agente decide anotar, no todo lo que pasa: al comienzo de esta etapa había solo 4 notas y se completaron hasta 7.
- Los avisos de conflicto que Engram marca automáticamente entre notas parecidas se revisaron: eran notas relacionadas o compatibles, sin contradicciones.
- Existe otra herramienta de memoria automática (claude-mem), distinta de Engram. Esta evidencia usa solo Engram.
- La memoria vive en la computadora del usuario; no se versiona dentro del repositorio.
