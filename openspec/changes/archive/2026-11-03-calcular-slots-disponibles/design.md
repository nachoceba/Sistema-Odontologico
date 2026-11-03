# Design: calcular-slots-disponibles (C-05b)

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: `specs/slot-availability/spec.md` y `specs/clinic-timezone/spec.md`.

Estado actual (leído del repo, no supuesto):

- `backend/app/domain/appointments/types.py` define `WorkingHours` (weekday 0 = lunes, horas locales), `TimeOff` (fechas locales inclusivas), `ExistingAppointment` (instantes UTC, `professional_id`, `status`), `AppointmentStatus` y `ValidationResult`. Todo `@dataclass(frozen=True)` y solo librería estándar.
- `backend/app/domain/appointments/validation.py` (C-05a) tiene `validate_appointment` y helpers privados que C-05b necesita igual: `_to_local` (con `ZoneInfo`), `_minutes_of_day`, `_is_on_time_off`, `_ranges_overlap` (rango semiabierto) y `_overlaps_existing` (solo `scheduled` del mismo profesional).
- `backend/tests/unit/domain/appointments/` tiene `helpers.py` (`local()`, `monday()`, `NOW`, `DRA_A_HOURS`, `DR_B_HOURS`, `appointment()`, `validate()`) y `test_validate_appointment.py` con los 33 tests de C-05a.
- No existe `backend/app/core/`.
- El explore (`docs/opsx/explore-calcular-slots-disponibles.md`) dejó 9 decisiones de dominio; el usuario las resolvió todas (abajo, D-1 a D-9).

Restricciones: regla dura 2 (`domain/` no importa FastAPI, SQLAlchemy, Celery ni Redis), Strict TDD, governance MEDIO, datos ficticios.

## Goals / Non-Goals

**Goals:**

- Una sola fuente de verdad para la conversión UTC <-> zona del consultorio (`app/core/timezone.py`), usada por `compute_slots` y por `validate_appointment`.
- Que `compute_slots` y `validate_appointment` no puedan divergir: comparten los mismos helpers de grilla, licencia y solapamiento, y un test de coherencia lo comprueba.
- Tests de bordes legibles y trazables a la spec (`pytest.param(..., id=...)`).

**Non-Goals:**

- Cambiar el comportamiento de `validate_appointment` (refactor puro; los 33 tests son la red de seguridad).
- Validar los tramos (RN-HO-02): se asumen ya válidos y sin superposición, como los garantiza el modelo (`working_hours`: `start_time < end_time`, sin superposición).
- Optimizar: un día tiene como mucho 1440 / `slot_minutes` franjas; un recorrido lineal por los turnos alcanza.

## Decisions

### Decisiones de dominio tomadas por el usuario

**D-1. Firma y salida.** `compute_slots` recibe el profesional y la zona del consultorio y devuelve `list[Slot]` con inicio y fin en UTC y estado. Contrato (argumentos por nombre, compatible con `validate_appointment`):

```
compute_slots(
    *,
    professional_id: str,
    day: date,                                   # fecha LOCAL del consultorio
    working_hours: Sequence[WorkingHours],       # ya filtrados del profesional
    time_off: Sequence[TimeOff],                 # ya filtrados del profesional
    existing_appointments: Sequence[ExistingAppointment],  # puede traer otros profesionales
    slot_minutes: int = 30,
    timezone: str = "America/Argentina/Buenos_Aires",
) -> list[Slot]
```

Respaldo: RN-GL-01 (fechas en UTC, mostradas en la zona del consultorio), RN-TU-09 (se agenda por profesional), `clinic_settings.timezone` y `slot_minutes` en `04_modelo_de_datos.md`. Alternativas descartadas: (B) mantener la firma de `CHANGES.md` sin zona ni profesional y que el llamador convierta: deja RN-GL-01 repartida entre capas; (C) recibir el rango UTC ya calculado: obliga al llamador a saber de días locales, que es justo lo que este change encapsula. La firma de C-05 en `CHANGES.md` la actualiza el usuario.

**D-2. Rango: el día local completo.** Se devuelven las franjas de 00:00 a 24:00 locales; lo que no es un slot completo dentro de un tramo es `OUTSIDE_HOURS`, incluido el resto de un tramo que no alcanza para un slot (ej. 15:30-15:45 en un tramo 14:00-15:45). Respaldo: US-006 ("slots libres, ocupados y fuera de horario diferenciados") y RN-TU-03 (turno completo dentro del tramo). **Decisión de diseño sin respaldo en la KB en cuanto al rango**: la KB no dice qué intervalo devuelve la función. Motivo: con el día completo la vista diaria (C-09) dibuja la grilla sin calcular nada y el día sin tramos y la licencia tienen la misma forma que un día normal. Alternativas descartadas: (B) solo del primer al último tramo: la grilla cambia de largo día a día; (C) solo las franjas dentro de tramos, domingo = lista vacía: no distingue "fuera de horario" de "no hay datos".

**D-2a. Grilla fuera de tramos (consecuencia de D-2, hallazgo 3 de la skill).** **Decisión de diseño sin respaldo en la KB.** Dentro de un tramo, la grilla se ancla al inicio del tramo (RN-TU-02, igual que C-05a). Fuera de tramos, las franjas son de `slot_minutes` contadas desde las 00:00 o desde el fin del tramo anterior, y se recortan al llegar al inicio del tramo siguiente o a las 24:00. El resto de un tramo que no alcanza un slot se recorta al fin del tramo. Solo las franjas `OUTSIDE_HOURS` pueden durar menos de `slot_minutes`. Motivo: es la única forma de que la lista sea contigua, sin huecos ni solapes, con tramos anclados en minutos distintos (09:15) o contiguos (13:15). Alternativa descartada: una grilla única anclada a las 00:00 para todo el día: las franjas fuera de horario pisarían las del tramo cuando el tramo no empieza en múltiplo de `slot_minutes`.

**D-3. Licencia = `OUTSIDE_HOURS`, sin cuarto estado.** Respaldo: RN-HO-03, US-005 ("los días de licencia no ofrecen slots"), US-006 y C-09 nombran tres estados. Alternativas descartadas: estado `TIME_OFF` (sin respaldo en la KB) y lista vacía (pierde la forma del día).

**D-4. Sin anticipación mínima.** `compute_slots` no recibe `now`; RN-TU-12 la sigue aplicando `validate_appointment` (DD-14). Respaldo: RN-TU-12, DD-14, `CHANGES.md` C-05 (no pasa `now`). Alternativas descartadas: `now` y `min_notice_hours` opcionales marcando franjas no libres (mezcla una regla de creación con la de ocupación y vuelve no determinista la vista por el reloj); un cuarto estado (sin respaldo). Consecuencia aceptada: la UI puede mostrar `FREE` una franja que la creación rechaza con `INSUFFICIENT_NOTICE` (escenario "Franja libre aunque falten menos de 6 horas").

**D-5. Solo `scheduled` ocupa.** Respaldo: RN-TU-01, RN-TU-05 (cancelar libera el slot), DD-05 y el constraint `EXCLUDE … WHERE (status = 'scheduled')` de `04_modelo_de_datos.md`; mismo criterio que C-05a. Alternativas descartadas: que `completed` o `no_show` ocupen (la base no los excluye, la vista mentiría respecto de lo que se puede agendar).

**D-6. Entradas inválidas → `ValueError`.** `slot_minutes <= 0` o `day` que no es `date`. **Decisión de diseño sin respaldo en la KB**: la KB no habla de errores de programación. Motivo: misma convención que C-05a (datetime sin zona → `ValueError`); son errores del llamador, no motivos de negocio, y una lista vacía los escondería. Alternativa descartada: devolver lista vacía.

**D-6a. Una fecha y hora no es un `day` válido (hallazgo 4 de la skill).** **Decisión de diseño sin respaldo en la KB.** En Python `datetime` hereda de `date`, así que `isinstance(day, date)` lo aceptaría y la hora se ignoraría en silencio. Se rechaza con `ValueError` (chequeo explícito de `datetime` antes que el de `date`). Motivo: un llamador que pasa un instante probablemente confundió UTC con hora local; fallar temprano evita mostrar el día equivocado.

**D-7. Supuesto: zona sin horario de verano.** Se declara SU-01 (consultorio en `America/Argentina/Buenos_Aires`, sin confirmar) y no hay escenarios de días de 23 o 25 horas. **Supuesto sin respaldo confirmado en la KB** (SU-01 figura como no confirmado y la zona es pregunta abierta Media). Motivo: Argentina no usa horario de verano; soportarlo exige definir qué hacer con horas repetidas o inexistentes (`fold`), que no aportan al MVP. El código no debe depender de que el día dure 24 horas (calcula inicio y fin del día con la zona), pero los tests no lo cubren.

**D-8. Refactor de `validation.py`.** **Decisión de diseño sin respaldo en la KB.** Los helpers compartidos pasan a un módulo común `app/domain/appointments/rules.py` (grilla anclada al tramo, licencia inclusiva, solapamiento semiabierto, ocupación por `scheduled` del mismo profesional) y la conversión de hora a `app/core/timezone.py`. `validation.py` los usa sin cambiar su comportamiento; los 33 tests de C-05a son la red de seguridad y se corren antes y después de cada paso. Motivo: con dos copias de la misma regla, `compute_slots` podría marcar `FREE` algo que `validate_appointment` rechaza; la regla dura 2 y el patrón "funciones puras de dominio" de `08_arquitectura_propuesta.md` empujan a una sola implementación. Alternativa descartada: duplicar la lógica y confiar solo en el test de coherencia (detecta la divergencia tarde y no la evita).

**D-9. Turno que cruza la medianoche local cuenta por solapamiento.** **Decisión de diseño sin respaldo en la KB.** Un turno existente se compara como rango de instantes UTC con cada franja (`[inicio, fin)`), sin recortarlo al día pedido; si toca una franja dentro de tramo de cualquiera de los dos días, la marca `BUSY`. Motivo: es la misma regla de solapamiento de RN-TU-01 sin casos especiales, y la que aplica el constraint de exclusión en la base. Alternativa descartada: ignorar la parte del turno fuera del día pedido (mostraría libre una franja ocupada).

### Decisiones técnicas del diseño

**D-T1. Tipos de salida.** `SlotStatus(Enum)` con `FREE`, `BUSY`, `OUTSIDE_HOURS` y `Slot` como `@dataclass(frozen=True)` con `starts_at`, `ends_at` (UTC con zona) y `status`, en `types.py`. Respaldo técnico: documentación de CPython consultada con Context7 (`docs/skills-mcp/evidencias/aplicacion/context7-c05b-propose.md`): `frozen=True` da inmutabilidad (`FrozenInstanceError`), `__eq__` por campo y `__hash__`; la igualdad de `datetime` con zona compara instantes. Como la igualdad no garantiza la representación, un test verifica además `utcoffset() == timedelta(0)` en cada franja.

**D-T2. Precedencia de estados.** `OUTSIDE_HOURS` > `BUSY` > `FREE` (requisito "Precedencia de estados y conflictos"). **Decisión de diseño sin respaldo en la KB**, surgida del hallazgo 1 de la skill (RN-HO-04). Motivo: el estado de la franja responde "¿se puede agendar acá?"; los conflictos de RN-HO-04 los lista C-07 y C-09 dibuja los turnos con su propia consulta. Alternativa descartada: `BUSY` sobre `OUTSIDE_HOURS` (una franja fuera de horario aparecería "ocupada" y la grilla dejaría de reflejar el horario).

**D-T3. Algoritmo.** `compute_slots` vive en `app/domain/appointments/slots.py` (al lado de `validation.py`). Validar entradas; calcular inicio y fin del día local con `app/core/timezone.py`; si el día está en licencia, todas las franjas son `OUTSIDE_HOURS` (misma grilla que un día normal); ordenar los tramos del `weekday` local; recorrer el día con un cursor en hora local generando las franjas de D-2a; pasar cada franja a UTC; marcar `BUSY` las franjas de tramo que se solapan con un `scheduled` del profesional (helper compartido).

**D-T4. `app/core/timezone.py`.** Tres funciones puras: `to_local(instant, timezone)` (rechaza naive con `ValueError`), `to_utc(local_naive, timezone)` (rechaza aware con `ValueError`) y `local_day_bounds(day, timezone) -> tuple[datetime, datetime]` (inicio incluido, fin excluido, en UTC). `app/core/__init__.py` queda vacío: `core` también alojará seguridad y configuración (`08_arquitectura_propuesta.md`), y `domain` no debe arrastrar esas dependencias al importar `timezone`.

**D-T5. Tests.** Archivos `backend/tests/unit/core/test_timezone.py` y `backend/tests/unit/domain/appointments/test_compute_slots.py`, reutilizando `helpers.py` (se le agregan helpers de lectura de franjas, por ejemplo `slot_at(slots, hour, minute)`). Los bordes se agrupan por requisito con `@pytest.mark.parametrize` y `pytest.param(..., id="...")` con ids legibles (evidencia `context7-c05b-pytest.md`); un id por escenario de la spec.

## Risks / Trade-offs

- [Divergencia entre `compute_slots` y `validate_appointment`] → helpers compartidos (D-8) y el test de coherencia de la spec.
- [El refactor rompe C-05a] → los 33 tests se corren como línea base antes de tocar `validation.py` y después de cada paso; cualquier rojo detiene el refactor.
- [La UI muestra libre una franja no reservable por anticipación mínima] → aceptado (D-4); `validate_appointment` lo rechaza con `INSUFFICIENT_NOTICE` y C-10 muestra el mensaje.
- [Los conflictos de RN-HO-04 no se ven en las franjas] → aceptado (D-T2); los lista C-07 y C-09 muestra los turnos.
- [Zona con horario de verano] → supuesto SU-01 (D-7); si la zona cambia, agregar escenarios de 23/25 horas y de horas repetidas.
- [Duración real del slot sin confirmar (pregunta Baja)] → `slot_minutes` es parámetro; los tests cubren 30 y 45.
- [Concurrencia] → `compute_slots` es una foto; la no superposición la garantiza el constraint de exclusión (C-02, DD-04).
- [Importar `app.core` desde `domain`] → `core/__init__.py` vacío y `timezone.py` solo con librería estándar.

## Migration Plan

No aplica: código nuevo y puro, sin base de datos ni despliegue. Rollback = revertir el commit.

## Open Questions

Preguntas que no cambian los escenarios ni las tasks si se responde con la recomendación (hallazgos 5 y 6 de la skill; decisión del usuario):

1. **Zona horaria inexistente** (`"America/Inexistente"`): recomendación, dejar que propague el error de `zoneinfo` (`ZoneInfoNotFoundError`), porque la zona viene de `clinic_settings` y su validación corresponde a quien la edita. Si el usuario prefiere `ValueError`, se agrega un escenario y una task.
2. **Turnos existentes sin zona**: recomendación, precondición documentada en el docstring (heredada de C-05a: los turnos llegan en UTC desde `timestamptz`). Si el usuario prefiere validarlo con `ValueError`, se agrega un escenario y una task.
