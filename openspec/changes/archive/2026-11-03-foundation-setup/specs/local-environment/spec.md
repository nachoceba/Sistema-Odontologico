# Spec Delta: local-environment

## Purpose

Levantar todo el sistema en desarrollo con un solo comando, en contenedores con versiones fijas de Python y Node, para que cualquier integrante (o la cátedra) pueda correrlo y probarlo sin instalar PostgreSQL, Redis ni Python 3.12 en su máquina.

## ADDED Requirements

> Pendiente de confirmar (P-1 del design): los servicios `worker` y `beat` usan Celery (DD-10), sujeto a la aceptación de la cátedra.

### Requirement: Un comando levanta los siete servicios

Con un `.env` válido en la raíz, `docker compose up` SHALL levantar los servicios `db` (PostgreSQL), `redis`, `api`, `worker`, `beat`, `frontend` y `mailpit`. La API MUST arrancar solo después de que `db` y `redis` estén sanos. Desde la máquina anfitriona MUST quedar accesibles la API en el puerto 8000, el frontend en el 5173 y la interfaz web de Mailpit en el 8025.

#### Scenario: Levantar todo (esperado)
- **WHEN** existe un `.env` copiado de `.env.example` con `JWT_SECRET_KEY` completada y se ejecuta `docker compose up`
- **THEN** los siete servicios quedan en ejecución, `db`, `redis` y `api` se informan sanos y `GET http://localhost:8000/api/v1/health` responde 200

#### Scenario: Falta el archivo `.env` (error)
- **WHEN** no existe `.env` en la raíz y se ejecuta `docker compose up`
- **THEN** el comando falla antes de crear contenedores con un mensaje que menciona el archivo `.env`

#### Scenario: Configuración inválida detiene la API (error)
- **WHEN** el `.env` tiene `JWT_SECRET_KEY` vacía y se ejecuta `docker compose up`
- **THEN** el log del servicio `api` muestra el error de validación y menciona `JWT_SECRET_KEY`, y el servicio nunca pasa a `healthy`; `worker` y `beat` terminan con error y mencionan `JWT_SECRET_KEY` (en desarrollo `uvicorn --reload` mantiene vivo el proceso vigilante de cambios, por eso el contenedor `api` no termina)

#### Scenario: Base y Redis no expuestos al anfitrión (borde)
- **WHEN** el entorno está levantado
- **THEN** PostgreSQL y Redis no publican puertos en la máquina anfitriona y solo son alcanzables desde los demás contenedores

### Requirement: Worker y beat con la zona del consultorio

Los servicios `worker` y `beat` SHALL arrancar conectados a Redis como broker, con la zona horaria de la programación igual a `CLINIC_TIMEZONE` y con los instantes internos en UTC. En este change MUST NOT haber tareas de negocio registradas.

#### Scenario: Worker conectado
- **WHEN** el entorno está levantado
- **THEN** el log de `worker` indica que está listo y conectado al broker en `redis`

#### Scenario: Zona de la programación (esperado)
- **WHEN** se inspecciona la configuración de la aplicación de tareas con `CLINIC_TIMEZONE = America/Argentina/Buenos_Aires`
- **THEN** su zona horaria es `America/Argentina/Buenos_Aires` y usa UTC internamente

#### Scenario: Sin tareas de negocio (borde)
- **WHEN** se listan las tareas registradas en la aplicación de tareas
- **THEN** no hay ninguna tarea propia del sistema (solo las internas de la herramienta)

### Requirement: Tests del backend en Python 3.12 dentro del contenedor

La imagen del backend SHALL usar Python 3.12 y MUST permitir correr la batería completa de tests del backend con un único comando documentado, sin instalar Python en el anfitrión. Los tests marcados como de integración MUST NOT correr por defecto.

#### Scenario: Tests en el contenedor (esperado)
- **WHEN** se ejecuta el comando documentado para correr los tests del backend en el contenedor
- **THEN** corre con Python 3.12 y todos los tests no marcados como de integración pasan

#### Scenario: Integración solo a pedido (borde)
- **WHEN** se corre la batería por defecto
- **THEN** los tests marcados como de integración no se ejecutan; se ejecutan solo al pedirlos explícitamente
