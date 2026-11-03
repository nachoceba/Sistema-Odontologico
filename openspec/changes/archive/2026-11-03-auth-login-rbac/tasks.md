# Tasks: auth-login-rbac (C-03)

> **Gobernanza CRÍTICA.** El grupo 0 bloquea todo lo demás: no se escribe código hasta que el usuario confirme P-1 a P-15. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso y refactor con los tests en verde. Los tests de integración corren en el contenedor (`pytest -m integration`). No editar `.env` ni `.env.example`. Sin commits ni push sin pedido explícito del usuario, y sin `Co-Authored-By`.

## 0. Confirmaciones del usuario (BLOQUEANTE)

- [x] 0.1 Obtener respuesta a P-1 (duración de la sesión, refresh token, SU-07) y marcarla CONFIRMADA en `design.md`
- [x] 0.2 Obtener respuesta a P-2 (dónde guarda el navegador el token) y marcarla CONFIRMADA en `design.md`
- [x] 0.3 Obtener respuesta a P-3 (intentos fallidos) y marcarla CONFIRMADA; si es B o C, reabrir specs, design y tasks con `/opsx:update` antes de seguir
- [x] 0.4 Obtener respuesta a P-4 (matriz RBAC y SU-06) y marcarla CONFIRMADA en `design.md`
- [x] 0.5 Obtener respuesta a P-5 (códigos y mensajes 401/403, cuenta desactivada) y marcarla CONFIRMADA en `design.md`
- [x] 0.6 Obtener respuestas a P-6 (email sin mayúsculas ni espacios), P-7 (redirección por rol), P-8 (cambio de rol con sesión abierta) y P-9 (datos de `/auth/me`) y marcarlas CONFIRMADAS en `design.md`
- [x] 0.7 Obtener respuestas a P-10 (variables de entorno) y P-11 (cerrar sesión); si P-10 = B, pedirle al usuario que agregue a mano las líneas del archivo temporal indicado en `design.md` §Migration Plan y verificar `tests/unit/test_env_example.py` en verde
- [x] 0.8 Obtener respuestas a P-12 (odontólogo sin ficha o con ficha inactiva) y P-13 (403 vs 404 y cómo se prueba "no ve turnos ajenos") y marcarlas CONFIRMADAS en `design.md`
- [x] 0.9 Obtener respuestas a P-14 (`react-router`) y P-15 (un change o dos); si se parte, reorganizar con `/opsx:update` cortando entre los grupos 5 y 6
- [x] 0.10 (ajustes: no hubo diferencias; registradas DD-45 a DD-55 en `knowledge-base/09_decisiones_y_supuestos.md`; SU-06 y SU-07 resueltos en 09 y 10) Si alguna respuesta difiere de la recomendación, ajustar specs, design y tasks; registrar las decisiones como DD-45 en adelante en `knowledge-base/09_decisiones_y_supuestos.md`, actualizar SU-06 y SU-07 en `09_decisiones_y_supuestos.md` y `10_preguntas_abiertas.md`; verificar `openspec validate auth-login-rbac --strict` en verde

## 1. Preparación y línea base

- [x] 1.1 Safety net: correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict`, `ruff check` y en el frontend `npm test`, `npm run typecheck` y `npm run lint`; anotar los números en verde como línea base (315 por defecto y 151 de integración según C-02); si algo falla, frenar y reportarlo como falla previa
- [x] 1.2 Agregar `PyJWT>=2.10,<3` a `pyproject.toml` y reconstruir la imagen del backend; verificar `python -c "import jwt"` dentro del contenedor y que la línea base sigue en verde

## 2. Dominio de autenticación (puro) — specs access-control y user-account-repository

- [x] 2.1 RED: tests en `tests/unit/domain/auth/test_access_rules.py` para `can_access_professional`: odontólogo con su profesional (permite), con el otro (niega), recepción y admin con cualquiera (permiten), odontólogo sin ficha (niega), id mal formado (niega); ejecutar y verificar que fallan por falta del módulo
- [x] 2.2 GREEN: `app/domain/auth/` con `Role`, `Principal`, `UserAccount` y `can_access_professional`; verificar 2.1 en verde y `tests/unit/test_architecture.py` en verde (sin imports de frameworks)
- [x] 2.3 RED → GREEN: tests de los errores `InvalidCredentialsError`, `NotAuthenticatedError` y `ForbiddenError` (pertenecen a `DomainError`, códigos `INVALID_CREDENTIALS`, `NOT_AUTHENTICATED`, `FORBIDDEN`, mensajes genéricos de P-5); implementarlos; verificar en verde
- [x] 2.4 RED → GREEN: test de que `Role` (dominio) y `UserRole` (infraestructura) tienen exactamente los mismos valores; verificar en verde
- [x] 2.5 Puerto `UserAccountRepository` (Protocol con `get_by_email` y `get_by_id`); verificar `mypy --strict app/` limpio

## 3. Repositorio de cuentas — spec user-account-repository

- [x] 3.1 RED: batería de contrato `tests/contract/test_user_account_repository.py` (email exacto, otras mayúsculas, inexistente, cuenta desactivada devuelta, id existente, id inexistente, id mal formado, odontólogo con `professional_id`) con la fábrica `in_memory`; verificar que falla
- [x] 3.2 GREEN: `app/infrastructure/in_memory/users.py`; verificar la batería en verde con `in_memory`
- [x] 3.3 RED: registrar la fábrica `postgres` en la batería; verificar que falla con `pytest -m integration`
- [x] 3.4 GREEN: `app/infrastructure/db/repositories/users.py` (búsqueda por `lower(email)` que usa el índice `uq_users_email_lower`, join externo a `professionals`, `parse_uuid` para ids); exportarlo en `repositories/__init__.py`; verificar la batería en verde con ambas fábricas y `tests/contract/test_import_order.py` en verde

## 4. Seguridad: contraseña y JWT — spec user-authentication

- [x] 4.1 RED: tests de `verify_password` en `tests/unit/core/test_security.py`: correcta (True), incorrecta (False), hash corrupto (False sin excepción), contraseña vacía (False); verificar que fallan
- [x] 4.2 GREEN: `verify_password` en `app/core/security.py` (D-3); verificar en verde junto con los tests existentes de `hash_password`
- [x] 4.3 RED: tests de `create_access_token` / `decode_access_token` con reloj inyectado: contenido mínimo (`sub`, `role`, `iat`, `exp`, sin email ni nombre), vence a los `ACCESS_TOKEN_EXPIRE_MINUTES`, vencido rechazado, otra clave rechazada, algoritmo `none` rechazado, sin `exp` rechazado, sin `sub` rechazado; verificar que fallan
- [x] 4.4 GREEN: implementar con PyJWT según D-2 (lista blanca de algoritmos, `require`, `InvalidTokenError` → `NotAuthenticatedError`); verificar 4.3 en verde, `mypy --strict` y `ruff` limpios

## 5. Casos de uso, dependencias y endpoints — specs user-authentication, access-control y error-model

- [x] 5.1 RED: tests de `app/application/auth.py` con el repositorio en memoria: `authenticate` válido (token + cuenta), contraseña incorrecta, email inexistente, cuenta desactivada (los tres con `InvalidCredentialsError` y el mismo mensaje), email con mayúsculas y espacios (P-6); `resolve_principal` con token válido, cuenta borrada, desactivada y con rol cambiado (P-8); verificar que fallan
- [x] 5.2 GREEN: implementar los casos de uso, incluida la verificación contra hash ficticio cuando el email no existe (D-3); verificar 5.1 en verde
- [x] 5.3 RED: tests de `tests/unit/api/test_error_handlers.py` para los códigos nuevos (401 con `WWW-Authenticate: Bearer` para `INVALID_CREDENTIALS` y `NOT_AUTHENTICATED`, 403 sin ese encabezado para `FORBIDDEN`); verificar que fallan
- [x] 5.4 GREEN: ampliar `STATUS_BY_CODE` y el manejador en `app/api/errors.py`; verificar 5.3 y los escenarios archivados de error-model en verde
- [x] 5.5 RED: tests de API de `POST /api/v1/auth/login` (override de `get_user_repository` con el repo en memoria, D-10): 200 con token y datos sin `password_hash`, 401 genérico en contraseña incorrecta / email inexistente / cuenta desactivada con mensajes idénticos, mayúsculas y espacios, 422 por campos vacíos y por contraseña de más de 128 caracteres; verificar que fallan
- [x] 5.6 GREEN: `app/api/dependencies.py` (`get_user_repository`) y `app/api/auth.py` con el login (D-9); incluir el router en `app/api/router.py`; verificar 5.5 en verde
- [x] 5.7 RED: tests de `current_user` y `require_role` con rutas de prueba montadas solo en el test: sin encabezado, esquema `Basic`, token vencido, cuenta desactivada con token vigente, rol cambiado → 401 `NOT_AUTHENTICATED`; rol permitido → 200; rol no permitido → 403 `FORBIDDEN`; sin token en ruta con rol → 401; ruta con dos roles probada con los tres roles; verificar que fallan
- [x] 5.8 GREEN: `current_user` con `HTTPBearer(auto_error=False)` y `require_role(*roles)` (D-4 a D-6); verificar 5.7 en verde
- [x] 5.9 RED → GREEN: `require_professional_access` con la ruta de prueba `/api/v1/_test/professionals/{professional_id}` (solo en el test): odontólogo propio 200, ajeno 403, sin ficha 403, id mal formado 403, recepción y admin 200 (D-8, P-13); verificar en verde
- [x] 5.10 RED → GREEN: `GET /api/v1/auth/me` con test de permisos por rol (admin, recepción y odontólogo reciben sus datos; sin token 401; la respuesta no contiene `password_hash`; nombre cambiado en el repo se refleja); verificar en verde
- [x] 5.11 RED → GREEN: `tests/unit/api/test_route_inventory.py` (D-7): toda `APIRoute` fuera de las públicas depende de `current_user` y responde 401 sin token; triangular con una app de prueba que registra una ruta sin protección y verificar que el chequeo la detecta y la nombra; verificar en verde con la app real
- [x] 5.12 Test de integración `tests/integration/test_auth_login.py`: login real contra PostgreSQL con un usuario creado en el test (sin la contraseña del seed en el código) y `GET /auth/me` con ese token; verificar con `pytest -m integration` en verde
- [x] 5.13 Verificar que `/openapi.json` lista `POST /api/v1/auth/login` y `GET /api/v1/auth/me` con el esquema de seguridad `HTTPBearer`, y que `mypy --strict`, `ruff check` y `pytest` completo están en verde

## 6. Frontend: sesión, login y rutas protegidas — specs frontend-auth y frontend-shell

- [x] 6.1 Agregar `react-router` a `frontend/package.json` (si P-14 = A), instalar y verificar `npm run typecheck` y `npm test` en verde (línea base)
- [x] 6.2 RED → GREEN: `src/auth/session.ts` (guardar, leer y borrar en `sessionStorage`; si el almacenamiento lanza error, cae a memoria); tests de guardar/leer/borrar y del almacenamiento que falla; verificar en verde
- [x] 6.3 RED → GREEN: `src/api/client.ts`: agrega `Authorization: Bearer` cuando hay token, no lo agrega a `/health` ni al login, ante 401 borra la sesión y avisa, ante 403 conserva la sesión; verificar en verde
- [x] 6.4 RED → GREEN: `LoginPage`: envío correcto navega a `/agenda`; 401 muestra "Email o contraseña incorrectos" y conserva el email; error de red muestra "No se pudo conectar con el servidor"; doble clic envía una sola solicitud; muestra el estado de la API (escenarios de frontend-shell adaptados); verificar en verde
- [x] 6.5 RED → GREEN: rutas (`AuthProvider`, `RequireAuth`, `App`): sin sesión `/agenda` → `/login`; con sesión `/login` → `/agenda`; ruta inexistente según haya sesión; recarga con token llama a `/auth/me` y sigue con sesión; 401 en una llamada vuelve a `/login` con "Tu sesión terminó. Volvé a ingresar"; "Salir" borra el token; página provisoria de agenda con nombre y rol; verificar en verde
- [x] 6.6 Adaptar o reemplazar `src/App.test.tsx` para que los escenarios archivados de frontend-shell sigan cubiertos en la pantalla de login; verificar que no quedan tests huérfanos y `npm test` en verde
- [x] 6.7 Revisar la pantalla de login con `frontend-design` (labels asociados, foco visible, errores con `role="alert"`) y las reglas de React de `vercel-react-best-practices`; verificar `npm run lint` y `npm run typecheck` limpios y que ningún archivo del frontend referencia `JWT_SECRET_KEY` ni otra variable secreta (grep)

## 7. Verificación integral y documentación

- [x] 7.1 Prueba manual en Docker Compose: seed con `SEED_DEMO_PASSWORD`, login con cada uno de los cuatro usuarios del seed, `/agenda` con nombre y rol, "Salir", login con contraseña incorrecta y con una cuenta desactivada a mano; anotar el resultado en el resumen del apply
- [x] 7.2 Batería completa en el contenedor: `pytest`, `pytest -m integration`, `mypy --strict`, `ruff check`, `npm test`, `npm run typecheck`, `npm run lint`; anotar los números y compararlos con la línea base de 1.1
- [x] 7.3 Actualizar `knowledge-base/03_actores_y_roles.md` (si P-4 cambió la matriz), `09_decisiones_y_supuestos.md` (DD de C-03, consultas de Context7 que influyeron) y la entrada de C-03 en `CHANGES.md` (estado, nota para C-08: test de punta a punta "odontólogo no ve turnos ajenos"; nota para C-04: rehash con `check_needs_rehash`); verificar `openspec validate auth-login-rbac --strict` en verde
