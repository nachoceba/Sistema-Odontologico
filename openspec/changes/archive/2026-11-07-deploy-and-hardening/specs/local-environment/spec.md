# Spec Delta

## MODIFIED Requirements

### Requirement: Un comando levanta los siete servicios

Con un `.env` válido en la raíz, `docker compose up` SHALL levantar los servicios `db` (PostgreSQL), `redis`, `api`, `worker`, `beat`, `frontend` y `mailpit`. Antes de que arranquen `api` y `worker`, el mismo comando MUST aplicar todas las migraciones pendientes y el seed ficticio de `seed-data` en un paso de preparación de una sola vez, que termina y no queda en ejecución. Si la preparación falla, `api` y `worker` MUST NOT arrancar. La API MUST arrancar solo después de que `db` y `redis` estén sanos y la preparación haya terminado bien. Desde la máquina anfitriona MUST quedar accesibles la API en el puerto 8000, el frontend en el 5173 y la interfaz web de Mailpit en el 8025.

#### Scenario: Levantar todo (esperado)
- **WHEN** existe un `.env` copiado de `.env.example` con `JWT_SECRET_KEY` y `SEED_DEMO_PASSWORD` completadas y se ejecuta `docker compose up`
- **THEN** la preparación termina con código 0, los siete servicios quedan en ejecución, `db`, `redis` y `api` se informan sanos y `GET http://localhost:8000/api/v1/health` responde 200

#### Scenario: Base vacía lista para usar (esperado)
- **WHEN** se ejecuta `docker compose up` sobre un volumen de base nuevo
- **THEN** al quedar sana la API la base tiene todas las migraciones aplicadas y los datos del seed, y las cuentas del seed pueden iniciar sesión sin ningún comando adicional

#### Scenario: Volver a levantar no duplica datos (borde)
- **WHEN** se ejecuta `docker compose up` por segunda vez sobre la misma base, con cambios hechos desde la interfaz
- **THEN** la preparación termina bien, no aplica migraciones repetidas, no duplica usuarios, profesionales ni pacientes y no pisa los cambios hechos

#### Scenario: Falta la contraseña del seed (error)
- **WHEN** el `.env` tiene `SEED_DEMO_PASSWORD` vacía y se ejecuta `docker compose up`
- **THEN** la preparación termina con error y su log menciona `SEED_DEMO_PASSWORD`; `api` y `worker` no arrancan

#### Scenario: Falta el archivo `.env` (error)
- **WHEN** no existe `.env` en la raíz y se ejecuta `docker compose up`
- **THEN** el comando falla antes de crear contenedores con un mensaje que menciona el archivo `.env`

#### Scenario: Configuración inválida detiene la API (error)
- **WHEN** el `.env` tiene `JWT_SECRET_KEY` vacía y se ejecuta `docker compose up`
- **THEN** la preparación termina con error y su log muestra el error de validación y menciona `JWT_SECRET_KEY` (las migraciones leen la misma configuración validada); `api` y `worker` no arrancan y `beat` termina con error y menciona `JWT_SECRET_KEY`

#### Scenario: Base y Redis no expuestos al anfitrión (borde)
- **WHEN** el entorno está levantado
- **THEN** PostgreSQL y Redis no publican puertos en la máquina anfitriona y solo son alcanzables desde los demás contenedores
