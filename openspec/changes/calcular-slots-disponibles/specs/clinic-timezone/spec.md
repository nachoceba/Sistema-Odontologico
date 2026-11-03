# Spec Delta: clinic-timezone

## Purpose

Convertir de forma única y pura entre instantes UTC (como se guardan las fechas) y la hora local del consultorio (como se muestran y se interpretan horarios y días), y dar el inicio y el fin de un día local expresados en UTC (RN-GL-01).

## ADDED Requirements

> Datos comunes: zona del consultorio `America/Argentina/Buenos_Aires` (UTC-3). Se asume que la zona no tiene horario de verano (supuesto SU-01, sin confirmar); no hay escenarios de días de 23 o 25 horas.

### Requirement: De instante UTC a hora local del consultorio

El sistema SHALL convertir un instante con zona a la hora local de la zona del consultorio, conservando el instante (solo cambia la representación). Un instante sin zona (naive) MUST rechazarse con `ValueError`.

#### Scenario: Conversión simple
- **DADO** el instante 5 de octubre de 2026 a las 12:00 UTC
- **CUANDO** se convierte a la hora local del consultorio
- **ENTONCES** el resultado es el 5 de octubre de 2026 a las 09:00 locales, con desplazamiento -03:00

#### Scenario: La conversión cambia la fecha (borde)
- **DADO** el instante 6 de octubre de 2026 a las 01:30 UTC
- **CUANDO** se convierte a la hora local del consultorio
- **ENTONCES** el resultado es el lunes 5 de octubre de 2026 a las 22:30 locales

#### Scenario: Instante sin zona (error de entrada)
- **DADO** la fecha y hora `2026-10-05 12:00` sin zona horaria
- **CUANDO** se pide convertirla a la hora local del consultorio
- **ENTONCES** se lanza `ValueError`

### Requirement: De hora local del consultorio a instante UTC

El sistema SHALL convertir una fecha y hora local del consultorio (sin zona, leída como hora de reloj del consultorio) al instante UTC equivalente, con zona UTC. Una fecha y hora que ya trae zona MUST rechazarse con `ValueError`, para no reinterpretar un instante.

#### Scenario: Hora local a UTC
- **DADO** la hora local `2026-10-05 09:00` del consultorio
- **CUANDO** se convierte a UTC
- **ENTONCES** el resultado es el 5 de octubre de 2026 a las 12:00 UTC, con desplazamiento cero

#### Scenario: Hora local que ya trae zona (error de entrada)
- **DADO** la fecha y hora `2026-10-05 09:00` con zona UTC
- **CUANDO** se pide convertirla como hora local a UTC
- **ENTONCES** se lanza `ValueError`

### Requirement: Inicio y fin del día local en UTC

El sistema SHALL devolver, para una fecha local del consultorio, el instante UTC de sus 00:00 locales (inicio, incluido) y el de las 00:00 locales del día siguiente (fin, excluido). Un instante igual al fin pertenece al día siguiente.

#### Scenario: Límites del lunes 5 de octubre de 2026
- **DADO** la fecha local lunes 5 de octubre de 2026
- **CUANDO** se piden el inicio y el fin del día local en UTC
- **ENTONCES** el inicio es el 5 de octubre de 2026 a las 03:00 UTC y el fin es el 6 de octubre de 2026 a las 03:00 UTC
- **Y** la diferencia entre ambos es de 24 horas

#### Scenario: El fin del día pertenece al día siguiente (borde)
- **DADO** el instante 6 de octubre de 2026 a las 03:00 UTC
- **CUANDO** se convierte a la hora local del consultorio
- **ENTONCES** su fecha local es el martes 6 de octubre de 2026 (00:00)
- **Y** coincide con el inicio del día local del martes 6 de octubre
