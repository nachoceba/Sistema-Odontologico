# Spec Delta: schedule-conflicts

## Purpose

Detectar, sin base de datos ni reloj propio, qué turnos `scheduled` de un profesional quedan fuera de su horario de trabajo o dentro de una licencia, para que recepción los reprograme o cancele sin que el sistema los toque (RN-HO-04, Flujo 5).

## ADDED Requirements

### Requirement: Turnos en conflicto con el horario y las licencias (RN-HO-04)

La regla de conflictos SHALL recibir los tramos de horario de un profesional, sus licencias, sus turnos, el momento actual y la zona horaria del consultorio, y MUST devolver los turnos que cumplen las tres condiciones siguientes: (1) estado `scheduled`; (2) todavía no empezaron, es decir, el momento actual es anterior a su inicio (DD-23, P-3); (3) no entran completos, inicio y fin, dentro de un mismo tramo del día de la semana local de su inicio (mismo criterio que RN-TU-03), o la fecha local de su inicio está dentro de una licencia (RN-HO-03, días completos inclusivos). Un turno que sigue entrando en un tramo pero ya no cae en la grilla de ese tramo MUST NOT considerarse en conflicto (P-3). El resultado MUST ordenarse por inicio y MUST indicar para cada turno el motivo: "fuera de horario" o "en licencia" (si se cumplen los dos, "en licencia"). La regla MUST NOT modificar, cancelar ni guardar nada, y MUST NOT leer el reloj (el momento actual llega como dato).

#### Scenario: Acortar el horario deja un turno afuera (esperado)
- **WHEN** la Dra. A tiene un turno `scheduled` el lunes 5 de octubre de 2026 de 12:30 a 13:00 (hora local), el momento actual es el 1 de octubre y su horario nuevo del lunes es 09:00–12:00
- **THEN** el resultado contiene ese turno con motivo "fuera de horario"

#### Scenario: Licencia sobre un día con turnos (esperado)
- **WHEN** la Dra. A tiene dos turnos `scheduled` el miércoles 14 de octubre dentro de su horario y una licencia del 12 al 16 de octubre
- **THEN** el resultado contiene los dos turnos, ordenados por inicio, con motivo "en licencia"

#### Scenario: Turno que sigue dentro del horario (esperado)
- **WHEN** la Dra. A tiene un turno el lunes 5 de octubre de 09:30 a 10:00 y su horario nuevo del lunes es 09:00–12:00 sin licencias
- **THEN** el resultado es vacío

#### Scenario: Turnos cancelados, atendidos o ausentes no cuentan (borde)
- **WHEN** fuera del horario nuevo hay un turno `cancelled`, uno `completed` y uno `no_show` de la Dra. A
- **THEN** el resultado es vacío

#### Scenario: Turno ya iniciado o pasado no cuenta (borde)
- **WHEN** un turno `scheduled` de la Dra. A fuera del horario nuevo empieza exactamente en el momento actual, y otro terminó ayer
- **THEN** el resultado es vacío (DD-23: un turno con inicio igual al momento actual ya empezó)

#### Scenario: Turno que termina justo en el fin del tramo (borde)
- **WHEN** el horario nuevo del lunes es 09:00–12:00 y la Dra. A tiene un turno de 11:30 a 12:00
- **THEN** el resultado es vacío (intervalos semiabiertos, DD-27)

#### Scenario: Turno que queda a caballo entre dos tramos (borde)
- **WHEN** el horario nuevo del lunes es 09:00–11:15 y 11:15–13:00 y la Dra. A tiene un turno de 11:00 a 11:30
- **THEN** el resultado contiene ese turno con motivo "fuera de horario" (debe entrar completo en un mismo tramo, RN-TU-03)

#### Scenario: Turno fuera de la grilla nueva pero dentro del tramo (borde)
- **WHEN** el horario del lunes pasa de 09:00–13:00 a 09:15–13:00 y la Dra. A tiene un turno de 10:00 a 10:30
- **THEN** el resultado es vacío (P-3: solo cuenta quedar fuera del horario o en licencia)

#### Scenario: Sin horario cargado (borde)
- **WHEN** el horario nuevo de la Dra. A es una semana vacía y tiene tres turnos `scheduled` futuros
- **THEN** el resultado contiene los tres con motivo "fuera de horario"

#### Scenario: Fuera de horario y en licencia a la vez (borde)
- **WHEN** un turno futuro de la Dra. A cae en un día de licencia y además fuera del horario nuevo
- **THEN** aparece una sola vez en el resultado, con motivo "en licencia"

#### Scenario: Día de la semana según la hora local (borde)
- **WHEN** la zona del consultorio es `America/Argentina/Buenos_Aires` y un turno empieza el martes 6 de octubre a las 01:30 UTC (lunes 22:30 local), con horario solo los lunes 20:00–23:00
- **THEN** el resultado es vacío (el día de la semana y la licencia se evalúan en hora local, RN-GL-01)

#### Scenario: Primer día y día siguiente a una licencia (borde)
- **WHEN** la Dra. A tiene una licencia del 12 al 12 de octubre, un turno el 12 a las 09:00 y otro el 13 a las 09:00, ambos dentro de su horario
- **THEN** el resultado contiene solo el del 12, con motivo "en licencia" (días completos inclusivos, RN-HO-03)

#### Scenario: Turno que empieza a medianoche local dentro de una licencia (borde)
- **WHEN** la Dra. A tiene horario los lunes 00:00–02:00, una licencia del lunes 12 al lunes 12 de octubre y un turno el lunes 12 a las 00:00 local (03:00 UTC)
- **THEN** el resultado contiene ese turno con motivo "en licencia" (la fecha se evalúa en hora local, RN-GL-01)

#### Scenario: Turnos de otro profesional se ignoran (borde)
- **WHEN** la lista de turnos recibida incluye un turno del Dr. B fuera del horario de la Dra. A
- **THEN** el resultado para la Dra. A no lo contiene

#### Scenario: Instante sin zona horaria (error de programación)
- **WHEN** el momento actual llega sin zona horaria
- **THEN** la regla lanza `ValueError` (DD-18)
