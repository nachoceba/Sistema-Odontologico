# Revision de escenarios C-05b `calcular-slots-disponibles`

Base: RN-HO-01..03, RN-TU-01/02/03/05/12, RN-GL-01, DD-03, SU-01, modelo de datos (`working_hours`, `time_off`, `clinic_settings`), CHANGES.md (scope de C-05: `compute_slots(working_hours, time_off, appointments, slot_minutes, date)`).

## Revision por escenario

1. **Tramo 09:00-12:00, slot 30, sin turnos: seis franjas libres.** Correcto (09:00, 09:30, 10:00, 10:30, 11:00, 11:30). Agregar que 12:00 NO es una franja (el turno debe terminar dentro del tramo, RN-TU-03). Es el limite superior y conviene asertarlo.
2. **Turno scheduled 10:00: franja 10:00 ocupada, demas libres.** Correcto, pero incompleto: falta el contraste con un turno `cancelled` en la misma hora (RN-TU-05: libera el slot), que es la regla que justifica filtrar por estado. Tambien falta turno `completed`/`no_show`: la KB solo dice que `scheduled` bloquea (RN-TU-01); decidir si esos estados ocupan o no la franja.
3. **Dia con licencia: todas las franjas "fuera de horario".** Hay que revisarlo:
   - No es un "error de negocio": `compute_slots` es pura y no lanza error; devuelve una clasificacion. Reencuadrar como escenario esperado.
   - Falta cubrir limites de `time_off`: `starts_on` y `ends_on` son fechas inclusivas (el primer y el ultimo dia estan cubiertos); el dia anterior al inicio y el posterior al fin no. Hoy solo se prueba un dia en el medio.
   - Falta el caso licencia + turno existente ese dia (RN-HO-04: no se cancelan turnos, se marcan como conflicto). Definir que muestra la franja: ¿"fuera de horario" o "ocupado"? La KB no lo resuelve; es una decision a tomar y escribir en la spec.
   - Decidir si la licencia de un profesional afecta solo a ese profesional (si `time_off` se filtra antes de llamar a la funcion o dentro).
4. **Tramo de tarde 14:00-15:45: franjas 14:00, 14:30, 15:00, 15:30 libres.** Hay un problema: 15:30 + 30 min termina 16:00, que excede el tramo (15:45). Por RN-TU-03 (turno completo dentro del tramo) la franja 15:30 NO deberia ser libre. Salen solo 14:00, 14:30 y 15:00 libres; 15:30 queda fuera de horario (o no existe). Ademas, RN-TU-02 dice que el inicio cae en la grilla del horario del profesional; un tramo que no es multiplo del slot es justo el caso de borde a especificar: ¿el remanente de 15 min se descarta? Reescribirlo como escenario de borde con resultado explicito (3 libres, resto descartado/fuera de horario).
5. **Turno a las 23:30 local guardado en UTC aparece en el dia correcto.** Dos observaciones:
   - Con `America/Argentina/Buenos_Aires` (UTC-3, sin horario de verano, SU-01) 23:30 local = 02:30 UTC del dia siguiente. Es un buen caso porque el dia UTC difiere del dia local. Pero la spec debe fijar los numeros concretos (fecha local, instante UTC) para ser testeable.
   - Un consultorio no tendria un tramo hasta las 23:30, y ademas RN-TU-03 exigiria un tramo que lo cubra. El escenario necesita un tramo valido (p. ej. 22:00-24:00 de prueba) o se prueba con un tramo mas realista y turnos en el limite de dia (00:00 local = 03:00 UTC). Aclarar tambien si `compute_slots` recibe `appointments` ya en UTC (lo mas probable) y la zona como parametro: la firma de CHANGES.md **no incluye timezone**, hay que agregarla o convertir antes (depende de `app/core/timezone.py`, que tambien es de C-05b en adelante).
   - Tramo que termina a medianoche: `end_time` 24:00 no es un `time` valido; ver faltantes.

## Casos que faltan

- **Sin tramo ese dia** (el `weekday` no tiene `working_hours`, p. ej. sabado/domingo): todo el dia fuera de horario o lista vacia. Definir que devuelve.
- **Varios tramos el mismo dia** (manana 09-12 + tarde 14-17): las franjas entre tramos (12:00-14:00) ¿se listan como fuera de horario o no se listan? Define el contrato de salida (¿grilla del dia completo o solo del horario?).
- **Mapeo de `weekday` (0-6)**: la KB no dice si 0 es lunes (Python `weekday()`) o domingo. Fijarlo en la spec con un test (fecha concreta -> weekday).
- **Turno que no cae en la grilla** (p. ej. 10:15 por un cambio de `slot_minutes` o de horario): ¿ocupa dos franjas parcialmente? Hay que definir el solape parcial.
- **Cambio de `slot_minutes`** (15/20/45): triangular con otro valor; 30 solo oculta bugs. Incluir uno que no divida el tramo.
- **Turnos de otro dia y de otro profesional**: no deben afectar la salida (el filtro por dia local es justo el escenario 5; el filtro por profesional depende de quien lo haga).
- **Anticipacion minima (RN-TU-12) y franjas pasadas**: ¿`compute_slots` marca como no disponibles las franjas del pasado/dentro de `min_notice_hours`? CHANGES.md lo asigna a `validate_appointment`, no a slots. Decidirlo explicito; si queda fuera, decirlo en "fuera de alcance" para que no se asuma. Si `compute_slots` no recibe `now`, la UI mostrara libres franjas que luego el alta rechaza.
- **Turnos no `scheduled`**: ver punto 2.
- **Transicion DST / dias de 23-25 horas**: no aplica (Argentina sin DST), pero la spec debe declararlo como supuesto (SU-01) para que nadie lo pruebe ni lo asuma.
- **Entradas invalidas** (tramos superpuestos o `start >= end`): son responsabilidad de la validacion de tramos (RN-HO-02), no de `compute_slots`. Declarar que la funcion asume entrada ya validada o que falla de forma definida.
- **Orden y determinismo de la salida**: franjas ordenadas por inicio, con inicio/fin y estado; sin duplicados cuando hay tramos adyacentes (09-12 y 12-14).
- **Relacion con el constraint de exclusion (reglas duras 3 y 6)**: la spec debe aclarar que la clasificacion "libre" es informativa y no garantia (carrera entre dos recepcionistas, US-007); el choque se resuelve en la base.

## Decisiones a tomar antes de escribir la spec

1. Contrato de salida: ¿grilla de todo el dia o solo franjas dentro del horario? (condiciona los escenarios 3 y 4, que hoy suponen "fuera de horario" para franjas que existen).
2. Prioridad entre estados cuando coinciden licencia y turno.
3. Firma con zona horaria y fecha: `date` local del consultorio, appointments en UTC.
4. Que estados bloquean una franja.

## Resumen de ajustes

| # | Veredicto | Ajuste |
|---|-----------|--------|
| 1 | OK | Agregar que 12:00 no es franja |
| 2 | OK, incompleto | Sumar turno cancelado / otros estados |
| 3 | Reencuadrar | No es error; sumar bordes de rango y licencia + turno |
| 4 | Incorrecto | 15:30 termina 16:00 > 15:45: solo 3 libres |
| 5 | Util, impreciso | Fijar numeros UTC, tramo valido y timezone en la firma |
