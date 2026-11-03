# Referencia: skill creadora (`skill-creator`) y skill propia

Cómo reproducir la herramienta con la que se creó `revisor-escenarios-turnos`. Verificado el 2026-11-03.

## La skill creadora

| Dato | Valor |
|---|---|
| Nombre | `skill-creator` |
| Fuente oficial | Repositorio de Anthropic [`anthropics/skills`](https://github.com/anthropics/skills), carpeta `skills/skill-creator` |
| Licencia | Apache 2.0 (`LICENSE.txt` dentro de la carpeta) |
| Instalada en | `~/.claude/skills/skill-creator/` (global, **fuera** del repositorio) |
| Contenido | `SKILL.md`, `agents/`, `assets/`, `eval-viewer/`, `references/`, `scripts/`, `LICENSE.txt` |

## Cómo reproducir la instalación

1. **Comprobar que el repositorio oficial la ofrece** (verificado; no instala nada):

   ```bash
   npx -y skills add anthropics/skills --list
   ```

   El listado muestra 20 skills, entre ellas `skill-creator`.

2. **Instalarla** con el mismo mecanismo que usa este proyecto para las demás skills (`skills-lock.json`):

   ```bash
   npx skills add anthropics/skills@skill-creator -y -a claude-code
   ```

   Este comando exacto **no se ejecutó** en esta entrega, porque la skill ya estaba instalada de forma global. Es la forma de instalación documentada por el propio proyecto (ver `.atl/skill-registry.md`), pendiente de probar en una máquina limpia.

3. **Comprobar que está disponible**: debe existir `~/.claude/skills/skill-creator/SKILL.md` y la skill tiene que aparecer en la lista de skills de una sesión nueva de Claude Code.

## La skill propia

`revisor-escenarios-turnos` se creó con `skill-creator` siguiendo su método: borrador, casos de prueba con y sin la skill, revisión de resultados y ajuste.

- **Ubicación (versionada en el repo)**: `.claude/skills/revisor-escenarios-turnos/SKILL.md`. Como vive dentro del repositorio, no hace falta una copia aparte: clonar el repo alcanza para tenerla.
- **Registro**: `.atl/skill-registry.md` (tabla de skills y reglas compactas).
- **Instrucciones del agente**: sección "Skill propia" en `CLAUDE.md` y `AGENTS.md`.
- **Pruebas y resultados**: `docs/skills-mcp/evidencias/skill-pruebas/` (tres casos, cada uno con y sin la skill).

## Qué se cambió después de las pruebas

La primera versión no leía `CHANGES.md` ni `04_modelo_de_datos.md`. Los agentes que la usaron dejaron sin detectar que la firma de `compute_slots` no incluye la zona horaria, y dejaron sospechas sin confirmar sobre los datos. Se corrigió agregando esas dos fuentes y un sexto tipo de hallazgo, "contrato incompleto".

En la prueba en una sesión nueva (`evidencias/prueba-sesion-nueva-*.png`) el agente encontró y ejecutó la skill, pero rotuló el error más grave como "contradice una regla", un tipo que la skill no tenía. Se agregó como séptimo tipo, "contradicción", para que el formato sea consistente.
