# Explore: `calcular-slots-disponibles` (C-05b)

Fase EXPLORE del ciclo OPSX. Solo lectura sobre el código; este archivo y las dos evidencias de `docs/skills-mcp/evidencias/aplicacion/` son lo único que se escribió. Es una preparación: no se implementa ni se archiva en esta entrega.
Origen: C-05 `domain-scheduling-core` (`CHANGES.md`), segundo recorte después de C-05a.

## 1. Problema

La UI de agenda (US-006, C-09) y el Flujo 2 paso 1 necesitan saber, para un profesional y un día, qué franjas están libres, ocupadas o fuera de horario. Hoy solo existe `validate_appointment` (C-05a), que responde por un turno suelto. C-05b agrega la función pura `compute_slots` y el módulo `app/core/timezone.py` (conversión UTC <-> zona del consultorio, inicio y fin de día local, RN-GL-01). Sin base de datos, sin red, sin pantallas.

## 2. Estado actual y qué se reutiliza de C-05a

Evidencia (lectura del repo):

- `backend/app/domain/appointments/` tiene `types.py` y `validation.py`. En `backend/tests/unit/domain/appointments/` hay `helpers.py` y `test_validate_appointment.py`. No existe `backend/app/core/` (lo crea este change).
- Se reutiliza de `types.py`: `WorkingHours` (weekday 0 = lunes, hora local), `TimeOff` (fechas locales inclusivas), `ExistingAppointment` (UTC, con `professional_id` y `status`) y `AppointmentStatus`. Convención del archivo: dataclasses inmutables, solo librería estándar, sin ORM.
- Se reutiliza de `validation.py` la lógica privada: pasar a hora local con `ZoneInfo`, grilla anclada al inicio de cada tramo, rango semiabierto `[inicio, fin)` para solapes, y solo `scheduled` del mismo profesional ocupa. Hoy esos helpers son privados y `_to_local` está duplicable: conviene que C-05b mueva la conversión a `app/core/timezone.py` y que `validation.py` la use (refactor menor, ver riesgo 3).
- Se reutiliza de los tests: `helpers.py` (`local()`, `monday()`, `DRA_A_HOURS`, `appointment()`) y el estilo de funciones `test_...` con nombres descriptivos. Las reglas de la spec `appointment-creation` (grilla, tramo, licencia, solape) son el contrato de coherencia con `compute_slots`.
- Firma prevista en `CHANGES.md` C-05: `compute_slots(working_hours, time_off, appointments, slot_minutes, date)` (libre / ocupado / fuera de horario).

## 3. Alcance y límites propuestos

Entra:

- `app/core/timezone.py`: UTC a hora local, hora local a UTC, inicio y fin del día local en UTC, para una zona IANA dada (RN-GL-01).
- `compute_slots` en `domain/appointments`: clasifica cada franja del día local de un profesional como libre / ocupada / fuera de horario.
- Tests pytest puros con casos de borde parametrizados (ver evidencia de Context7).

Reglas que lo gobiernan: RN-HO-01, RN-HO-03 (licencias), RN-TU-01 (solape, ocupación por `scheduled`), RN-TU-02 (grilla), RN-TU-03 (el turno debe entrar completo en el tramo), RN-TU-09/10/11 (por profesional, slot fijo, sin sobreturnos), RN-GL-01.

No entra (según el pedido): base de datos, pantallas, login, emails, validación de tramos (RN-HO-02, otro recorte: los tramos se tratan como dato de confianza), transiciones de estado, regla de paciente inactivo, puertos de repositorios.

## 4. Contrato propuesto (a confirmar)

Propuesta, no es código final. Es compatible con `validate_appointment`: argumentos por nombre, `professional_id` como `str`, y `timezone` con el mismo valor por defecto.

```
compute_slots(
    *,
    professional_id: str,
    day: date,                                  # fecha LOCAL del consultorio
    working_hours: Sequence[WorkingHours],      # ya filtrados del profesional
    time_off: Sequence[TimeOff],                # ya filtrados del profesional
    existing_appointments: Sequence[ExistingAppointment],  # puede traer varios profesionales; se filtra
    slot_minutes: int = 30,
    timezone: str = "America/Argentina/Buenos_Aires",
) -> list[Slot]
```

- `Slot` (dataclass inmutable): `starts_at: datetime` y `ends_at: datetime` en UTC con zona, y `status: SlotStatus`.
- `SlotStatus` (enum): `FREE`, `BUSY`, `OUTSIDE_HOURS`. Son los tres estados que nombran US-006 y C-09; no se agrega ninguno.
- Orden: cronológico ascendente por `starts_at`, sin huecos ni solapes entre franjas.
- Una franja `FREE` debe ser aceptada por `validate_appointment` (salvo anticipación mínima, ver decisión 4). Esa coherencia es una propiedad testeable.
- Errores de programación (no de negocio): `ValueError` si `slot_minutes <= 0` o si `day` no es una fecha (decisión 6).

## 5. Escenarios candidatos

Supuesto común: Buenos Aires (UTC-3), `slot_minutes = 30`, la Dra. A atiende lunes de 09:00 a 13:00 y de 14:00 a 18:00, lunes 5 de octubre de 2026. Los estados de los escenarios 1 y 8 dependen de las decisiones 1 y 2.

Esperados:

1. Lunes sin turnos: 8 franjas `FREE` de 09:00 a 13:00 y 8 de 14:00 a 18:00; el resto del día `OUTSIDE_HOURS` (RN-TU-02, RN-TU-03).
2. Turno `scheduled` 10:00-10:30: la franja 10:00 es `BUSY`; 09:30 y 10:30 son `FREE` (turnos pegados, rango `[inicio, fin)`, RN-TU-01).
3. Turno `cancelled` 10:00-10:30: la franja 10:00 es `FREE` (RN-TU-05).
4. Turno `scheduled` de otro profesional a las 10:00: la franja de la Dra. A es `FREE` (RN-TU-09).

Error de negocio o de entrada:

5. Licencia que cubre el lunes: las 16 franjas de tramos quedan `OUTSIDE_HOURS` (RN-HO-03; depende de la decisión 3).
6. `slot_minutes = 0` o negativo: `ValueError`. `day` que no es `date`: `ValueError` (decisión 6).

Bordes:

7. Tramo 09:00-13:15 con slot de 30: la franja 13:00-13:30 no entra completa en el tramo y queda `OUTSIDE_HOURS`; la última `FREE` es 12:30 (RN-TU-03; decisión 2).
8. Tramo que arranca 09:15: franjas 09:15, 09:45, etc.; la grilla se ancla al inicio del tramo, como en C-05a (RN-TU-02).
9. Día sin tramos (domingo): ninguna franja `FREE` (decisión 2 define si es lista vacía o día entero `OUTSIDE_HOURS`).
10. Día local en UTC: el lunes local va de 03:00 UTC del lunes a 03:00 UTC del martes. Un turno `scheduled` del martes a las 01:30 UTC (22:30 local del lunes) no toca ninguna franja del lunes; uno del martes a las 03:00 UTC pertenece al martes (RN-GL-01).
11. Turno existente desalineado 10:15-10:45: marca `BUSY` las franjas 10:00 y 10:30 por solape parcial (RN-TU-01).
12. Licencia de varios días (viernes a martes) con el lunes adentro: todo `OUTSIDE_HOURS`; el miércoles siguiente al fin queda libre. Licencia de un solo día (`starts_on == ends_on`) (RN-HO-03).
13. Turno `completed` o `no_show` a las 10:00: según C-05a no ocupa (decisión 5).
14. Slot de 45 minutos sobre un tramo de 09:00-13:00: las franjas son 09:00, 09:45, ... y la última que entra termina 12:45 (RN-TU-03).
15. Tramos contiguos (09:00-13:00 y 13:00-17:15) con anclas distintas en cada tramo (RN-TU-02).
16. Coherencia: toda franja `FREE` es aceptada por `validate_appointment` con el mismo input y un `now` lejano (propiedad que cruza C-05a y C-05b).

Los tests de bordes se escriben con `@pytest.mark.parametrize` y `pytest.param(..., id="...")` (fuente: Context7 sobre pytest, `docs/skills-mcp/evidencias/aplicacion/context7-c05b-pytest.md`).

## 6. Riesgos

1. **Firma de `CHANGES.md` incompleta**: no trae `timezone` ni `professional_id` ni el tipo de salida (hallazgo 1 de la skill). Hay que ajustar la entrada de C-05 en `CHANGES.md` si se confirma el contrato.
2. **Cuarto estado**: la tentación de agregar `TIME_OFF` no tiene respaldo en la KB (hallazgo 3).
3. **Duplicación con `validation.py`**: si `compute_slots` copia la lógica de grilla y de solape, dos funciones pueden divergir. Mitigación: extraer los helpers compartidos y probar la coherencia (escenario 16). Cambiar `validation.py` es una decisión de alcance a confirmar.
4. **Zona horaria**: SU-01 sin confirmar. Argentina no usa DST; con otra zona un día podría durar 23 o 25 horas. La spec debe declararlo como supuesto (hallazgo 9). La doc de Context7 sobre `zoneinfo` (evidencia previa `mcp-context7-uso.md`) confirma que `fold` y horas inexistentes solo importan con DST.
5. **Duración de slot real**: la pregunta de la KB (15, 20 o 30 minutos) sigue abierta y baja; con otro valor la grilla cambia.
6. **Anticipación mínima**: si la UI muestra `FREE` una franja que `validate_appointment` rechaza por RN-TU-12, el usuario ve un slot no reservable (decisión 4).
7. **Turnos que cruzan el límite del día local**: no ocurre con horarios razonables, pero conviene decidir qué hace la función si un turno existente cruza la medianoche local.
8. **Concurrencia**: como en C-05a, `compute_slots` es una foto; solo el constraint de exclusión (C-02) garantiza la no superposición.
9. **Gobernanza**: C-05 es MEDIO; implementar con checkpoints y mostrar decisiones no obvias al usuario.

## 7. Aportes de las incorporaciones del TP

- Skill `revisor-escenarios-turnos` (invocada como skill con la herramienta Skill): produjo 12 hallazgos sobre un borrador de 14 escenarios. Se incorporaron como riesgos 1, 2, 4 a 6 y como la lista de decisiones de abajo. Salida completa en `docs/skills-mcp/evidencias/aplicacion/skill-revisor-c05b.md`.
- MCP Context7 (respondió de verdad): resolvió `/pytest-dev/pytest` y devolvió la documentación de `parametrize` con ids (`ids=[...]`, `idfn`, `pytest.param(id=...)`). Se usa para el diseño de los tests de bordes. Detalle en `docs/skills-mcp/evidencias/aplicacion/context7-c05b-pytest.md`.

## 8. Decisiones de dominio abiertas (decisión del usuario)

1. **Firma y salida de `compute_slots`.** ¿Recibe `professional_id` y `timezone`, y devuelve una lista de `Slot` (UTC + estado)?
   - A) Sí, como en la sección 4.
   - B) Mantener la firma de `CHANGES.md` y que el llamador convierta todo.
   - C) Recibir el rango UTC del día ya calculado.
   - Recomendación: A. Respaldo: RN-GL-01, RN-TU-09; contrato de `CHANGES.md` C-05 incompleto (no define zona ni profesional).
2. **Rango de la grilla y franja que no entra.** ¿Qué franjas se devuelven?
   - A) Todo el día local, con `OUTSIDE_HOURS` fuera de tramos y para el resto parcial de un tramo.
   - B) Solo desde el inicio del primer tramo hasta el fin del último.
   - C) Solo las franjas que caen dentro de tramos; el domingo devuelve lista vacía.
   - Recomendación: A. Respaldo: US-006 pide diferenciar "libres, ocupados y fuera de horario" y RN-TU-03 exige turno completo en el tramo; sin respaldo en la KB sobre qué rango de franjas se devuelve.
3. **Licencia.** ¿Cómo se informa un día con licencia?
   - A) `OUTSIDE_HOURS`.
   - B) Estado nuevo `TIME_OFF`.
   - C) Lista vacía.
   - Recomendación: A. Respaldo: RN-HO-03; la KB nombra solo tres estados (US-006, C-09). Un cuarto estado: sin respaldo en la KB.
4. **Anticipación mínima.** ¿`compute_slots` la considera?
   - A) No; la rechaza `validate_appointment` y la UI lo maneja.
   - B) Sí, con `now` y `min_notice_hours` opcionales, marcando esas franjas como no libres.
   - C) Sí, con un cuarto estado.
   - Recomendación: A. Respaldo: RN-TU-12 y DD-14 (la regla vive en `validate_appointment`); `CHANGES.md` C-05 no pasa `now` a `compute_slots`.
5. **Estados que ocupan una franja.** ¿Ocupan solo los `scheduled`?
   - A) Solo `scheduled`.
   - B) También `completed`.
   - C) También `completed` y `no_show`.
   - Recomendación: A (igual que C-05a). Respaldo: RN-TU-01 y el constraint `WHERE (status = 'scheduled')` de `04_modelo_de_datos.md`; sin respaldo en la KB para slots de UI.
6. **Errores de entrada.** ¿Qué hace la función con `slot_minutes <= 0` o un `day` inválido?
   - A) `ValueError` (error de programación, como la regla de datetime naive de C-05a).
   - B) Devolver lista vacía.
   - Recomendación: A. Respaldo: spec `appointment-creation` (datetime naive); sin respaldo en la KB para `slot_minutes <= 0`.
7. **Zona horaria y DST.** ¿Se asume una zona sin horario de verano?
   - A) Sí, declarado como supuesto (SU-01) y sin escenarios de días de 23/25 horas.
   - B) Soportar DST ahora.
   - Recomendación: A. Respaldo: SU-01 y la pregunta abierta sobre la zona del consultorio en `10_preguntas_abiertas.md`.
8. **Refactor de `validation.py`.** ¿Se extraen los helpers compartidos y se mueve la conversión a `app/core/timezone.py`?
   - A) Sí, tocando C-05a de forma mínima y con sus 33 tests en verde.
   - B) No; `compute_slots` duplica la lógica y se prueba la coherencia.
   - Recomendación: A. Respaldo: sin respaldo en la KB (decisión de diseño); regla dura 2 y patrón de funciones puras de `08_arquitectura_propuesta.md`.
9. **Turno existente que cruza el límite del día local.** ¿Cuenta en las franjas del día siguiente?
   - A) Sí, por solape con la franja (`[inicio, fin)`).
   - B) No, se ignora fuera del día pedido.
   - Recomendación: A. Respaldo: RN-TU-01; sin respaldo en la KB sobre turnos que cruzan medianoche.

## 9. Siguiente acción recomendada

`/opsx:propose C-05b-calcular-slots-disponibles` una vez que el usuario resuelva las decisiones 1 a 6 como mínimo; las demás se pueden dejar con la recomendación.
