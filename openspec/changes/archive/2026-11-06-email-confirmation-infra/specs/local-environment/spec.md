# Spec Delta

## MODIFIED Requirements

### Requirement: Worker y beat con la zona del consultorio

Los servicios `worker` y `beat` SHALL arrancar conectados a Redis como broker, con la zona horaria de la programación igual a `CLINIC_TIMEZONE` y con los instantes internos en UTC. Desde C-11 el `worker` MUST arrancar solo después de que `db` y `redis` estén sanos (procesa notificaciones guardadas en la base) y MUST ejecutar las tareas de la spec `notification-tasks`; `beat` MUST programarlas. En el entorno de desarrollo los emails MUST llegar a Mailpit y verse en su interfaz web.

#### Scenario: Worker conectado
- **WHEN** el entorno está levantado
- **THEN** el log de `worker` indica que está listo, conectado al broker en `redis`, y lista `enviar_email` y `reencolar_pendientes` entre sus tareas

#### Scenario: Zona de la programación (esperado)
- **WHEN** se inspecciona la configuración de la aplicación de tareas con `CLINIC_TIMEZONE = America/Argentina/Buenos_Aires`
- **THEN** su zona horaria es `America/Argentina/Buenos_Aires` y usa UTC internamente

#### Scenario: Sin tareas de negocio (borde)
- **WHEN** se listan las tareas registradas en la aplicación de tareas
- **THEN** no hay ninguna tarea propia del sistema fuera de `enviar_email` y `reencolar_pendientes` (la de recordatorios llega en C-12)

#### Scenario: Confirmación visible en Mailpit (esperado)
- **WHEN** con el entorno levantado y el seed cargado se agenda un turno futuro para un paciente del seed
- **THEN** en pocos segundos la interfaz de Mailpit en el puerto 8025 muestra el email de confirmación para ese paciente y la notificación queda `sent`

#### Scenario: Worker detenido (borde)
- **WHEN** el servicio `worker` está detenido y se agenda un turno
- **THEN** la API responde 201, la confirmación queda `pending` y, al volver a levantar el `worker`, el email sale sin intervención manual
