# demo-packaging Specification

## Purpose
Empaquetar el sistema para una demo local con un solo comando: el frontend construido y servido como archivos estáticos con la URL de la API fijada al construir, la API sin recarga de código y Mailpit como único servidor SMTP, sin cuentas ni servicios externos.

## Requirements

### Requirement: Imagen del frontend con etapas de desarrollo y de demo

La imagen del frontend SHALL tener una etapa de desarrollo, que sirve la SPA con el servidor de Vite y recarga en caliente (la que usa `docker compose up`), y una etapa de demo, que construye la SPA con `VITE_API_URL` recibida como argumento del build y la sirve como archivos estáticos con nginx. En la etapa de demo, cualquier ruta de la SPA que no sea un archivo existente (por ejemplo `/agenda` o `/pacientes`) MUST responder con `index.html`, y un archivo inexistente con extensión (por ejemplo `/assets/no-existe.js`) MUST responder 404. La imagen de demo MUST NOT contener el código fuente, `node_modules` ni herramientas de build; solo los archivos construidos y la configuración del servidor web. Si `VITE_API_URL` falta o está vacía, el build de la demo MUST fallar con un mensaje que la nombra.

#### Scenario: Página de inicio servida (esperado)
- **WHEN** el modo demo está levantado y se pide `GET http://localhost:8080/`
- **THEN** la respuesta es 200 con el `index.html` de la SPA construida

#### Scenario: Ruta de la SPA al recargar (borde)
- **WHEN** se pide `GET http://localhost:8080/pacientes` directamente, sin pasar por `/`
- **THEN** la respuesta es 200 con el mismo `index.html`

#### Scenario: Archivo estático inexistente (error)
- **WHEN** se pide `GET http://localhost:8080/assets/no-existe.js`
- **THEN** la respuesta es 404

#### Scenario: URL de la API fijada al construir (esperado)
- **WHEN** la imagen de demo se construye con `VITE_API_URL = http://localhost:8000/api/v1`
- **THEN** la pantalla de login consulta `http://localhost:8000/api/v1/health` y muestra "API disponible" con la API levantada

#### Scenario: Build sin URL de la API (error)
- **WHEN** se construye la imagen de demo sin `VITE_API_URL`
- **THEN** el build falla con un mensaje que menciona `VITE_API_URL`

#### Scenario: Imagen de demo sin código fuente (borde)
- **WHEN** se lista el contenido de la imagen de demo
- **THEN** no contiene `src/`, `node_modules/` ni `package.json`

### Requirement: Modo demo con un comando

El repositorio SHALL ofrecer un comando documentado que levanta el modo demo sobre la misma definición de servicios del entorno de desarrollo: `db`, `redis`, la preparación (migraciones y seed), `api`, `worker`, `beat`, `frontend` con la etapa de demo y `mailpit`. En modo demo la API MUST correr sin recarga automática y sin montar el código del anfitrión, y el frontend MUST publicarse en el puerto 8080 del anfitrión. Los emails MUST ir a Mailpit (http://localhost:8025): el modo demo MUST NOT requerir ni declarar ningún servidor SMTP externo, cuenta o servicio fuera de los contenedores. Los secretos MUST salir solo del `.env` local.

#### Scenario: Levantar la demo (esperado)
- **WHEN** existe un `.env` válido y se ejecuta el comando documentado del modo demo
- **THEN** la preparación termina bien, `api` responde `GET http://localhost:8000/api/v1/health` con 200, el frontend responde en http://localhost:8080 y Mailpit en http://localhost:8025

#### Scenario: Agendar desde la demo envía la confirmación a Mailpit (esperado)
- **WHEN** en la demo la recepcionista del seed agenda un turno futuro para un paciente del seed desde el navegador
- **THEN** la confirmación aparece en la interfaz de Mailpit y ningún email sale de los contenedores

#### Scenario: API sin recarga ni código montado (borde)
- **WHEN** se inspecciona la configuración resuelta del servicio `api` en modo demo
- **THEN** su comando no incluye `--reload` y no monta el directorio `backend` del anfitrión

#### Scenario: Desarrollo no cambia (borde)
- **WHEN** se ejecuta `docker compose up` sin el archivo del modo demo
- **THEN** el frontend corre con el servidor de Vite en el puerto 5173 y la API con recarga automática, como antes

#### Scenario: Origen de la demo fuera de CORS (error)
- **WHEN** el `.env` local tiene `CORS_ORIGINS = http://localhost:5173` y se usa la demo en http://localhost:8080
- **THEN** el navegador bloquea las respuestas de la API y la pantalla de login muestra "API no disponible"; el README indica agregar `http://localhost:8080` a `CORS_ORIGINS`
