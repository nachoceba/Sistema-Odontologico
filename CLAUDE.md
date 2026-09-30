# Sistema Odontológico — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

Sistema de gestión de agenda de turnos para un consultorio odontológico, con recordatorios por email. Proyecto académico (Metodología I): todo gratuito y con datos de pacientes ficticios.

---

## Stack Tecnológico

| Capa | Tecnología | Nota |
|------|------------|------|
| Backend | Python + FastAPI | API REST documentada con OpenAPI |
| Validación | Pydantic | Esquemas de entrada y salida |
| ORM / migraciones | SQLAlchemy 2.0 (síncrono) + Alembic | Migraciones versionadas |
| Base de datos | PostgreSQL | Constraint de exclusión para superposición (`btree_gist`) |
| Autenticación | JWT | Email + contraseña con hash seguro; token de vida corta |
| Autorización | `require_role` (dependencia de FastAPI) | Chequeo de rol en la capa de aplicación; no hay RLS |
| Tareas asincrónicas | Redis + Celery + Celery Beat | Emails y recordatorio programado |
| Email | SMTP | Mailpit en desarrollo; proveedor gratuito a definir |
| Frontend | React + TypeScript + Vite | SPA que consume la API REST |
| Contenedores | Docker / Docker Compose | Un comando levanta `db`, `redis`, `api`, `worker`, `beat`, `frontend`, `mailpit` |
| Tests | pytest (backend) y Vitest (frontend) | Foco en la capa de dominio |

Arquitectura en capas del backend: `api/` → `application/` → `domain/` (funciones puras) → `infrastructure/`.

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, arquitectura e integraciones |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, constraints, migraciones, seed |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-XX) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos extremo a extremo |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Capas, estructura de directorios, variables de entorno |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones DD y supuestos SU |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Inconsistencias a resolver ANTES de codear |
| [11_recordatorios_email.md](knowledge-base/11_recordatorios_email.md) | Emails de confirmación y recordatorio |

> ⚠️ Preguntas de prioridad **Alta** abiertas en `10_preguntas_abiertas.md`: proveedor SMTP gratuito y su cupo (SU-02), aceptación de Celery por la cátedra (DD-10) y quién edita los horarios de los profesionales (SU-06). Resolverlas antes de los changes que dependen de ellas (C-01, C-07, C-11/C-12).

Contexto de mercado (no normativo): [docs/discovery/informe-discovery.md](docs/discovery/informe-discovery.md).

---

## Skills Disponibles

<!-- Fuente: .atl/skill-registry.md -->

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI / SQLAlchemy / Alembic / PostgreSQL | `supabase-postgres-best-practices` (solo la parte de PostgreSQL: esquema, índices, constraints), `tdd` |
| **Backend Aux / Dominio** | Funciones puras de `domain/`, Celery, email | `tdd` |
| **Frontend** | React + TypeScript + Vite | `frontend-design:frontend-design`, `vercel-react-best-practices` (solo la parte de React), `tdd` |
| **Orquestación** | OPSX / SDD / docs | `kb-creator`, `roadmap-generator`, `agent-instruction`, `skill-creator` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

> La skill `supabase` se desinstaló porque no aplica a este stack (no hay Supabase, RLS ni Next.js). De `supabase-postgres-best-practices` ignorar lo específico de Supabase (RLS, `auth.uid()`). De `vercel-react-best-practices` usar solo las reglas de React; ignorar lo de Next.js y Server Components.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 13 changes en 6 fases (0 Fundación, 1 Datos y acceso, 2 Dominio y catálogos, 3 Agenda de turnos MVP, 4 Notificaciones por email, 5 Salida a producción).
- **Camino crítico** (7): `C-01 → C-02 → C-03 → C-08 → C-11 → C-12 → C-13`, con una cadena paralela de igual longitud `C-01 → C-02 → C-03 → C-07 → C-09 → C-10 → C-13`.
- **Primer change**: `C-01` (`foundation-setup`).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras (específicas del proyecto)

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

**Stack y arquitectura**

1. Python con type hints en todo el código; en el frontend, TypeScript estricto, sin `any`.
2. NUNCA importar FastAPI, SQLAlchemy, Celery ni Redis desde `domain/` → funciones puras; el I/O solo va en `infrastructure/`.
3. La no superposición de turnos se garantiza con el constraint de exclusión en la migración de Alembic y se valida también en el dominio; NUNCA confiar solo en la aplicación.
4. Todo endpoint exige JWT y chequeo de rol (`require_role`), salvo el login; cada endpoint lleva su test de permisos por rol.
5. NUNCA commitear `.env` ni claves → solo `.env.example`; los secretos (`JWT_SECRET_KEY`, `SMTP_PASSWORD`, base de datos) jamás van al frontend ni a variables `VITE_`.

**Regla de dominio**

6. NUNCA permitir que un profesional tenga dos turnos superpuestos: la regla se valida en el código y además la base de datos la bloquea; todo cambio en la agenda debe incluir un test de ese caso.

**Universales (no cubiertas por el global)**

7. NUNCA commitear ni pushear sin pedido explícito del usuario → proponer el mensaje y esperar.
8. NUNCA agregar `Co-Authored-By` ni marca de IA en commits o PRs.
9. Verificar con pytest, Vitest, typecheck y lint; levantar Docker solo para los tests de integración.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)       → respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
