# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

Proyecto: Sistema Odontológico (agenda de turnos). Generado el 2026-09-30.

## Decisiones de find-skill (una línea por recomendación)

Find-skill solo recomienda; la elección la tomó el equipo. Fuente de las recomendaciones: `.active-orchestrator-state.json` (`skills.recommended`).

| # | Skill | Fuente | Decisión | Justificación (una línea) |
|---|-------|--------|----------|---------------------------|
| 1 | `supabase-postgres-best-practices` | supabase/agent-skills | **Instalada** | Le enseña al agente a armar bien la base de datos PostgreSQL, para que el sistema nunca permita dos turnos en el mismo horario; aunque no usemos Supabase, sirve igual porque el proyecto usa PostgreSQL. |
| 2 | `supabase` | supabase/agent-skills | **Desinstalada** | La habíamos instalado para el stack anterior; como el profe pidió FastAPI con su propio login y base PostgreSQL, ya no sirve y la sacamos. |
| 3 | `tdd` | mattpocock/skills | **Instalada** | Hace que el agente escriba primero las pruebas y después el código, que es el método de trabajo que usamos en este proyecto. |
| 4 | `frontend-design` | anthropics/skills | **Ya disponible (local)** | Ya la teníamos instalada en el equipo (`frontend-design:frontend-design`) y sirve para que las pantallas de la agenda se vean prolijas. |
| 5 | `vercel-react-best-practices` | vercel-labs/agent-skills | **Instalada** | Le da al agente buenas prácticas de React para que las pantallas de la agenda y los formularios sean rápidas y estén bien armadas (usamos React en el frontend). |
| 6 | `web-design-guidelines` | vercel-labs/agent-skills | No instalada por ahora | Revisa accesibilidad y diseño de las pantallas, pero es un extra que puede esperar. |
| 7 | `security-and-hardening` | addyosmani/agent-skills | No instalada | La usa poca gente y, como usamos solo datos inventados de pacientes, no la necesitamos por ahora. |

**Cambio de stack:** el profe definió el stack (FastAPI, SQLAlchemy, PostgreSQL, Redis, Docker; React, TypeScript y Vite). Por eso se desinstaló `supabase` y se sumó `vercel-react-best-practices`. Las instaladas quedan en `.claude/skills/` del proyecto (ver `skills-lock.json`) con `npx skills add <fuente>@<skill> -y -a claude-code`. Se revisó el contenido de cada `SKILL.md` antes de usarlas.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| Escribir, revisar o refactorizar componentes React, carga de datos y rendimiento del frontend | vercel-react-best-practices | `.claude/skills/vercel-react-best-practices/SKILL.md` |
| Antes de crear o cambiar tablas, migraciones, índices, funciones o diagnosticar consultas lentas en Postgres | supabase-postgres-best-practices | `.claude/skills/supabase-postgres-best-practices/SKILL.md` |
| Construir features o arreglar bugs test-first, red-green-refactor, tests de integración | tdd | `.claude/skills/tdd/SKILL.md` |
| Flujo de fundación del proyecto (openspec init, discovery, KB, roadmap, find-skill, registry, agent-instruction) | active-orchestrator | `~/.claude/skills/active-orchestrator/SKILL.md` |
| Generar AGENTS.md / CLAUDE.md del proyecto | agent-instruction | `~/.claude/skills/agent-instruction/SKILL.md` |
| Fase de Discovery: investigación de mercado y Q&A | discovery-research | `~/.claude/skills/discovery-research/SKILL.md` |
| Descubrir e instalar skills | find-skill | `~/.claude/skills/find-skill/SKILL.md` |
| Crear la knowledge-base de 10 archivos | kb-creator | `~/.claude/skills/kb-creator/SKILL.md` |
| Generar CHANGES.md (roadmap de changes) | roadmap-generator | `~/.claude/skills/roadmap-generator/SKILL.md` |
| Crear o mejorar skills | skill-creator | `~/.claude/skills/skill-creator/SKILL.md` |
| Skills de frontend (UI prolija de la agenda) | frontend-design:frontend-design | plugin local `frontend-design` |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### supabase-postgres-best-practices
- Cargar antes de tocar tablas, migraciones, RLS, índices o funciones, aunque el cambio sea de una columna.
- Prioridad de reglas: consultas e índices, conexiones, seguridad y RLS (críticas); diseño de esquema (alta); bloqueos, acceso a datos y monitoreo (medias/bajas).
- Indexar claves foráneas y columnas de filtro frecuentes; usar índices parciales y compuestos cuando corresponda.
- Usar tipos de datos y restricciones explícitos (`CHECK`, `UNIQUE`, `EXCLUDE`); claves primarias y nombres en minúscula.
- RLS: envolver `auth.uid()` en `select` para rendimiento y privilegios mínimos.
- Transacciones cortas; evitar N+1 y usar inserts por lotes.
- Las reglas detalladas están en `references/<prefijo>-*.md` (query-, conn-, security-, schema-, lock-, data-, monitor-, advanced-).

### vercel-react-best-practices
- Aplica solo la parte de React puro (cliente): no usar reglas de Next.js, RSC ni `server-*` porque el frontend es React + Vite.
- Evitar cascadas de pedidos: lanzar en paralelo con `Promise.all()` los pedidos independientes a la API.
- Importar directo de cada módulo, sin archivos "barrel"; cargar con `lazy`/import dinámico los componentes pesados.
- Menos re-renders: no definir componentes dentro de otros, calcular valores derivados durante el render y usar dependencias primitivas en los efectos.
- Usar `setState` funcional y `startTransition` para actualizaciones no urgentes.
- Usar `Map`/`Set` para búsquedas repetidas y `toSorted()` para no mutar arreglos.
- Renderizado condicional con ternario, no con `&&`.
- Detalle de cada regla en `rules/<prefijo>-*.md` (async-, bundle-, client-, rerender-, rendering-, js-, advanced-).

### tdd
- **Rojo antes de verde:** escribir el test que falla primero y luego solo el código para pasarlo; nada especulativo.
- Un ciclo a la vez: un test, una implementación mínima (cortes verticales, no todos los tests primero).
- Probar comportamiento por interfaces públicas, no detalles internos; los tests sobreviven a refactors.
- Acordar con el usuario los "seams" (puntos de prueba) antes de escribir tests; ninguno en un seam sin confirmar.
- Evitar tests acoplados a la implementación y tests tautológicos: el valor esperado sale de una fuente independiente (literal, ejemplo de la spec).
- Refactorizar no es parte del ciclo rojo-verde: va en la etapa de revisión.
- Se combina con Strict TDD del proyecto: seguir las capas `domain / application / infrastructure` y probar dominio con funciones puras.

### frontend-design
- UI con intención visual clara: tipografía y jerarquía propias, sin plantillas genéricas.
- Mantener accesibilidad y consistencia en las pantallas de agenda y formularios.

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| CHANGES.md | `CHANGES.md` | Índice de los 13 changes, dependencias, riesgos y alineación con el informe |
| Knowledge base | `knowledge-base/README.md` | Índice de la base de conocimiento (11 archivos) |
| Informe de Discovery | `docs/discovery/informe-discovery.md` | Investigación de mercado y verificación de fuentes |
| Discovery Q&A | `discovery/discovery.md` | Respuestas del checklist de Discovery |
| AGENTS.md | `AGENTS.md` | Reglas duras del proyecto, skills por agente y roadmap (idéntico a `CLAUDE.md`) |
| CLAUDE.md | `CLAUDE.md` | Mismo contenido que `AGENTS.md` |

Read the convention files listed above for project-specific patterns and rules. `AGENTS.md` y `CLAUDE.md` existen en la raíz; si cambian las skills, volver a correr esta skill.
