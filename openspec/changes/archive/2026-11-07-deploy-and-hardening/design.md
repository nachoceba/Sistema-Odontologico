# Design: deploy-and-hardening (C-13)

> **Gobernanza MEDIA.** Las decisiones P-1 a P-12 están **CONFIRMADAS por el usuario** (todas la opción A, la recomendada) y se registran como DD-104 a DD-115 (P-n = DD-(103+n)) en `knowledge-base/09_decisiones_y_supuestos.md`.

## Context

Motivación en `proposal.md`. Estado real del repositorio (revisado el 2026-11-06):

- **Docker Compose** (`docker-compose.yml`): siete servicios; `api`, `worker` y `beat` comparten la imagen de desarrollo del backend (`pip install -e ".[dev]"`, montaje `./backend:/app`, `uvicorn --reload`). `db` y `redis` no publican puertos. `frontend` usa `node:22-alpine` con `npm run dev` en el 5173 y recibe solo `VITE_API_URL`. Migraciones y seed se corren a mano (`docker compose exec api alembic upgrade head` y `python -m scripts.seed`, README).
- **Migraciones y seed**: `alembic/env.py` toma la URL de `get_settings()` (valida toda la configuración, incluida `JWT_SECRET_KEY`). `scripts/seed.py` es idempotente, exige `SEED_DEMO_PASSWORD` y `CLINIC_TIMEZONE`, verifica que la base esté migrada y termina con código distinto de 0 si falta algo (DD-40).
- **Backend**: `backend/Dockerfile` dice que "C-13 define una imagen de producción sin extras de dev". `app/main.py` configura `CORSMiddleware` con `allow_origins=settings.CORS_ORIGINS` y `allow_methods=["*"]`, `allow_headers=["*"]`. `CORS_ORIGINS` acepta cualquier cadena (incluso `*`).
- **Permisos**: `tests/unit/api/test_route_inventory.py` ya comprueba que toda ruta fuera de la lista pública depende de `current_user` y responde 401 sin token, y que no hay rutas de notificaciones o tareas. Hay tests de permisos por recurso (`test_users_permissions.py`, `test_patients_permissions.py`, `test_professionals_permissions.py`, `test_appointments_permissions.py`). Son 33 rutas (2 públicas). No existe una tabla única ruta × rol.
- **Frontend**: solo `src/config.ts` lee `import.meta.env.VITE_API_URL`; el token vive en `sessionStorage` (DD-46). `package.json` no tiene Playwright ni otra herramienta de navegador. `npm run build` = `tsc -b && vite build`.
- **Configuración**: `tests/unit/test_env_example.py` compara las variables de `Settings` con `.env.example`, exige secretos vacíos y una sola variable `VITE_`. `.env.example` trae credenciales de base ficticias de desarrollo (`odonto_dev`) y `SEED_DEMO_PASSWORD` vacía.
- **Registros**: uvicorn escribe la línea de acceso con la dirección completa, incluida la consulta (`?q=…` de la búsqueda de pacientes, DD-77).
- **Smoke previo**: `tests/integration/test_smoke.py` es un humo de la base de pruebas (no del flujo). `tests/integration/test_reminders_end_to_end.py` y `test_confirmation_end_to_end.py` ya consultan la API HTTP de Mailpit (`http://mailpit:8025/api/v1`) desde el contenedor, sobre la base `_test` y una cola propia.
- **Pendientes anotados para C-13**: DD-40 (contraseña del seed en una demo), DD-46 (cookie httpOnly), DD-47 (límite de intentos de login), DD-77 (registro de accesos), SU-02 (SMTP de producción, abierto), R-8 (adopción) y R-10 (revisión legal antes de datos reales).
- **Context7** (`/websites/docker_compose`, 2026-11-06): el patrón de servicio de una sola vez con `depends_on: condition: service_completed_successfully` sigue vigente y se recomienda cuando varios servicios dependen del mismo paso; `pre_start` es más nuevo y corre por servicio. Los archivos de Compose se combinan en el orden de `-f`; las listas como `ports` se concatenan, por eso el override de la demo necesita `!reset` para quitar montajes y puertos (verificar la versión de Compose instalada al aplicar).

## Goals / Non-Goals

**Goals:**
- Un comando para desarrollo y otro para la demo, sin pasos manuales de base de datos.
- Que una ruta nueva sin permisos declarados, un secreto en el bundle o un CORS abierto hagan fallar un test o el build.
- Un smoke test repetible que recorra el flujo completo con los tres roles y Mailpit.
- Documentación suficiente para que otra persona levante y pruebe el sistema, y un checklist de adopción para recepción.

**Non-Goals:**
- Despliegue en la nube, dominio, HTTPS, proveedor SMTP real o cualquier cuenta externa.
- Imagen de backend de producción separada, refresh token, cookie httpOnly, límite de intentos (ver P-2 y P-9).
- Cambios en reglas de agenda, esquema, endpoints o pantallas.

## Decisiones confirmadas (P-1 a P-12)

Cada pregunta en lenguaje simple, con opciones. **Todas CONFIRMADAS con la opción A.**

### P-1 — ¿Cómo se aplican migraciones y seed al levantar? — CONFIRMADA: A (DD-104)
- **A (recomendada)**: un servicio de preparación `migrate` de una sola vez (misma imagen del backend) que corre `alembic upgrade head` y después `python -m scripts.seed`; `api` y `worker` esperan a que termine bien (`service_completed_successfully`). Si falta `SEED_DEMO_PASSWORD`, falla y nada arranca.
- B: un script de arranque dentro de `api` que migra y siembra antes de `uvicorn` (el `worker` puede arrancar antes de que termine; se repite en cada reinicio de `api`).
- C: dejarlo manual y documentado como hoy.
**Por qué A**: un solo lugar, corre una vez por `up`, el seed ya es idempotente y el error queda en un log propio. B mezcla preparación con servir pedidos; C no cumple "aplicados al iniciar".

### P-2 — ¿Cómo se arma el modo demo? — CONFIRMADA: A (DD-105)
- **A (recomendada)**: un archivo `docker-compose.demo.yml` que se suma al de desarrollo (`docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build`): frontend con la etapa nginx en el 8080, `api` sin `--reload` y sin montar el código (con `!reset`), misma imagen de backend. Desarrollo queda igual.
- B: un archivo de Compose completo y separado para la demo (duplica la definición de los siete servicios).
- C: un solo archivo con perfiles (`--profile demo`) y dos servicios de frontend.
**Por qué A**: no duplica servicios y deja el desarrollo intacto. Una imagen de backend sin extras de desarrollo (multi-stage) queda como mejora posterior: la demo es local y la imagen actual funciona. Compose v5.6.1 (verificado al aplicar) soporta `!reset`.

### P-3 — ¿Cómo sirve el frontend la demo y cómo llega a la API? — CONFIRMADA: A (DD-106)
- **A (recomendada)**: nginx sirve solo los archivos estáticos (con vuelta a `index.html`); el navegador llama a la API directo en `http://localhost:8000/api/v1` (fijada con el build-arg `VITE_API_URL`) y CORS permite `http://localhost:8080`.
- B: nginx también hace de proxy de `/api/` a la API (mismo origen, sin CORS); `VITE_API_URL=/api/v1`.
- C: `vite preview` dentro del contenedor, sin nginx.
**Por qué A**: misma forma de llamar a la API que en desarrollo y el CORS ya está probado. B suma configuración de proxy y hace pasar la búsqueda `q` también por el registro de nginx; C usa una herramienta que Vite no recomienda para servir.

### P-4 — ¿Qué se hace con el registro de accesos que guarda `?q=…` (DD-77)? — CONFIRMADA: A (DD-107)
- **A (recomendada)**: un filtro de registros en la API que quita la parte de consulta de cada línea de acceso (se ven método, ruta y código), en desarrollo y en la demo.
- B: apagar el registro de accesos de uvicorn (`--no-access-log`).
- C: dejarlo así y documentarlo (los datos son ficticios).
**Por qué A**: conserva lo útil para diagnosticar y saca el dato del paciente; B deja sin registro; C posterga un riesgo ya anotado para C-13. Con P-3 = A, nginx no ve las búsquedas (solo sirve archivos).

### P-5 — ¿Cómo se automatiza el smoke test? — CONFIRMADA: A (DD-108)
- **A (recomendada)**: un test de pytest con marcador propio `smoke` (fuera de la batería por defecto y de `-m integration`), que corre dentro del contenedor `api` contra la API levantada (`http://api:8000`) y la API HTTP de Mailpit, y pide la pasada forzada al `worker` real por la cola: `docker compose exec api pytest -m smoke`.
- B: un script de Python en `backend/scripts/smoke.py` que imprime cada paso.
- C: Playwright con navegador (no está en el repositorio: suma dependencia y Chromium).
**Por qué A**: reusa pytest, `httpx` y el patrón de Mailpit de los tests de C-11/C-12, da un resultado claro por paso y no agrega dependencias. C se descarta por complejidad.

### P-6 — Si mañana no hay franjas (viernes y sábado con el seed de lunes a viernes), ¿qué hace el smoke test? — CONFIRMADA: A (DD-109)
El recordatorio solo sale para turnos de mañana, y el seed no tiene tramos en sábado ni domingo.
- **A (recomendada)**: el test, como administrador, agrega a un profesional un tramo para el día de la semana de mañana (con `PUT /working-hours`) y al terminar le devuelve exactamente sus tramos originales.
- B: el paso del recordatorio se saltea con un aviso cuando mañana no hay franjas.
- C: documentar que el smoke test se corre de domingo a jueves.
**Por qué A**: el test pasa completo cualquier día y usa la API como un usuario real; B y C dejan días en que el flujo no se verifica entero.

### P-7 — ¿Qué alcance tiene la matriz de permisos? — CONFIRMADA: A (DD-110)
- **A (recomendada)**: una tabla única ruta × rol en un test, que debe ser igual al inventario de rutas; para cada ruta protegida comprueba 401 sin token, 403 con cada rol no permitido y "ni 401 ni 403" con cada rol permitido. Los tests por recurso (incluido el alcance "propio" del odontólogo) quedan como están.
- B: solo un chequeo de que cada ruta aparece en algún archivo `*_permissions.py`.
- C: A más la regla "propio" en la misma tabla.
**Por qué A**: una sola fuente que no deja pasar una ruta sin declarar; B es frágil (busca texto); C duplica lo que ya prueban los tests por recurso.

### P-8 — ¿Cómo se comprueba que ningún secreto llega al bundle? — CONFIRMADA: A (DD-111)
- **A (recomendada)**: dos chequeos: un test de Vitest que revisa que el código solo lee `import.meta.env.VITE_API_URL`, y un script `npm run check:bundle` que busca en `dist/` nombres y patrones de secretos; el script corre en la etapa de build de la imagen de la demo y la hace fallar.
- B: solo el test de Vitest sobre el código.
- C: un test de pytest que lee `frontend/dist`.
**Por qué A**: el test detecta el error antes del build y el script cubre lo que realmente se publica; C mezcla backend y frontend y depende de un build previo.

### P-9 — ¿Se endurece la sesión (DD-46) y el login (DD-47) en C-13? — CONFIRMADA: A (DD-112)
- **A (recomendada)**: no. Se mantienen el token en `sessionStorage` y el login sin límite de intentos; se documentan como decisiones abiertas antes de usar datos reales.
- B: límite simple de intentos fallidos por email con Redis (429 tras N fallos en M minutos).
- C: B más cookie httpOnly (cambia CORS, suma CSRF).
**Por qué A**: la demo es local con datos ficticios y argon2 ya hace lento cada intento; B y C suman lógica y casos de error que el alcance no necesita.

### P-10 — ¿Qué valores quedan en `.env.example`? — CONFIRMADA: A (DD-113)
- **A (recomendada)**: se mantienen las credenciales de base ficticias de desarrollo (permiten levantar sin pensar); `JWT_SECRET_KEY`, `SMTP_PASSWORD` y `SEED_DEMO_PASSWORD` vacías; `CORS_ORIGINS` con el 5173 y el 8080. El README pide cambiar en el `.env` local la contraseña de la base y elegir una `SEED_DEMO_PASSWORD` propia (DD-40).
- B: dejar vacías también las credenciales de base.
**Por qué A**: es lo que ya permite la spec y no complica el primer arranque; los valores reales viven solo en el `.env` local, que los agentes no leen ni commitean.

### P-11 — ¿Dónde van el README y el checklist de adopción? — CONFIRMADA: A (DD-114)
- **A (recomendada)**: README reescrito (qué es, requisitos, setup, comandos de desarrollo y demo, servicios y URLs, variables sin valores, chequeos, smoke test, decisiones abiertas) y el checklist de adopción en `docs/adopcion-recepcion.md`, enlazado desde el README.
- B: todo en el README.
**Por qué A**: el README queda corto y técnico; el checklist es para la recepción y el dueño, no para quien levanta el entorno.

### P-12 — ¿Un change o dos? — CONFIRMADA: A (DD-115)
- **A (recomendada)**: un solo change por grupos, con un punto de corte seguro tras el grupo 5 (endurecimiento terminado: CORS, matriz, registros y bundle, sin tocar Compose).
- B: partir en C-13a (endurecimiento) y C-13b (empaquetado, smoke test y documentación).
**Por qué A**: son pocas tareas por grupo y la documentación final cierra todo junto; el punto de corte permite parar sin dejar nada a medias (igual que DD-93 y DD-102).

## Decisiones técnicas

### D-1 — Preparación al iniciar (P-1 = A)
Servicio `migrate` en `docker-compose.yml` con la misma imagen y `env_file` que el backend, `restart: "no"`, `command: ["sh", "-c", "alembic upgrade head && python -m scripts.seed"]`, `depends_on: db (service_healthy)`. `api` y `worker` suman `migrate: condition: service_completed_successfully`; `beat` no lo necesita (no usa la base). Al no cambiar `seed.py`, su mensaje "Falta la variable de entorno SEED_DEMO_PASSWORD" ya cumple el escenario de error.

### D-2 — Imagen del frontend (P-3 = A)
`frontend/Dockerfile` con tres etapas: `dev` (la actual), `build` (`ARG VITE_API_URL`, falla si está vacía, `npm ci`, `npm run build`, `npm run check:bundle`) y `demo` (`nginx:alpine`, copia `dist/` y `nginx.conf`). `nginx.conf`: `try_files $uri $uri/ /index.html` para rutas sin extensión y 404 para archivos con extensión inexistentes. `docker-compose.yml` fija `target: dev`; el override de la demo usa `target: demo`, `args: VITE_API_URL` y `ports: !reset ["8080:80"]`. Se agrega `frontend/.dockerignore` (`node_modules`, `dist`).

### D-3 — CORS
`allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"]`, `allow_headers=["Authorization","Content-Type"]`, `allow_credentials=False`. Validador de `CORS_ORIGINS` en `Settings`: cada elemento distinto de `*` y con esquema `http://` o `https://`; el error nombra la variable (`hide_input_in_errors` ya evita repetir el valor).

### D-4 — Matriz de permisos (P-7 = A)
`tests/unit/api/test_permission_matrix.py` con `MATRIX: dict[tuple[str, str], frozenset[Role] | None]` (`None` = pública), armada a mano desde `03_actores_y_roles.md` y los routers actuales. Reusa `api_routes`/`route_keys` del inventario y los usuarios de `tests/unit/api/conftest.py`. Para "ni 401 ni 403" con roles permitidos se usan ids de ejemplo; un 404 o 422 cuenta como "pasó el chequeo de rol" (el orden de dependencias es sesión → rol → cuerpo). El inventario existente no cambia.

### D-5 — Registro de accesos (P-4 = A)
`app/core/logging.py` con un `logging.Filter` que reescribe el argumento de dirección de las líneas del logger `uvicorn.access` quitando desde `?`; se instala en `create_app()` (uvicorn ya configuró sus loggers al importar la app, también con `--reload`). Test con `caplog` y `TestClient` no alcanza (el `TestClient` no usa el logger de uvicorn): se prueba el filtro con registros armados con el mismo formato de uvicorn y, en la verificación del grupo, con `docker compose logs api`.

### D-6 — Smoke test (P-5 = A, P-6 = A)
`backend/tests/smoke/test_end_to_end.py` con marcador `smoke` declarado en `pyproject.toml` y `addopts = "-m 'not integration and not smoke'"`. Usa `httpx` contra `http://api:8000/api/v1` (configurable con `SMOKE_API_URL`) y `http://mailpit:8025/api/v1`; las cuentas son las del seed y la contraseña sale de `SEED_DEMO_PASSWORD`. La pasada forzada se pide con `celery_app.send_task("enviar_recordatorios", kwargs={"forzar": True})` al `worker` del entorno (misma base que la API) y se espera el email en Mailpit con un tiempo límite. Las franjas salen de `GET /professionals/{id}/slots?date=<mañana>`. Limpieza en un `finally`/fixture: cancelar turnos `scheduled` del test, desactivar sus dos pacientes y restaurar tramos si se agregaron. No borra mensajes de Mailpit que no sean del test.

### D-7 — Bundle (P-8 = A)
`frontend/scripts/check-bundle.mjs` (Node puro, sin dependencias): recorre `dist/`, busca `JWT_SECRET_KEY`, `SMTP_PASSWORD`, `SEED_DEMO_PASSWORD`, `POSTGRES_PASSWORD`, `DATABASE_URL` y `postgresql`, imprime archivo y texto y sale con 1. Se prueba con Vitest sobre una carpeta temporal con y sin hallazgos. `src/env-usage.test.ts` recorre `src/` (sin `*.test.*`) y extrae los `import.meta.env.X`.

### D-8 — Documentación
README según P-11; `docs/adopcion-recepcion.md` con: preparación (cuentas por persona, horarios cargados, prueba del email en Mailpit), primera semana en paralelo con la planilla, criterios para dejar la planilla (métrica de `01_vision_y_objetivos.md`), qué hacer si la API no responde, a quién avisar y preguntas abiertas para el dueño. Sin nombres de proveedores de email ni cuentas reales.

## Risks / Trade-offs

- [`!reset` requiere una versión reciente de Compose] → Compose v5.6.1 lo soporta (verificado al aplicar).
- [El seed corre en cada `up`] → es idempotente y no pisa cambios (spec `seed-data`); tarda poco.
- [Una `JWT_SECRET_KEY` vacía ahora frena en `migrate` y no en `api`] → el escenario de `local-environment` se ajusta; el mensaje sigue nombrando la variable.
- [El smoke test escribe en la base de desarrollo o demo] → datos ficticios, pacientes propios desactivados al final y tramos restaurados; nunca toca la base `_test`.
- [El smoke test depende del reloj y del día] → P-6 = A lo cubre; mañana con feriado no existe en el modelo (no hay feriados).
- [El filtro del registro depende del formato de uvicorn] → el test usa el formato real de la versión instalada; si uvicorn cambia, el test falla en lugar de dejar pasar la consulta.
- [Demo sin HTTPS, sin límite de intentos y con token en `sessionStorage`] → aceptado para uso local con datos ficticios (P-9); se documenta como pendiente antes de datos reales (R-10).
- [Adopción (R-8)] → checklist; la decisión de dejar la planilla queda en el dueño.

## Migration Plan

1. Aplicar los grupos en orden; después del grupo 5 se puede parar sin romper nada (P-12).
2. Al pasar a la versión nueva: completar `SEED_DEMO_PASSWORD` en el `.env` local, agregar `http://localhost:8080` a `CORS_ORIGINS` y `docker compose up --build`.
3. Reversión: quitar el servicio `migrate` y el override de la demo vuelve al flujo manual; los cambios de CORS y registros son independientes.

## Open Questions

Ninguna: P-1 a P-12 quedaron confirmadas (opción A). No se usó la skill `revisor-escenarios-turnos`: el change no cambia reglas de agenda; el smoke test solo usa casos de uso ya especificados.
