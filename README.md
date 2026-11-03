# Sistema Odontológico: agenda de turnos

Trabajo de integración de Metodología I (Tecnicatura Universitaria en Programación): del Discovery al primer change con Spec-Driven Development (OpenSpec) y Active Stack.

Sistema de gestión de turnos y agenda de pacientes para consultorios odontológicos, pensado para el mercado argentino. Un consultorio puede tener uno o varios odontólogos y la agenda se maneja por profesional.

## Video explicativo

[Ver el video explicativo en YouTube](https://youtu.be/Wz8IocynNSU)

## Qué hay en este repositorio

| Carpeta o archivo | Contenido |
|---|---|
| `docs/discovery/` | Informe de Discovery (investigación de mercado, `.md` y `.pdf`) |
| `discovery/` | Respuestas del checklist de Discovery |
| `knowledge-base/` | Base de conocimiento: visión, descripción, actores, modelo de datos, reglas, funcionalidades, flujos, arquitectura, decisiones y preguntas abiertas (más un archivo extra sobre recordatorios por email y su índice) |
| `CHANGES.md` | Roadmap de 13 changes con dependencias, camino crítico y riesgos |
| `.atl/skill-registry.md` | Registro de skills con la decisión de cada recomendación |
| `AGENTS.md` y `CLAUDE.md` | Reglas del proyecto para los agentes (mismo contenido) |
| `.active-orchestrator-state.json` | Estado de la fundación del proyecto |
| `openspec/specs/` | Especificaciones vigentes (`appointment-creation`) |
| `openspec/changes/archive/` | Change archivado `crear-turno-sin-solapamientos` (proposal, design, tasks y specs) |
| `backend/app/` | Implementación del change (lógica de dominio en Python) |
| `backend/tests/` | Tests automatizados, uno por cada escenario de la especificación |
| `docs/opsx/` | Resumen de Explore y registro de Verify del change |
| `docs/engram/` | Evidencia de la memoria del agente (Engram) |
| `.claude/skills/revisor-escenarios-turnos/` | Skill propia del agente para revisar escenarios de agenda |
| `docs/skills-mcp/` | Ficha de investigación, referencia de la skill creadora, configuración de ejemplo del MCP y evidencias |

El código está en `backend/` porque el stack del proyecto tiene backend y frontend separados (FastAPI y React). Por ahora solo existe la lógica de dominio del change elegido.

## Cómo instalar y correr los tests

Requisitos: Python 3.12 o superior.

```bash
cd backend
python -m venv .venv
```

Activar el entorno virtual:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (Git Bash) o Linux/macOS: `source .venv/Scripts/activate` o `source .venv/bin/activate`

Instalar las dependencias y correr los tests:

```bash
pip install pytest tzdata
pytest
```

Resultado esperado: `33 passed`.

## El change implementado

`crear-turno-sin-solapamientos`: dado un profesional, su horario, sus licencias y sus turnos, el sistema responde si se puede crear un turno nuevo o no, con un solo motivo de rechazo en orden fijo (anticipación mínima de 6 horas, grilla de 30 minutos, horario de trabajo, licencia y solapamiento). Los turnos que empiezan justo cuando termina otro no se consideran solapados.

Para ver el recorrido completo: `docs/opsx/explore-crear-turno-sin-solapamientos.md`, `openspec/changes/archive/` y `docs/opsx/verify-crear-turno-sin-solapamientos.md`.

## Herramientas del agente: skill propia y MCP

Estas incorporaciones son herramientas de desarrollo para el agente (Claude Code). No forman parte del producto. Detalle de la investigación en `docs/skills-mcp/investigacion.md`.

### Skill propia: `revisor-escenarios-turnos`

Está en `.claude/skills/revisor-escenarios-turnos/` y viene con el repositorio: al clonarlo y abrirlo con Claude Code ya está disponible. Revisa los escenarios de un change de agenda contra la base de conocimiento. Cómo se creó y cómo reproducir `skill-creator`: `docs/skills-mcp/skill-creator.md`.

### MCP: Context7 (documentación actualizada de librerías)

- **Para qué**: consultar la documentación vigente de librerías (por ejemplo `zoneinfo` de Python, pytest, Pydantic, FastAPI) mientras se prepara un change.
- **Herramientas**: `resolve-library-id` (obtiene el identificador de la librería) y `query-docs` (consulta la documentación). Siempre se usan en ese orden.
- **Requisitos**: Claude Code y Node.js con `npx` (se probó con Node v24.19.0).
- **Variables de entorno**: ninguna. Context7 funciona sin clave de API; la clave es opcional y solo da más límite de uso. Si se llega a usar una, va en la configuración local del usuario y nunca en el repositorio.
- **Configuración**: servidor local (`stdio`) declarado a nivel usuario en `~/.claude.json`, clave `mcpServers.context7`. El ejemplo sin secretos está en `docs/skills-mcp/mcp-context7.example.json`. Para reproducirla, agregar ese bloque a la configuración de Claude Code (a nivel usuario, o como `.mcp.json` en la carpeta del proyecto) y reiniciar la sesión.
- **Comprobar la conexión**: ejecutar `claude mcp list` en una terminal. Debe aparecer `context7: npx -y --package=@upstash/context7-mcp@2.2.5 -- context7-mcp - ✔ Connected`.
- **Comprobar que funciona**: pedirle al agente una consulta concreta, por ejemplo "consultá en Context7 cómo convierte `zoneinfo` un datetime UTC a hora local". Debe llamar a `resolve-library-id` y después a `query-docs`.
- **Límites de uso**: solo se consulta documentación pública. No se envían datos de pacientes (ni siquiera ficticios), claves ni código propio en las consultas, porque el texto de la consulta viaja al servicio externo de Context7.
- **Problemas de instalación**: en esta instalación no apareció ninguno. Una advertencia de uso: `query-docs` exige antes un identificador obtenido con `resolve-library-id`.
- **Evidencia de uso real**: `docs/skills-mcp/evidencias/mcp-context7-uso.md`.

## Stack previsto

Backend: Python, FastAPI, JWT, SQLAlchemy, PostgreSQL, Redis y Docker Compose. Frontend: React, TypeScript y Vite. Todo gratuito, con datos de pacientes ficticios. El detalle está en `knowledge-base/02_descripcion_general.md`.
