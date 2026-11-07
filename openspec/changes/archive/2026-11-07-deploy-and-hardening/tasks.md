# Tasks: deploy-and-hardening (C-13)

> **Gobernanza MEDIA.** El grupo 0 (confirmaciones P-1 a P-12 de `design.md`) quedó cerrado: todas confirmadas con la opción A. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso de entradas distintas (TRIANGULATE) y refactor con los tests en verde después de cada paso (REFACTOR). Antes de tocar un archivo existente se corren sus tests y se anota el número (safety net); si algo falla, se frena y se reporta como falla previa. Los tests de integración y el smoke test corren en el contenedor. Sin migraciones, endpoints ni dependencias de Python o npm nuevas; no leer ni editar `.env` (los secretos los completa el usuario en su `.env` local; nunca se piden por chat). `domain/` sin cambios. Emails solo a Mailpit; datos ficticios; ningún proveedor SMTP ni cuenta externa en ningún archivo. Todo cambio que toque la agenda conserva su test de no superposición (regla dura 6). Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`. Cada task indica **Verifica:** cómo se comprueba.

## 0. Confirmaciones del usuario

- [x] 0.1 Obtener respuesta a P-1 (preparación al iniciar), P-2 (modo demo) y P-3 (nginx y llegada a la API) y marcarlas CONFIRMADAS en `design.md`; si P-1 ≠ A, reescribir el requirement "Un comando levanta los siete servicios" de `local-environment` y D-1; si P-2 = B o C, ajustar "Modo demo con un comando" y D-2; si P-3 = B, quitar el origen 8080 de los escenarios de CORS y del ejemplo. **Verifica:** `design.md` sin "PENDIENTE" en P-1 a P-3
- [x] 0.2 Obtener respuesta a P-4 (registro de accesos), P-5 (forma del smoke test) y P-6 (mañana sin franjas); si P-4 = C, quitar la capability `access-logging` y el grupo 4; si P-5 = B, cambiar "no corre en la batería por defecto" por el comando del script; si P-6 ≠ A, ajustar el escenario "Mañana sin horario de atención". **Verifica:** `design.md` sin "PENDIENTE" en P-4 a P-6
- [x] 0.3 Obtener respuesta a P-7 (matriz), P-8 (bundle), P-9 (sesión y login) y P-10 (`.env.example`); si P-9 = B o C, sumar un requirement y un grupo para el límite de intentos (y la cookie); si P-10 = B, ajustar "Archivo de ejemplo completo y sin secretos". **Verifica:** `design.md` sin "PENDIENTE" en P-7 a P-10
- [x] 0.4 Obtener respuesta a P-11 (README y checklist) y P-12 (un change o dos); si P-12 = B, partir con `/opsx:update` en el punto de corte del grupo 5. **Verifica:** `design.md` sin "PENDIENTE" en P-11 y P-12
- [x] 0.5 Quitar las marcas "pendiente de confirmación (P-n)" de las specs y ajustar specs, design y tasks a las respuestas. **Verifica:** `openspec validate deploy-and-hardening --strict` en verde

## 1. Línea base

- [x] 1.1 Safety net general en el contenedor: `pytest`, `pytest -m integration`, `mypy --strict app/`, `ruff check .` y `ruff format --check .`; en `frontend`: `npm test`, `npm run typecheck` y `npm run lint`. Anotar los números (C-12 dejó 1548 por defecto, 331 de integración más 1 omitido y 380 de frontend). **Verifica:** todo en verde; si algo falla, frenar y reportarlo como falla previa
- [x] 1.2 `docker compose version` y anotar si soporta `!reset` (P-2). **Verifica:** versión anotada en el registro de la apply

## 2. CORS estricto — specs api-health y runtime-configuration

- [x] 2.1 Safety net: correr `tests/unit/api/test_health.py`, `tests/unit/core/test_config.py` y `tests/unit/test_env_example.py`. **Verifica:** en verde y número anotado
- [x] 2.2 RED: test de `Settings` con `CORS_ORIGINS = *` → falla y el error nombra `CORS_ORIGINS`; ver que falla. **Verifica:** el test falla porque hoy `*` se acepta
- [x] 2.3 GREEN: validador de `CORS_ORIGINS` en `app/core/config.py` que rechaza `*`. **Verifica:** test en verde
- [x] 2.4 TRIANGULATE: `http://localhost:5173,*` → falla; `localhost:5173` (sin esquema) → falla; `http://localhost:5173,http://localhost:8080` → dos orígenes; el error no repite el valor. **Verifica:** tests en verde
- [x] 2.5 RED: tests de preflight: `OPTIONS /api/v1/patients` con `Access-Control-Request-Method: PATCH` y encabezados `authorization, content-type` desde un origen permitido → 200 sin `Access-Control-Allow-Credentials: true`; con `x-otro-encabezado` → no se autoriza; ver que el segundo falla con la configuración actual (`allow_headers=["*"]`). **Verifica:** el test del encabezado no usado falla
- [x] 2.6 GREEN: `CORSMiddleware` en `app/main.py` con métodos y encabezados explícitos y `allow_credentials=False` (D-3). **Verifica:** tests de CORS nuevos y previos en verde
- [x] 2.7 TRIANGULATE: origen de la demo `http://localhost:8080` permitido cuando figura en `CORS_ORIGINS`; preflight desde `http://malicioso.example` sin `Access-Control-Allow-Origin`. **Verifica:** tests en verde
- [x] 2.8 REFACTOR: constantes con nombre para métodos y encabezados permitidos. **Verifica:** tests del grupo y de 2.1 en verde después de cada paso; `mypy --strict app/` y `ruff check .` limpios

## 3. Matriz única de permisos — spec access-control

- [x] 3.1 Safety net: correr `tests/unit/api/test_route_inventory.py` y los cuatro `*_permissions.py`. **Verifica:** en verde y número anotado
- [x] 3.2 RED: `tests/unit/api/test_permission_matrix.py` con la tabla de las 33 rutas (2 públicas) armada desde `03_actores_y_roles.md` y una fila de menos a propósito; el test de igualdad con el inventario falla nombrando la ruta faltante. **Verifica:** el test falla nombrando esa ruta
- [x] 3.3 GREEN: completar la tabla (D-4). **Verifica:** test de igualdad en verde
- [x] 3.4 TRIANGULATE: test con una fila de una ruta que no existe → falla nombrando la fila (función de comparación probada con conjuntos armados); 401 sin token en cada ruta protegida; 403 con cada rol no permitido (incluye recepción en `POST /api/v1/users` y odontólogo en `POST /api/v1/appointments`); ni 401 ni 403 con cada rol permitido (incluye admin y recepción en `GET /api/v1/patients?q=ruiz`); públicas sin 401 ni 403. **Verifica:** tests en verde; si alguna ruta real no coincide con la matriz de la KB, frenar y reportar la diferencia al usuario sin cambiar permisos
- [x] 3.5 REFACTOR: compartir con `test_route_inventory.py` las funciones `api_routes` y `route_keys` sin cambiar sus tests. **Verifica:** inventario, matriz y `*_permissions.py` en verde (número de 3.1 más los nuevos)

## 4. Registro de accesos sin consulta — spec access-logging

- [x] 4.1 Safety net: correr `tests/unit/api/` completo. **Verifica:** en verde y número anotado
- [x] 4.2 RED: `tests/unit/core/test_access_log_filter.py`: un registro con el formato de `uvicorn.access` para `GET /api/v1/patients?q=ruiz` 200, pasado por el filtro, produce un mensaje con `GET`, `/api/v1/patients` y `200` y sin `ruiz` ni `q=`; ver que falla. **Verifica:** el test falla por falta del módulo
- [x] 4.3 GREEN: `app/core/logging.py` con el filtro (D-5). **Verifica:** test en verde
- [x] 4.4 TRIANGULATE: búsqueda por documento (`q=40555666`); `GET /api/v1/appointments?professional_id=…&from=…&to=…`; ruta sin consulta (`/api/v1/health`) queda igual; respuesta 401 con consulta; un registro de otro logger no se modifica. **Verifica:** tests en verde
- [x] 4.5 RED → GREEN: `create_app()` instala el filtro en el logger `uvicorn.access` una sola vez (crear la app dos veces no duplica el filtro). **Verifica:** test en verde
- [x] 4.6 REFACTOR: docstring con referencia a DD-77. **Verifica:** tests del grupo y de 4.1 en verde; `mypy --strict app/` y `ruff check .` limpios

## 5. Ningún secreto en el bundle — spec runtime-configuration

- [x] 5.1 Safety net: correr `npm test` en `frontend` y anotar el número. **Verifica:** en verde
- [x] 5.2 RED: `frontend/src/env-usage.test.ts`: recorre `src/` (sin tests) y exige que la única variable de `import.meta.env` sea `VITE_API_URL`; con un archivo de prueba que lee `VITE_OTRA` (en una carpeta temporal) falla nombrando archivo y variable; ver que el caso de error falla antes de escribir la función. **Verifica:** el test falla por falta de la función de búsqueda
- [x] 5.3 GREEN: función pura de extracción de variables y el test sobre `src/`. **Verifica:** tests en verde
- [x] 5.4 RED: test de Vitest de `frontend/scripts/check-bundle.mjs` con una carpeta temporal que contiene `SMTP_PASSWORD` → devuelve el archivo y el texto; ver que falla. **Verifica:** el test falla por falta del script
- [x] 5.5 GREEN: `check-bundle.mjs` (D-7) y `"check:bundle"` en `package.json`. **Verifica:** test en verde
- [x] 5.6 TRIANGULATE: carpeta limpia → sin hallazgos; `postgresql+psycopg://` → hallazgo; `DATABASE_URL` en un `.map` → hallazgo; `npm run build && npm run check:bundle` sobre el código real → sin hallazgos. **Verifica:** tests en verde y comando real con código 0
- [x] 5.7 REFACTOR: lista de textos prohibidos en una constante exportada, compartida por el script y su test. **Verifica:** `npm test`, `npm run typecheck` y `npm run lint` en verde (número de 5.1 más los nuevos)
- [x] 5.8 **Punto de corte seguro (P-12)**: correr `pytest`, `mypy --strict app/`, `ruff check .`, `npm test`, `npm run typecheck` y `npm run lint`. **Verifica:** todo en verde

## 6. Migraciones y seed al iniciar — specs local-environment y runtime-configuration

- [x] 6.1 Safety net: correr `tests/unit/test_env_example.py` y `tests/integration/db/test_seed.py` (`-m integration`). **Verifica:** en verde y número anotado
- [x] 6.2 RED: en `test_env_example.py`, `SEED_DEMO_PASSWORD` declarada y vacía, y `CORS_ORIGINS` con `http://localhost:5173` y `http://localhost:8080` y sin `*`; ver que falla el de orígenes. **Verifica:** el test de orígenes falla
- [x] 6.3 GREEN: `.env.example` con `CORS_ORIGINS=http://localhost:5173,http://localhost:8080` y el comentario de `SEED_DEMO_PASSWORD` (completarla en el `.env` local con una contraseña propia, DD-40); sin valores secretos. **Verifica:** tests de 6.1 y 6.2 en verde; `git status` no muestra `.env`
- [x] 6.4 RED → GREEN: test de la configuración resuelta de Compose (`docker compose config` sobre `.env.example` copiado a una carpeta temporal, o lectura del YAML): existe `migrate` con `restart: "no"` y el comando de migración y seed; `api` y `worker` dependen de `migrate` con `service_completed_successfully`; `frontend` no recibe secretos. **Verifica:** test en verde
- [x] 6.5 GREEN: servicio `migrate` y `depends_on` en `docker-compose.yml` (D-1); `target: dev` del frontend. **Verifica:** `docker compose up` sobre un volumen nuevo: `migrate` termina con código 0, la API queda sana y el login del seed funciona sin comandos adicionales
- [x] 6.6 TRIANGULATE: segundo `docker compose up` sobre la misma base no duplica datos; con `SEED_DEMO_PASSWORD` vacía `migrate` falla nombrando la variable y `api` y `worker` no arrancan; con `JWT_SECRET_KEY` vacía `migrate` falla nombrándola. **Verifica:** `docker compose ps -a` y `docker compose logs migrate` muestran cada caso
- [x] 6.7 README: sección de setup actualizada (copiar `.env.example`, generar `JWT_SECRET_KEY`, elegir `SEED_DEMO_PASSWORD` en el `.env` local, `docker compose up`), sin los comandos manuales de migración y seed como paso obligatorio. **Verifica:** seguir la sección tal cual sobre un volumen nuevo levanta el sistema

## 7. Imagen del frontend y modo demo — spec demo-packaging

- [x] 7.1 Safety net: `npm test` y `docker compose build frontend`. **Verifica:** en verde y la imagen de desarrollo construye
- [x] 7.2 `frontend/Dockerfile` con etapas `dev`, `build` y `demo`, `frontend/nginx.conf` y `frontend/.dockerignore` (D-2). **Verifica:** `docker build --target demo --build-arg VITE_API_URL=http://localhost:8000/api/v1 frontend` termina bien y `docker build --target demo frontend` (sin la URL) falla mencionando `VITE_API_URL`
- [x] 7.3 `docker-compose.demo.yml` (D-2): frontend `target: demo` en el 8080, `api` sin `--reload` y sin montar `./backend` (con `!reset`, o archivo completo si 1.2 dio que no se soporta). **Verifica:** `docker compose -f docker-compose.yml -f docker-compose.demo.yml config` muestra el comando de `api` sin `--reload`, sin el montaje y el frontend en `8080:80`
- [x] 7.4 Comprobar la demo levantada con `curl`: `GET /` y `GET /pacientes` → 200 con `index.html`; `GET /assets/no-existe.js` → 404; la imagen no tiene `src/`, `node_modules/` ni `package.json` (`docker compose run --rm --entrypoint ls frontend /usr/share/nginx/html` y `/`). **Verifica:** respuestas y listado esperados
- [x] 7.5 Regla de secretos: `docker compose -f docker-compose.yml -f docker-compose.demo.yml config` no muestra `JWT_SECRET_KEY`, `SMTP_PASSWORD`, `DATABASE_URL`, `POSTGRES_PASSWORD` ni `SEED_DEMO_PASSWORD` en el servicio `frontend`. **Verifica:** salida revisada
- [x] 7.6 Prueba en el navegador de la demo (http://localhost:8080): login de la recepcionista del seed, "API disponible", agendar un turno y ver la confirmación en Mailpit (http://localhost:8025). **Verifica:** confirmación visible en Mailpit
- [x] 7.7 README: sección "Modo demo" con el comando, URLs (8080, 8000, 8025), el aviso de agregar `http://localhost:8080` a `CORS_ORIGINS` y cómo volver al modo desarrollo. **Verifica:** relectura contra lo comprobado en 7.3 a 7.6

## 8. Smoke test de punta a punta — spec end-to-end-smoke

- [x] 8.1 Safety net: correr `pytest` y `pytest -m integration` y confirmar que el marcador nuevo no cambia esos números. **Verifica:** mismos números que en 1.1
- [x] 8.2 RED: marcador `smoke` en `pyproject.toml` y `addopts` con `not integration and not smoke`; `backend/tests/smoke/test_end_to_end.py` con el paso 1 (login por rol y `GET /auth/me`) y el chequeo previo de `SEED_DEMO_PASSWORD` y de que API y Mailpit responden; correrlo con el entorno detenido y ver que falla nombrando el servicio. **Verifica:** `docker compose run --rm api pytest -m smoke` falla nombrando la API o Mailpit
- [x] 8.3 GREEN: con el entorno levantado el paso 1 pasa. **Verifica:** `docker compose exec api pytest -m smoke` en verde
- [x] 8.4 RED → GREEN: pasos 2 y 3 (turno A en una franja libre de mañana, `SLOT_TAKEN` con el otro paciente del test, 403 del odontólogo, confirmación en Mailpit) con dos pacientes propios creados por la recepcionista. **Verifica:** test en verde
- [x] 8.5 RED → GREEN: pasos 4 y 5 (cancelar A con motivo y franja libre de nuevo; agendar B, reprogramar B y confirmación del nuevo horario). **Verifica:** test en verde
- [x] 8.6 RED → GREEN: paso 6 (pasada forzada con `send_task` al `worker`; un solo recordatorio, el de B con el horario nuevo; segunda pasada sin mensajes nuevos). **Verifica:** test en verde
- [x] 8.7 TRIANGULATE: mañana sin tramos (P-6): con un reloj de referencia de viernes o con un profesional sin tramo para mañana, el test agrega el tramo y al final los tramos quedan iguales a los originales; limpieza en `finally` aun con un paso que falla (provocar una falla y revisar que pacientes y turnos quedaron desactivados y cancelados); búsqueda en `EMAIL_REDIRECT_TO` cuando tiene valor. **Verifica:** tests en verde y datos revisados por la API
- [x] 8.8 REFACTOR: helpers de Mailpit y de franjas compartidos con los tests de integración de C-11/C-12 sin cambiar esos tests. **Verifica:** `pytest -m smoke` y `pytest -m integration` en verde después de cada paso
- [x] 8.9 Regla dura 6: el paso 2 confirma `SLOT_TAKEN`; correr `tests/integration/db/test_appointment_exclusion.py`. **Verifica:** en verde y sin cambios
- [x] 8.10 Correr el smoke test también contra el modo demo. **Verifica:** `docker compose -f docker-compose.yml -f docker-compose.demo.yml exec api pytest -m smoke` en verde
- [x] 8.11 README: sección "Smoke test" con el comando, qué recorre, qué datos deja y el comando de la pasada forzada de C-12. **Verifica:** relectura; el comando documentado es el que corrió en 8.6 y 8.10

## 9. README completo y checklist de adopción — P-11

- [x] 9.1 Reescribir `README.md` (D-8): qué es, requisitos (Docker Desktop), setup, comandos de desarrollo y demo, servicios y URLs, tabla de variables sin valores (cuáles son sensibles y que viven solo en el `.env` local), chequeos (pytest, integración, smoke, mypy, ruff, Vitest, typecheck, lint), estado de los changes y decisiones abiertas (SU-01 zona, SU-02 SMTP de producción, P-9 sesión y login, R-10 revisión legal antes de datos reales); quitar lo desactualizado (tabla de carpetas y "El change implementado" del primer change). Sin nombres de proveedores de email ni cuentas reales. **Verifica:** relectura; cada comando del README corrió en los grupos 6 a 8
- [x] 9.2 `docs/adopcion-recepcion.md` (D-8) enlazado desde el README: preparación, semana en paralelo con la planilla, criterio para dejar la planilla (métrica de `01_vision_y_objetivos.md`), qué hacer si la API no responde, preguntas abiertas para el dueño (adopción, `10_preguntas_abiertas.md`). **Verifica:** relectura contra R-8 y la métrica de éxito; el enlace del README abre el archivo

## 10. KB, roadmap y documentación de agentes

- [x] 10.1 Registrar P-1 a P-12 confirmadas como DD-104 en adelante en `knowledge-base/09_decisiones_y_supuestos.md`; actualizar DD-40 (contraseña propia del seed en el `.env` local), DD-46 y DD-47 (resultado de P-9), DD-77 (registro sin consulta); SU-02 sigue abierto solo para producción. **Verifica:** los códigos citados existen y no repiten números
- [x] 10.2 `knowledge-base/08_arquitectura_propuesta.md` (§Seguridad: CORS con métodos y encabezados, matriz de permisos, registro sin consulta, bundle sin secretos; §Variables de entorno: `CORS_ORIGINS` con el 8080, `SEED_DEMO_PASSWORD`; estructura de directorios con `docker-compose.demo.yml` y `nginx.conf`); `11_recordatorios_email.md` §Límites y riesgos (smoke test con Mailpit, modo demo); `10_preguntas_abiertas.md` (adopción y sesión/login como pendientes antes de datos reales). **Verifica:** relectura de cada sección contra las specs
- [x] 10.3 `CHANGES.md`: entrada C-13 con estado, tests, specs nuevas y modificadas, decisiones; riesgos R-1, R-6, R-8 y R-10 con su mitigación actualizada; tabla resumen y "siguientes changes" (roadmap completo). `CLAUDE.md` y `AGENTS.md`: roadmap con C-13 archivado y la fila de Docker Compose (desarrollo y demo); ambos archivos idénticos. **Verifica:** relectura; `diff CLAUDE.md AGENTS.md` vacío; `git status` no muestra `.env`

## 11. Verificación final

- [x] 11.1 En el contenedor: `pytest`, `pytest -m integration`, `pytest -m smoke` (con el entorno levantado), `mypy --strict app/`, `ruff check .` y `ruff format --check .`; en `frontend`: `npm test`, `npm run typecheck`, `npm run lint`, `npm run build` y `npm run check:bundle`; comparar con la línea base del grupo 1. **Verifica:** todo en verde y ningún test previo perdido
- [x] 11.2 `docker compose up` (desarrollo) y el comando del modo demo sobre volúmenes nuevos levantan sin pasos manuales. **Verifica:** API sana, frontend en 5173 y 8080 respectivamente, Mailpit en 8025
- [x] 11.3 `openspec validate deploy-and-hardening --strict`. **Verifica:** en verde
