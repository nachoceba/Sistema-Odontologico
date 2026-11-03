---
name: revisor-escenarios-turnos
description: Revisa escenarios o specs de agenda y turnos del sistema odontológico contra la base de conocimiento para detectar reglas ambiguas, casos de borde faltantes y decisiones de dominio sin respaldo. Usala siempre que explores, propongas o escribas la spec, el design o las tasks de un change que toque turnos, horarios, licencias, slots, zona horaria o estados del turno (por ejemplo C-05b calcular-slots-disponibles, C-07, C-08, C-09), aunque el usuario no pida "revisar escenarios" de forma explícita. También cuando pida "qué casos faltan", "revisá la spec" o "buscá ambigüedades".
---

# Revisor de escenarios de turnos

Esta skill es una herramienta de desarrollo para el agente. No forma parte del producto: el consultorio nunca la ve.

## Para qué sirve

Una spec de agenda suele cubrir el caso feliz y olvidarse de los bordes (un tramo que no entra justo, un turno que cruza medianoche en UTC, una licencia de un día). Esos huecos aparecen tarde, cuando el código ya está escrito, y arreglarlos cuesta más. La skill obliga a hacer la revisión antes, siempre de la misma manera y apoyada en la KB, no en lo que el agente "recuerda" de las reglas.

## Qué necesitás

1. Los escenarios o la spec borrador que se quiere revisar. Si todavía no existen, los escenarios que el agente tenga pensados.
2. Las reglas de la KB, **leídas en el momento**, no de memoria:
   - `knowledge-base/05_reglas_de_negocio.md` (RN-HO, RN-TU, RN-PA, RN-GL-01 y las que apliquen)
   - `knowledge-base/10_preguntas_abiertas.md` (preguntas abiertas y su prioridad)
   - `knowledge-base/09_decisiones_y_supuestos.md` si un hallazgo toca una decisión DD o un supuesto SU
   - `knowledge-base/04_modelo_de_datos.md` para confirmar campos, estados y constraints reales. Sin esto las sospechas sobre los datos (profesional inactivo, licencias con fechas invertidas) quedan sin confirmar.
   - `CHANGES.md`, la entrada del change que se revisa: su alcance y la firma prevista de las funciones. Los escenarios deben ser coherentes con ese contrato.
3. La spec principal vigente si el change extiende un dominio ya archivado (por ejemplo `openspec/specs/appointment-creation/spec.md`).

## Procedimiento

1. **Listá los escenarios** que se van a revisar, uno por línea, con su resultado esperado.
2. **Mapeá cada escenario a las reglas RN** que lo gobiernan. Un escenario sin ninguna regla asociada es un hallazgo en sí mismo.
3. **Buscá estos siete tipos de problema:**
   - **Contradicción**: el resultado esperado del escenario choca con una regla de la KB (ejemplo: una franja de 15:30 con slot de 30 minutos termina fuera de un tramo que cierra a las 15:45, contra RN-TU-03). Es el hallazgo más grave: el escenario está mal, no solo incompleto.
   - **Contrato incompleto**: la firma o el alcance que figura en `CHANGES.md` no alcanza para los escenarios (ejemplo: la función recibe fechas pero ningún parámetro de zona horaria, o el mapeo de `weekday` no está definido).
   - **Ambigüedad**: la regla admite dos lecturas (ejemplo: un slot que no entra completo en el tramo, RN-TU-02 y RN-TU-03).
   - **Borde faltante**: no hay escenario para un límite (inicio o fin exacto de tramo, turnos pegados, cambio de día por zona horaria, licencia de un solo día, día sin horarios).
   - **Reglas solapadas o reemplazadas**: dos reglas dicen cosas parecidas (por ejemplo RN-TU-04 quedó cubierta por RN-TU-12) y el escenario cita la equivocada.
   - **Pregunta abierta que bloquea**: el escenario depende de algo sin responder en `10_preguntas_abiertas.md` (SU-01 zona horaria, SU-05 varios turnos por día, duración real del slot).
   - **Decisión de dominio sin respaldo**: el escenario asume algo que no está en ninguna RN, DD ni SU.
4. **Verificá cada hallazgo contra el texto de la KB** antes de listarlo. Si no podés citar la línea o el código de la regla, no es un hallazgo: es una sospecha, y se marca como tal.
5. **No resuelvas las decisiones de dominio vos mismo.** Proponé una opción como sugerencia, marcada como "decisión a confirmar", y dejá que el usuario decida. Si el usuario la confirma, recién ahí se registra en la KB con su justificación.

## Formato de la respuesta

Usá siempre esta estructura:

```
## Revisión de escenarios: <change o tema>

### Resumen
<N> escenarios revisados, <M> hallazgos (<a> ambigüedades, <b> bordes faltantes, <c> reglas solapadas, <d> preguntas abiertas, <e> sin respaldo, <f> contrato incompleto, <g> contradicciones).

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|

### Escenarios sin hallazgos
<lista corta>

### Decisiones que necesitan al usuario
<lista numerada de preguntas concretas>
```

La columna "Respaldo en la KB" lleva el código y el archivo (por ejemplo `RN-TU-03`, `05_reglas_de_negocio.md`) o la frase literal **"sin respaldo en la KB"**.

## Cómo revisar el resultado

Antes de dar por buena una revisión, comprobá:

- Cada hallazgo cita una regla, una pregunta abierta o dice "sin respaldo en la KB". Sin esa columna completa, la revisión no sirve.
- Los códigos citados existen de verdad en el archivo (abrilo y buscalo).
- Ninguna decisión de dominio quedó incorporada como si fuera un hecho: todas figuran en "Decisiones que necesitan al usuario".
- Hay al menos un escenario esperado, uno de error de negocio y uno de borde en lo que se revisó (lo exige la spec de un change). Si falta alguno, es un hallazgo.
- No se inventaron reglas, estados ni campos que no estén en `04_modelo_de_datos.md` o `05_reglas_de_negocio.md`.

## Límites

- Trabaja con datos y escenarios ficticios; no hace falta ni conviene usar datos reales de pacientes (RN-PR-01).
- No escribe código ni tests: solo revisa y señala. La implementación sigue el flujo TDD del proyecto (`tdd`).
- No modifica la KB por su cuenta; propone cambios y espera la confirmación del usuario.
