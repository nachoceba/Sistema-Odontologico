# Tasks: C-16 `online-booking-expiry`

> Depende de C-15 `public-patient-booking` implementado y archivado. TDD estricto: RED, GREEN, TRIANGULATE y REFACTOR, con línea de base antes de tocar cada archivo existente.
> Skills: `tdd` en todo; `supabase-postgres-best-practices` (solo PostgreSQL) en el grupo 1; `revisor-escenarios-turnos` en el grupo 3.

## 1. Esquema

- [x] 1.1 Línea de base: `pytest`, `pytest -m integration` y `pytest -m smoke` en verde. Anotar las cantidades
- [x] 1.2 RED/GREEN: migración `0004` con el valor `booking_expired` en `notification_kind`. Tests en `tests/integration/db/test_migration.py`: se acepta, el `UNIQUE` impide el duplicado y la reversión falla si hay filas. Verificar en verde, con `test_models_match_migration.py` incluido

## 2. Vencimiento

- [x] 2.1 RED/GREEN: `AppointmentRepository.expire_pending(now, limit)` con `FOR UPDATE SKIP LOCKED`. Test de contrato en memoria y en PostgreSQL: cancela con el motivo y limpia las columnas; no toca vigentes, confirmados ni turnos de recepción; un vencimiento exacto se cancela. Verificar en verde
- [x] 2.2 RED/GREEN/TRIANGULATE: caso de uso `expire_pending_bookings`, que cancela y registra un `booking_expired` `pending` en la misma transacción y lo despacha después del commit. Repetirlo no cambia nada. Un fallo del despachador no deshace la cancelación. Devuelve la cantidad. Verificar en verde
- [x] 2.3 RED/GREEN: tarea `vencer_reservas_pendientes` y su programación cada 5 minutos en Beat. Tests del registro de la tarea, del log sin datos personales y de que no hay ruta HTTP nueva (inventario de rutas sin cambios). Verificar en verde

## 3. Aviso de vencimiento

- [x] 3.1 RED/GREEN: `NotificationRepository.add_pending_booking_expired` con `ON CONFLICT DO NOTHING`. Contrato: una sola fila aunque se llame dos veces. Verificar en verde
- [x] 3.2 RED/GREEN/TRIANGULATE: plantilla `booking_expired` en texto plano. Cubre asunto, profesional, fecha y hora local (13:30 UTC → 10:30), la frase de cancelación, el enlace a `/turnos`, los datos del consultorio, la línea de `EMAIL_REDIRECT_TO`, y que no tiene documento ni datos ajenos. Verificar en verde
- [x] 3.3 RED/GREEN: regla de envío de `deliver_notification` para `booking_expired`. Envía si el turno está cancelado por vencimiento y no empezó; queda `EXPIRED` si otro motivo canceló el turno, si se confirmó o si ya empezó; y usa los reintentos de C-11. Los tests previos de `confirmation` y `reminder` siguen sin cambios. Verificar en verde
- [x] 3.4 Revisión con `revisor-escenarios-turnos` del vencimiento y del aviso contra RN-TU-05, RN-TU-14, RN-NO-04, RN-NO-05 y DD-21. Llevar las decisiones nuevas al usuario

## 4. Integración (Docker)

- [x] 4.1 Test con dos conexiones: la confirmación toma la fila primero y el vencimiento la saltea. El turno queda confirmado, con una confirmación de C-11 y sin `booking_expired`. Verificar en verde
- [x] 4.2 Test con dos conexiones: el vencimiento toma la fila primero y la confirmación recibe 410. El turno queda cancelado, con un `booking_expired` y sin confirmación. Verificar en verde
- [x] 4.3 Test: dos pasadas simultáneas cancelan cada reserva una vez y dejan un solo `booking_expired`. Verificar en verde
- [x] 4.4 Test con Mailpit: una reserva con DNI existente vence y el aviso llega al email de la ficha, con el profesional y la hora local; una cancelada por la recepción no recibe aviso. Verificar en verde
- [x] 4.5 Test: después de vencer, la franja vuelve a las franjas públicas y la recepción la puede agendar (regla dura 6). Verificar en verde
- [x] 4.6 Sumar al smoke una reserva que vence con la tarea forzada y su aviso en Mailpit. Verificar `pytest -m smoke` en verde

## 5. Documentación

- [x] 5.1 KB según D-3 (`04`, `05`, `07`, `09` con DD-140 y `11`). Verificar que RN-NO-05 nombra la excepción y que los códigos citados existen
- [x] 5.2 `CHANGES.md`: entrada C-16 con dependencia de C-15, scope, exclusiones, governance y "Leer antes", y el resumen del roadmap en `CLAUDE.md` y `AGENTS.md`. Verificar que los dos resúmenes son iguales
- [x] 5.3 Verificación final: `pytest`, `pytest -m integration`, `pytest -m smoke`, `mypy --strict app/`, `ruff check` y `openspec validate online-booking-expiry --strict` en verde. Anotar las cantidades en la entrada de C-16
