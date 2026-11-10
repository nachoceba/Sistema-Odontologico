# Spec Delta: notification-tasks

## ADDED Requirements

### Requirement: Vencimiento de reservas cada 5 minutos (DD-132)

Celery Beat SHALL disparar cada 5 minutos la tarea `vencer_reservas_pendientes`, que aplica la regla de la spec `online-booking-expiry`. No existe ninguna ruta HTTP para dispararla, y el inventario de rutas y la matriz de permisos no cambian.

#### Scenario: Programación registrada (esperado)
- **WHEN** se inspecciona la programación de Beat
- **THEN** figura `vencer_reservas_pendientes` cada 5 minutos junto a las tareas de C-11 y C-12

#### Scenario: Sin ruta HTTP (borde)
- **WHEN** se busca en la documentación OpenAPI una ruta de vencimiento
- **THEN** no existe ninguna
