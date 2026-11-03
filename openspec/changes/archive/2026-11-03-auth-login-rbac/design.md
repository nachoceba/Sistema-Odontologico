# Design: auth-login-rbac (C-03)

> **Gobernanza CRÍTICA.** Todas las decisiones P-1 a P-15 fueron **CONFIRMADAS (2026-11-03)** por la usuaria, todas con la opción recomendada; las specs usan esos valores.

## Context

Motivación en `proposal.md`. Estado real del código (verificado el 2026-11-03):

- `app/core/config.py` ya valida `JWT_SECRET_KEY` (mínimo 32 caracteres, `SecretStr`), `JWT_ALGORITHM` (solo `HS256`, default) y `ACCESS_TOKEN_EXPIRE_MINUTES` (entero > 0, default 30). **No hacen falta variables de entorno nuevas.**
- `app/core/security.py` solo tiene `hash_password` con un `PasswordHasher()` de argon2-cffi a nivel de módulo (DD-41). `argon2-cffi` ya está en `pyproject.toml`; **PyJWT no**.
- `UserModel` (`users`): `id` UUID, `email` con índice único sobre `lower(email)` (DD-38), `password_hash`, `full_name`, `role` (enum `UserRole` de infraestructura: `admin`, `receptionist`, `dentist`), `active`. `ProfessionalModel.user_id` es único: una cuenta tiene como mucho una ficha de profesional.
- No existe repositorio ni puerto de usuarios (C-05d no lo definió; CHANGES.md lo deja para C-04 en su parte de escritura).
- `app/api/errors.py` traduce `DomainError` con una tabla `STATUS_BY_CODE` (default 400) y el cuerpo `{"error": {"code", "message"}}`; no agrega encabezados.
- `app/main.py` arma la app con `create_app()`; `app/api/router.py` cuelga todo de `/api/v1`; solo existe `GET /api/v1/health`.
- Tests de API: `tests/unit/api/conftest.py` monta la app con una `DATABASE_URL` inexistente, así que los tests unitarios de API no pueden tocar la base: necesitan sustituir el repositorio de cuentas por el de memoria (override de dependencias).
- `tests/unit/test_architecture.py` prohíbe imports de frameworks en `app/domain/`.
- Frontend: React 19 + TS ~5.9 + Vite 8 + Vitest 5; un solo componente `App` que muestra el estado de `/health`; **sin router**; `src/config.ts` lee `VITE_API_URL`.
- Seed: 1 admin, 1 recepción, 2 odontólogos con su ficha; contraseña desde `SEED_DEMO_PASSWORD` (DD-40).

## Goals / Non-Goals

**Goals:**
- Login y validación del JWT con librerías mantenidas (PyJWT, argon2-cffi).
- Dependencias reutilizables (`current_user`, `require_role`, alcance propio) que los changes C-04, C-06, C-07 y C-08 apliquen sin rediseñar.
- Una red de seguridad automática (inventario de rutas) que haga imposible olvidar la protección de un endpoint nuevo.
- Login y rutas protegidas en el frontend.

**Non-Goals:**
- Endpoints de turnos, horarios, pacientes o usuarios (C-04, C-06, C-07, C-08). La regla "odontólogo no lee turnos ajenos" se entrega como regla y dependencia probadas; el test de punta a punta contra un endpoint de turnos va en C-08 (P-12).
- Refresh token, revocación de tokens, recuperación de contraseña, cambio de contraseña, MFA.
- Bloqueo de cuentas o límite de intentos (salvo que P-3 diga lo contrario).
- Cookies httpOnly y CSRF (P-2).
- Cambios de esquema o migraciones.

## Decisiones confirmadas (P-1 a P-15)

Cada pregunta está en lenguaje simple, con opciones, la recomendada y por qué.

### P-1 — ¿Cuánto dura la sesión y hay "renovación automática"? (SU-07) — CONFIRMADA (2026-11-03)
Cuando alguien inicia sesión recibe un "pase" que vence. Al vencer, tiene que volver a escribir su contraseña.
- **A (recomendada)**: 30 minutos, sin renovación. Al vencer, vuelve al login.
- B: 8 horas (una jornada), sin renovación.
- C: 30 minutos con renovación automática (refresh token) mientras la persona esté usando el sistema.
**Por qué A**: es lo que ya dicen la KB (SU-07, DD-11) y la configuración (`ACCESS_TOKEN_EXPIRE_MINUTES = 30`). Un pase corto limita el daño si alguien lo roba, porque no se puede anular antes de que venza. C es lo más cómodo pero suma un segundo tipo de token, guardarlo y rotarlo: más trabajo y más riesgo para un MVP. Si la recepción se queja, se puede subir el número sin tocar código (es una variable de entorno).

### P-2 — ¿Dónde guarda el navegador el pase de sesión? — CONFIRMADA (2026-11-03)
- A: solo en la memoria de la página. Si se recarga la página (F5), hay que volver a iniciar sesión.
- **B (recomendada)**: `sessionStorage`. Sobrevive a recargar la página, pero se borra al cerrar la pestaña.
- C: `localStorage`. Sobrevive a cerrar el navegador.
- D: cookie protegida que pone el servidor (httpOnly).
**Por qué B**: equilibrio entre comodidad (recargar no te saca) y riesgo (cerrar la pestaña cierra la sesión). A, B y C tienen el mismo riesgo si alguien logra inyectar código en la página (XSS): CHANGES.md ya acepta y documenta ese riesgo. D es la más segura pero cambia el diseño de la API (cookies, protección CSRF, CORS con credenciales); queda como mejora para C-13.

### P-3 — ¿Qué pasa si alguien se equivoca de contraseña muchas veces? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: nada especial en C-03; se documenta el riesgo y se revisa en C-13 (salida a producción).
- B: limitar intentos por email (por ejemplo 5 cada 15 minutos) usando Redis; al pasarse, la API responde "demasiados intentos, esperá unos minutos" (429).
- C: bloquear la cuenta después de N intentos hasta que el administrador la desbloquee (requiere una columna nueva y una migración).
**Por qué A**: los datos son ficticios y el hash argon2 ya es lento a propósito, lo que encarece probar contraseñas a ciegas. C permite que cualquiera bloquee a la recepcionista escribiendo mal su email a propósito. B es razonable pero suma Redis al login y variables nuevas (`LOGIN_MAX_ATTEMPTS`, `LOGIN_WINDOW_MINUTES`); conviene hacerlo junto con el endurecimiento de C-13.

### P-4 — ¿Confirmamos qué puede hacer cada rol? (matriz RBAC y SU-06) — CONFIRMADA (2026-11-03)
La KB (`03_actores_y_roles.md`) dice: el **administrador** puede todo; la **recepción** crea, lee y modifica pacientes y turnos (cancelar es cambiar estado), **ve todos los turnos** y solo lee horarios y profesionales; el **odontólogo** lee pacientes, lee solo sus turnos, horarios y ficha, y solo cambia el estado de sus turnos a atendido o ausente. Pregunta abierta de prioridad Alta SU-06: ¿solo el administrador edita horarios?
- **A (recomendada)**: confirmar la matriz tal cual, con "solo el administrador edita horarios y licencias".
- B: la matriz, pero la recepción también edita horarios y licencias.
- C: otra variante que indique el usuario.
**Por qué A**: es lo que ya asumen la KB y CHANGES.md; los horarios cambian poco y concentrarlos en una persona evita conflictos. C-03 no crea esos endpoints, pero deja la matriz confirmada para que C-07 y C-08 la apliquen con su test de permisos. Responder esto cierra SU-06.

### P-5 — ¿Qué mensaje y qué código responde la API en cada falla? — CONFIRMADA (2026-11-03)
- **A (recomendada)**:
  - Email o contraseña mal, **o cuenta desactivada**: 401, código `INVALID_CREDENTIALS`, mensaje "Email o contraseña incorrectos". El mismo para los tres casos.
  - Sin sesión, sesión vencida o inválida: 401, código `NOT_AUTHENTICATED`, "Tu sesión terminó. Volvé a ingresar" en el frontend.
  - Con sesión pero sin permiso: 403, código `FORBIDDEN`, "No tenés permiso para esta acción".
- B: igual que A, pero la cuenta desactivada recibe un mensaje propio ("Tu usuario está desactivado") con 403.
**Por qué A**: con un mensaje distinto para cuentas desactivadas, alguien de afuera podría averiguar qué emails existen y cuál es la contraseña correcta de una cuenta dada de baja. El Flujo 1 pide "mensaje genérico, sin revelar cuál dato falló". 401 significa "no sé quién sos" y 403 "sé quién sos pero no podés": por eso la falta de rol es 403.

### P-6 — ¿El email del login distingue mayúsculas y espacios? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: no. `Admin@Example.com ` (con espacio al final) entra igual que `admin@example.com`.
- B: se exige el email exacto.
**Por qué A**: la base ya trata el email como único sin distinguir mayúsculas (DD-38); los espacios que se cuelan al copiar y pegar son el error más común en un login. La contraseña sí se compara exacta (no se le quitan espacios).

### P-7 — ¿A qué pantalla va cada rol después de entrar? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: los tres roles van a `/agenda`. Hasta que exista la agenda (C-10), esa página muestra "Hola, <nombre>", el rol y el botón "Salir".
- B: el administrador va a `/usuarios`, la recepción y los odontólogos a `/agenda`.
**Por qué A**: la agenda es la pantalla principal de los tres (el odontólogo verá solo la suya, RN-AU-04). `/usuarios` todavía no existe (C-04).

### P-8 — Si el administrador cambia el rol de alguien que ya tiene sesión abierta, ¿qué pasa? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: su sesión se corta en el siguiente clic (401) y tiene que volver a entrar, ya con el rol nuevo.
- B: sigue con la sesión y el sistema usa el rol nuevo sin avisarle.
**Por qué A**: CHANGES.md pide que se rechacen los cambios de rol; así nunca conviven en la misma sesión dos roles distintos y la pantalla no queda mostrando opciones del rol anterior. Lo mismo pasa si se desactiva la cuenta (eso no es pregunta: lo exige RN-AU-03).

### P-9 — ¿Qué datos devuelve "quién soy" (`GET /auth/me`)? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: id, email, nombre completo, rol y, si es odontólogo, el id de su ficha de profesional. Nada más.
- B: solo id, nombre y rol (sin email).
**Por qué A**: el frontend necesita el nombre y el rol para la pantalla, y el id de profesional para que la futura agenda del odontólogo filtre lo propio. El email es de la propia persona, no es dato de pacientes. Nunca se devuelven el hash ni el token. La seguridad se prueba con un test que verifica que la respuesta no contiene `password_hash`.

### P-10 — ¿Hacen falta variables de entorno nuevas? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: no. `JWT_SECRET_KEY`, `JWT_ALGORITHM=HS256` y `ACCESS_TOKEN_EXPIRE_MINUTES=30` ya existen y se validan desde C-01; `.env.example` no cambia.
- B: si en P-3 se elige limitar intentos, se agregan `LOGIN_MAX_ATTEMPTS` y `LOGIN_WINDOW_MINUTES` (el texto está en el archivo temporal que acompaña este change, ver "Migration Plan"; lo agrega el usuario a mano).
**Por qué A**: menos configuración que mantener; el frontend no necesita ninguna variable nueva (sigue usando solo `VITE_API_URL`).

### P-11 — ¿Cómo se cierra la sesión? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: botón "Salir" que borra el pase del navegador y vuelve al login. El servidor no guarda sesiones, así que un pase copiado antes seguiría sirviendo hasta que venza (máximo 30 minutos).
- B: además, una "lista negra" en Redis de pases cerrados que la API rechaza.
**Por qué A**: B convierte al JWT en sesión con estado (cada request consulta Redis) y suma un endpoint; para datos ficticios y pases de 30 minutos no se justifica. Se documenta el riesgo (DD-11 ya lo acepta).

### P-12 — Un odontólogo sin ficha de profesional, o con la ficha desactivada, ¿qué ve? — CONFIRMADA (2026-11-03)
(Hallazgo de la revisión de escenarios: el modelo permite una cuenta `dentist` sin fila en `professionals`.)
- **A (recomendada)**: puede iniciar sesión, pero no ve turnos ni horarios de nadie hasta que el administrador le asigne su ficha. Si su ficha está desactivada, sigue viendo lo suyo (para consultar su historial); el ingreso lo decide solo `users.active`.
- B: no puede ni iniciar sesión sin ficha activa.
**Por qué A**: separa "puede entrar" (cuenta activa, RN-AU-03) de "qué ve" (RN-AU-04), y nunca le muestra datos ajenos por error. C-04 crea cuenta y ficha juntas, así que el caso solo aparece por datos cargados a mano.

### P-13 — Si un odontólogo pide un turno de otro profesional, ¿decimos "no tenés permiso" o "no existe"? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: "no tenés permiso" (403).
- B: "no existe" (404), para no confirmar que ese turno existe.
**Por qué A**: los odontólogos son personal del mismo consultorio y ya saben qué profesionales hay; el 403 es más claro para depurar y para el usuario. B tiene sentido con usuarios externos, que acá no hay.
Además: ¿cómo se prueba "un odontólogo no ve turnos ajenos" si C-03 todavía no tiene la pantalla de turnos? **Recomendado**: C-03 entrega la regla y la dependencia, probadas con una ruta de prueba que existe solo en los tests; el test contra el endpoint real de turnos es obligatorio en C-08. Alternativa: adelantar a C-03 un endpoint mínimo de lectura de turnos (agranda el change y pisa a C-08).

### P-14 — ¿Sumamos una librería de rutas al frontend? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: sí, `react-router` (la librería de rutas más usada de React; solo el modo "librería", sin servidor).
- B: rutas hechas a mano con `window.location` y un `switch`.
**Por qué A**: C-04, C-06 y C-10 suman pantallas; hacerlo a mano obliga a reimplementar redirecciones, "volver atrás" y rutas protegidas. Es gratis y mantenida.

### P-15 — ¿Hacemos C-03 de una vez o lo partimos en dos? — CONFIRMADA (2026-11-03)
- **A (recomendada)**: un solo change, ejecutado por grupos (backend primero, frontend al final), como C-02.
- B: C-03a (backend: login, JWT, dependencias, repositorio) y C-03b (frontend: login y rutas protegidas).
**Por qué A**: el tamaño es similar al de C-02 (que se hizo en uno) y el frontend depende de una sola ruta del backend; partirlo duplica revisión y archivado. Si se elige B, el corte natural es entre los grupos 5 y 6 de `tasks.md`.

## Decisions

Decisiones técnicas (no de dominio). Si una respuesta P-n las afecta, se indica.

### D-1 — Capas
- `app/domain/auth/` (puro, sin frameworks; lo vigila `test_architecture.py`): `Role` (enum de dominio con los tres valores), `UserAccount` (cuenta leída: id, email, nombre, hash, rol, activo, `professional_id | None`), `Principal` (lo que sabe una request: id, rol, `professional_id`), puerto `UserAccountRepository` (Protocol: `get_by_email`, `get_by_id`), errores `InvalidCredentialsError`, `NotAuthenticatedError`, `ForbiddenError` (subclases de `DomainError` con `code`), y la regla pura `can_access_professional(principal, professional_id) -> bool`.
- `app/core/security.py`: `verify_password`, `create_access_token`, `decode_access_token` (PyJWT y argon2-cffi viven en `core`, igual que `hash_password`, porque `domain` no puede importar librerías de terceros con I/O ni frameworks; argon2 y PyJWT son puras pero se mantienen fuera del dominio por coherencia con DD-41).
- `app/application/auth.py`: caso de uso `authenticate(email, password, repo, settings) -> (token, account)` y `resolve_principal(token, repo, settings) -> Principal`. Sin FastAPI.
- `app/api/dependencies.py`: `get_user_repository` (fábrica sobreescribible en tests), `current_user`, `require_role(*roles)`, `require_professional_access` (aplica la regla de alcance a un parámetro de ruta).
- `app/api/auth.py`: router con `POST /auth/login` y `GET /auth/me`.
- Repositorios: `app/infrastructure/in_memory/users.py` y `app/infrastructure/db/repositories/users.py`; batería de contrato en `tests/contract/test_user_account_repository.py` con las fábricas `in_memory` y `postgres`.
**Alternativa**: poner todo en `app/api/`. Descartada: el caso de uso quedaría acoplado a FastAPI y sin tests puros.

### D-2 — JWT con PyJWT (Context7: `/jpadilla/pyjwt`, consultado el 2026-11-03)
- Contenido: `sub` (id de la cuenta, texto), `role`, `iat`, `exp`. Nada más (spec user-authentication).
- `jwt.encode(payload, key, algorithm=settings.JWT_ALGORITHM)` con `exp` como `datetime` UTC.
- `jwt.decode(token, key, algorithms=[settings.JWT_ALGORITHM], options={"require": ["exp", "iat", "sub"]})`. La documentación confirma: `algorithms` es obligatorio y fija la lista blanca (rechaza `none` y otros algoritmos); `exp` se verifica solo y lanza `ExpiredSignatureError`; un claim faltante en `require` lanza `MissingRequiredClaimError`; todas heredan de `InvalidTokenError`. Se captura `InvalidTokenError` y se traduce a `NotAuthenticatedError` (un solo código, P-5).
- Sin `leeway` (un solo servidor, sin desfase de relojes).
- El reloj se inyecta (parámetro `now`) para probar el vencimiento sin dormir.
**Alternativa**: python-jose. Descartada por CHANGES.md (sin mantenimiento).

### D-3 — Verificación de contraseña con argon2-cffi (Context7: `/hynek/argon2-cffi`, consultado el 2026-11-03)
- `PasswordHasher.verify(hash, password)` devuelve `True` o lanza `VerifyMismatchError` (no coincide), `InvalidHashError` (hash corrupto) o `VerificationError`. `verify_password` devuelve `bool`: `False` ante cualquiera de las tres (un hash corrupto en la base no debe dar 500 en el login; se registra en el log sin datos sensibles).
- **Tiempo parejo**: si el email no existe, igual se verifica contra un hash ficticio precalculado para que el tiempo de respuesta no revele si la cuenta existe (complementa P-5 A).
- `check_needs_rehash` existe y la doc recomienda rehashear al iniciar sesión; **no se hace en C-03** porque el repositorio es de solo lectura y los parámetros por defecto no cambiaron. Queda anotado para C-04 (que tendrá escritura de usuarios).

### D-4 — Esquema `Bearer` propio y errores uniformes (Context7: `/websites/fastapi_tiangolo`, consultado el 2026-11-03)
- Se usa `HTTPBearer(auto_error=False)`: la doc indica que con `auto_error=False` la dependencia devuelve `None` si falta el encabezado, en lugar de responder sola. Así `current_user` lanza `NotAuthenticatedError` y la respuesta sale con el cuerpo uniforme (`{"error": ...}`) en lugar del `{"detail": "Not authenticated"}` de FastAPI. Se mantiene `HTTPBearer` (y no un header manual) para que OpenAPI documente el esquema de seguridad y `/docs` tenga el botón "Authorize".
- La doc también confirma que las versiones actuales de FastAPI responden 401 (no 403) ante credenciales faltantes; de todos modos no dependemos de ese comportamiento.
- `app/api/errors.py`: la tabla suma `INVALID_CREDENTIALS: 401`, `NOT_AUTHENTICATED: 401`, `FORBIDDEN: 403`, y el manejador agrega `WWW-Authenticate: Bearer` a toda respuesta 401 (spec error-model).
- **Alternativa**: `OAuth2PasswordBearer` + formulario `application/x-www-form-urlencoded`. Descartada: obliga a que el login reciba `username` en formulario; nuestro contrato es JSON con `email`.

### D-5 — `current_user` recarga la cuenta en cada request
Decodifica el token → busca la cuenta por `sub` → rechaza si no existe, si `active = false` o si `role` difiere del del token (P-8) → devuelve `Principal`. Una consulta por request (por clave primaria, con el join al profesional): costo aceptable para un consultorio. Se ejecuta en endpoints síncronos (`def`), coherente con SQLAlchemy síncrono (FastAPI los corre en su pool de hilos).

### D-6 — `require_role(*roles)` como fábrica de dependencias
`require_role(Role.ADMIN, Role.RECEPTIONIST)` devuelve una dependencia que depende de `current_user` y lanza `ForbiddenError` si el rol no está. Orden garantizado: primero 401, después 403 (escenario "Sin token en ruta con rol"). Se usa en el decorador de la ruta o como parámetro tipado `Annotated[Principal, Depends(require_role(...))]`.

### D-7 — Inventario de rutas
`tests/unit/api/test_route_inventory.py` recorre `app.routes` (solo `APIRoute`), y para cada ruta fuera de `PUBLIC_ROUTES = {("POST", "/api/v1/auth/login"), ("GET", "/api/v1/health")}` verifica que su árbol de dependencias (`route.dependant`, recursivo) incluya `current_user`. Además hace una llamada real sin token a cada ruta protegida y espera 401. Las rutas de OpenAPI (`/openapi.json`, `/docs`) no son `APIRoute` y quedan fuera (se documenta; publicar el esquema no expone datos).
**Alternativa**: middleware global que exige token salvo una lista blanca. Descartada: duplica la lógica de `current_user` y esconde la dependencia de cada endpoint.

### D-8 — Alcance propio del odontólogo
`can_access_professional(principal, professional_id: str) -> bool` (pura): `admin` y `receptionist` → `True`; `dentist` → `principal.professional_id is not None and principal.professional_id == professional_id` (comparación de texto normalizado; un id mal formado nunca coincide). `require_professional_access` la aplica al parámetro de ruta `professional_id` y lanza `ForbiddenError` (P-13). Para recursos que se identifican por otro id (un turno), C-08 cargará el turno y aplicará la misma regla con su `professional_id`. Se prueba con una ruta registrada solo en el test (`/api/v1/_test/professionals/{professional_id}`), nunca en la app real.

### D-9 — Contrato del login
- Request JSON: `email` (texto, 1..254 caracteres, se recorta y se pasa a minúsculas, P-6) y `password` (1..128 caracteres, sin recortar). Se valida con Pydantic; fuera de rango → 422 (formato de FastAPI; el 422 no se uniforma en este change).
- No se usa `EmailStr` para no sumar `email-validator` ni rechazar con 422 emails "raros" que igual darían 401.
- Response 200: `{"access_token", "token_type": "bearer", "expires_in": <segundos>, "user": {id, email, full_name, role, professional_id}}`.

### D-10 — Tests de API sin base de datos
Los tests de `tests/unit/api/` sobreescriben `get_user_repository` con el repositorio en memoria (`app.dependency_overrides`). El contrato del repositorio PostgreSQL se prueba en la batería de contrato con `-m integration`; un test de integración extra hace login real contra la base con los usuarios del seed.

### D-11 — Frontend
- `src/auth/session.ts`: guardar, leer y borrar el token en `sessionStorage` (P-2) envuelto en `try/catch` (el almacenamiento puede fallar en modo privado: entonces la sesión vive solo en memoria).
- `src/api/client.ts`: `apiFetch` que agrega `Authorization: Bearer`, y ante 401 borra la sesión y notifica (evento) para redirigir a `/login`; ante 403 no borra nada. `/health` y el login no pasan por el agregado del token.
- `src/auth/AuthProvider.tsx` (contexto con `user`, `login`, `logout`) y `RequireAuth` (redirige a `/login`).
- Pantallas: `LoginPage` (incluye el indicador de estado de la API, spec frontend-shell) y `AgendaPlaceholderPage`. Con `react-router` (P-14) en modo librería (`BrowserRouter`, `Routes`, `Navigate`). Al montar con token guardado, se llama a `/auth/me` para obtener nombre y rol (no se decodifica el JWT en el navegador).
- Reglas de `vercel-react-best-practices` (solo React): sin componentes definidos dentro de otros, renderizado condicional con ternario, imports directos sin barrels. `frontend-design`: pantalla de login sobria y accesible (labels asociados, foco visible, errores con `role="alert"`).
- Tests con Vitest + Testing Library, `fetch` simulado como en `App.test.tsx`.

## Revisión de escenarios (skill `revisor-escenarios-turnos`)

Se aplicó solo al requisito "Un odontólogo solo accede a lo propio", el único que toca turnos y horarios.

**Resumen**: 5 escenarios revisados, 5 hallazgos (1 ambigüedad, 2 bordes faltantes, 1 pregunta abierta, 1 sin respaldo).

| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Borde faltante | Odontólogo sin ficha | `users 1───0..1 professionals`: puede existir una cuenta `dentist` sin profesional | `04_modelo_de_datos.md` (relación users–professionals), DD-38 | Negar todo acceso (P-12 A); escenario agregado |
| 2 | Ambigüedad | Odontólogo con ficha desactivada | `professionals.active` y `users.active` son independientes; RN-AU-03 habla solo de la cuenta | RN-AU-03, `04_modelo_de_datos.md` | El ingreso lo decide `users.active`; ve lo suyo aunque la ficha esté inactiva (P-12 A) |
| 3 | Sin respaldo | Odontólogo con otro profesional | Responder 403 o 404 no está definido en la KB | sin respaldo en la KB | 403 `FORBIDDEN` (P-13 A) |
| 4 | Pregunta abierta | Recepción con cualquier profesional | La lectura de horarios por recepción depende de quién los edita | SU-06 (prioridad Alta, `10_preguntas_abiertas.md`) | Confirmar la matriz (P-4 A) |
| 5 | Borde faltante | Id de profesional mal formado | Sin escenario para un id que no es UUID | sin respaldo en la KB (convención de los repos: `parse_uuid` devuelve "sin resultado") | Negar sin error interno; escenario agregado |

**Escenarios sin hallazgos**: odontólogo con su propio profesional (RN-AU-04); administración con cualquier profesional (matriz RBAC).
**Contrato**: CHANGES.md pide el test "dentist no lee turnos ajenos", pero C-03 no tiene endpoint de turnos: se cubre con la regla y una ruta de prueba, y el test de punta a punta queda como obligación de C-08 (P-13).

## Risks / Trade-offs

- [Token robado sirve hasta que vence; "Salir" no lo anula] → vida corta (P-1), recarga de la cuenta en cada request (desactivar corta el acceso al instante), riesgo ya aceptado en DD-11.
- [XSS puede leer el token de `sessionStorage`] → sin `dangerouslySetInnerHTML`, React escapa por defecto; riesgo aceptado en CHANGES.md; cookie httpOnly como mejora en C-13.
- [Sin límite de intentos: fuerza bruta] → argon2 lento, contraseñas del seed fuera del repo (DD-40); revisar en C-13 (P-3).
- [Un endpoint futuro sin `require_role`] → test de inventario de rutas (D-7) y test de permisos por rol obligatorio (regla dura 4).
- [Enumeración de cuentas por tiempo de respuesta] → verificación contra hash ficticio cuando el email no existe (D-3).
- [Un hash corrupto en la base] → `verify_password` devuelve `False` (401) y se registra sin datos sensibles; no 500.
- [Una consulta extra a la base por request] → por clave primaria; aceptable a la escala de un consultorio.
- [`UserRole` de infraestructura y `Role` de dominio duplicados] → el repositorio convierte por valor; un test verifica que ambos tienen los mismos valores.
- [El 422 de validación sigue con el formato de FastAPI, no el uniforme] → fuera de alcance; anotado para un change posterior si molesta.

## Migration Plan

1. Agregar `PyJWT>=2.10,<3` a `pyproject.toml` y reconstruir la imagen del backend (`docker compose build api worker beat`).
2. Agregar `react-router` a `frontend/package.json` (si P-14 = A) y reconstruir la imagen del frontend.
3. Sin migraciones de base. Sin variables nuevas si P-10 = A. Si P-3 = B, el usuario agrega a mano a `.env.example` y a su `.env` las líneas del archivo temporal `C:\Users\Nacho\AppData\Local\Temp\claude\C--Users-Nacho--claude-spares-spare-D8YkE8\c784f797-31af-4ac5-971b-3bba426bb686\scratchpad\c03-env-vars-opcionales.txt` (el agente no edita `.env` ni `.env.example`).
4. Para probar a mano: `docker compose up`, correr el seed con `SEED_DEMO_PASSWORD` definido y entrar con una cuenta del seed.
5. Rollback: revertir el commit; no hay cambios de datos.

## Open Questions

Ninguna diferible: todas las decisiones abiertas están en P-1 a P-15 y bloquean el grupo 1 de `tasks.md`.
