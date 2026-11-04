# Tasks: user-management (C-04)

> **Gobernanza ALTA.** El grupo 0 bloquea todo lo demás: no se escribe código hasta que la usuaria confirme P-1 a P-14. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso y refactor con los tests en verde. Los tests de integración corren en el contenedor (`pytest -m integration`). No editar `.env` ni `.env.example`. `domain/` sin imports de FastAPI ni SQLAlchemy; type hints en todo; TypeScript sin `any`. Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`.

## 0. Confirmaciones de la usuaria (BLOQUEANTE)

- [x] 0.1 Obtener respuesta a P-1 (contraseña inicial) y P-2 (asignar contraseña nueva) y marcarlas CONFIRMADAS en `design.md`
- [x] 0.2 Obtener respuesta a P-3 (editar email) y P-4 (cambios de rol, caso odontólogo) y marcarlas CONFIRMADAS
- [x] 0.3 Obtener respuesta a P-5 (protección de la propia cuenta) y marcarla CONFIRMADA; si es C, agregar el error `LAST_ACTIVE_ADMIN` a specs y tasks con `/opsx:update`
- [x] 0.4 Obtener respuestas a P-6 (turnos de un odontólogo desactivado), P-7 (ficha junto con la cuenta) y P-8 (reactivar, sin borrado) y marcarlas CONFIRMADAS
- [x] 0.5 Obtener respuestas a P-9 (listado sin páginas), P-10 (datos de la ficha al crear) y P-11 (qué ve un no administrador en `/usuarios`) y marcarlas CONFIRMADAS
- [x] 0.6 Obtener respuestas a P-12 (rehash al iniciar sesión), P-13 (repositorio de profesionales ahora) y P-14 (un change o dos); si P-14 = B, partir con `/opsx:update` entre los grupos 6 y 7
- [x] 0.7 Si alguna respuesta difiere de la recomendación, ajustar specs, design y tasks; registrar las decisiones como DD-56 en adelante en `knowledge-base/09_decisiones_y_supuestos.md`; verificar `openspec validate user-management --strict` en verde

## 1. Preparación y línea base

- [x] 1.1 Safety net: correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/`, `ruff check` y en el frontend `npm test`, `npm run typecheck` y `npm run lint`; anotar los números en verde (C-03 dejó 424 por defecto, 161 de integración y 40 de frontend); si algo falla, frenar y reportarlo como falla previa

## 2. Dominio de usuarios (puro) — spec user-management

- [x] 2.1 RED: `tests/unit/domain/users/test_rules.py` para `normalize_email` (recorta y pasa a minúsculas) e `is_valid_email` (válido; sin `@`; dos `@`; con espacio; 2 y 255 caracteres; nada antes o después del `@`); ejecutar y ver que falla
- [x] 2.2 GREEN → TRIANGULATE → REFACTOR: `app/domain/users/rules.py`; verificar en verde y `tests/unit/test_architecture.py` en verde
- [x] 2.3 RED: tests de `check_role_change` (P-4, P-5): admin↔recepción permitido; recepción→dentist permitido; dentist→recepción y dentist→admin `RoleChangeNotAllowedError`; mismo rol sin error; cambio del propio rol `SelfModificationError` (aunque sea a un rol permitido); y de `check_can_deactivate(is_self)`; ver que fallan
- [x] 2.4 GREEN → TRIANGULATE → REFACTOR: reglas y `app/domain/users/errors.py` (`USER_NOT_FOUND`, `EMAIL_TAKEN`, `ROLE_CHANGE_NOT_ALLOWED`, `SELF_MODIFICATION_NOT_ALLOWED`, todos `DomainError` con mensajes de la spec frontend); verificar en verde
- [x] 2.5 RED → GREEN: `professional_for_new_dentist` (P-10): nombre a mostrar enviado se usa recortado; vacío o ausente toma el nombre completo; matrícula vacía queda en `None`
- [x] 2.6 Tipos `NewAccount`, `NewProfessional`, `AccountChanges` en `app/domain/users/types.py`; ampliar el Protocol `UserAccountRepository` con `list_all`, `create` y `update` (design D-2); `app/domain/professionals/` con `Professional` y `ProfessionalRepository` (D-8); verificar `mypy --strict app/` (fallará en las implementaciones hasta el grupo 3: anotarlo)

## 3. Repositorio de cuentas con escritura — spec user-account-repository

- [x] 3.1 RED: ampliar `tests/contract/test_user_account_repository.py` con los escenarios nuevos (listado ordenado, inactivas incluidas, vacío; crear recepcionista; crear odontólogo con ficha; email duplicado con otras mayúsculas → `EMAIL_TAKEN`; falla en la ficha no deja la cuenta; cambiar nombre y email; email de otra cuenta; pasar a dentist crea ficha; desactivar odontólogo desactiva ficha; cambiar hash; id inexistente y mal formado → `USER_NOT_FOUND`) con la fábrica `in_memory`; ver que falla
- [x] 3.2 GREEN: `InMemoryUserAccountRepository` con almacén de fichas y simulación de la falla de ficha para la batería; verificar en verde con `in_memory`
- [x] 3.3 RED: correr la batería con la fábrica `postgres` (`pytest -m integration`); ver que falla
- [x] 3.4 GREEN: `SqlAlchemyUserAccountRepository.list_all/create/update` con una transacción por operación, `flush` para el id, `IntegrityError` de `uq_users_email_lower` → `EmailTakenError` (D-3); verificar la batería en verde con ambas fábricas y `tests/contract/test_import_order.py` en verde
- [x] 3.5 REFACTOR: extraer el mapeo modelo→`UserAccount` compartido; batería en verde

## 4. Repositorio de profesionales — spec professional-repository

- [x] 4.1 RED: `tests/contract/test_professional_repository.py` (listado ordenado, solo activas, vacío, por id existente, inexistente, mal formado) con `in_memory`; ver que falla
- [x] 4.2 GREEN: `app/infrastructure/in_memory/professionals.py`; verificar en verde
- [x] 4.3 RED → GREEN: fábrica `postgres` y `app/infrastructure/db/repositories/professionals.py` (orden `lower(display_name)`, `parse_uuid`); exportar en `repositories/__init__.py`; batería en verde con ambas fábricas

## 5. Casos de uso — specs user-management y user-authentication

- [x] 5.1 RED: `tests/unit/application/test_users.py` con el repo en memoria: alta normaliza email y guarda hash (no el texto); alta de dentist con ficha y sin nombre a mostrar; campos de ficha ignorados en otro rol; edición de nombre/email; email propio con otras mayúsculas; cambio de rol a dentist crea ficha; dentist→otro rechazado; propio rol rechazado; desactivar/reactivar idempotentes y con la ficha; desactivarse a sí mismo rechazado; set_password cambia el hash; id inexistente → `USER_NOT_FOUND`; ver que fallan
- [x] 5.2 GREEN → TRIANGULATE → REFACTOR: `app/application/users.py` (D-4); verificar en verde
- [x] 5.3 RED: tests de rehash en `tests/unit/application/test_auth.py` (D-7): hash con parámetros débiles se actualiza tras login correcto; hash al día no cambia; login fallido no cambia el hash; falla del `update` no impide el login; ver que fallan
- [x] 5.4 GREEN: `needs_rehash` en `app/core/security.py` (test propio en `tests/unit/core/test_security.py`) y rehash en `authenticate`; verificar en verde junto con los tests existentes del login

## 6. API — specs user-management y error-model

- [x] 6.1 RED: tests de `tests/unit/api/test_error_handlers.py` para `USER_NOT_FOUND` (404) y `EMAIL_TAKEN`, `ROLE_CHANGE_NOT_ALLOWED`, `SELF_MODIFICATION_NOT_ALLOWED` (409, sin `WWW-Authenticate`); y para el 422 sin `input` ni `ctx` (una contraseña enviada no aparece en el cuerpo, en un alta y en el login); ver que fallan
- [x] 6.2 GREEN: ampliar `STATUS_BY_CODE` y registrar el manejador de `RequestValidationError` (D-6) en `app/api/errors.py`; verificar en verde junto con los escenarios archivados de error-model y de login
- [x] 6.3 RED: `tests/unit/api/test_users_permissions.py`: tabla parametrizada de cada endpoint (`GET /users`, `POST /users`, `PATCH /users/{id}`, `POST .../deactivate`, `POST .../reactivate`, `PUT .../password`) × admin (2xx), recepción (403), odontólogo (403), sin token (401); verificar que un 403 no modificó datos; ver que falla
- [x] 6.4 RED: `tests/unit/api/test_users.py` con los escenarios de la spec user-management (alta 201 sin hash, email repetido 409, contraseña de 7 → 422, email mal formado 422, rol inexistente 422, alta de dentist con ficha, PATCH nombre/email/rol, 404 por id inexistente y mal formado, desactivar y login rechazado, token vigente de cuenta desactivada → 401, reactivar, desactivarse a sí mismo 409, password 204 y login con la nueva, 129 caracteres 422); ver que fallan
- [x] 6.5 GREEN: `app/api/users.py` (router con `require_role(Role.ADMIN)`, esquemas Pydantic de D-5, `ManagedUserOut` sin hash) e inclusión en `app/api/router.py`; verificar 6.3, 6.4 y `tests/unit/api/test_route_inventory.py` en verde
- [x] 6.6 REFACTOR: validadores compartidos (recorte, email) entre `auth.py` y `users.py` si corresponde; todo en verde
- [x] 6.7 Integración `tests/integration/test_user_management.py`: alta real de odontólogo contra PostgreSQL (cuenta y ficha en la base), login con esa cuenta; desactivar → login 401 y ficha inactiva; email repetido con otras mayúsculas → 409; verificar con `pytest -m integration`
- [x] 6.8 Verificar que `/openapi.json` lista las seis operaciones de `/users` con el esquema `HTTPBearer`; `mypy --strict app/`, `ruff check` y `pytest` completo en verde

## 7. Frontend — spec frontend-user-management

- [x] 7.1 RED: `src/api/users.test.ts`: cada función llama al endpoint y método correctos con `Authorization`, devuelve los datos tipados y ante 4xx lanza `ApiError` con `status` y `code`; ver que falla
- [x] 7.2 GREEN → REFACTOR: `src/api/users.ts` sin `any`; verificar en verde
- [x] 7.3 RED: tests de acceso: el enlace "Usuarios" aparece solo para admin en `/agenda`; un odontólogo en `/usuarios` ve "No tenés permiso para esta acción" sin llamar a `GET /users` y conserva la sesión; sin sesión va a `/login`; ver que fallan
- [x] 7.4 GREEN: `RequireRole`, ruta `/usuarios` en `src/App.tsx` y enlace en `AgendaPlaceholderPage`; verificar en verde
- [x] 7.5 RED: tests de `UsersPage`: "Cargando…", tabla con roles en castellano y "Inactivo", error de red; alta de odontóloga con campos de ficha; campos de ficha ocultos para recepción; 409 `EMAIL_TAKEN` conserva email y nombre y vacía la contraseña; 422 con su mensaje; envío doble; ver que fallan
- [x] 7.6 GREEN → REFACTOR: `UsersPage`, `UserForm` y `messages.ts`; verificar en verde
- [x] 7.7 RED → GREEN: editar (selector de rol bloqueado para odontólogo, propia fila sin "Desactivar" ni cambio de rol, rechazo 409 mantiene datos, `USER_NOT_FOUND` recarga), desactivar con confirmación y cancelación, reactivar, asignar contraseña ("Contraseña actualizada" y campo vacío); verificar que la contraseña no queda en `sessionStorage` ni `localStorage`
- [x] 7.8 Verificar `npm test`, `npm run typecheck` y `npm run lint` en verde

## 8. Cierre

- [x] 8.1 Prueba manual con Docker: seed, entrar como admin, crear una odontóloga, entrar con ella, desactivarla y comprobar que no entra; reactivarla; probar que la recepción no ve "Usuarios"
- [x] 8.2 Suite completa en verde (backend por defecto e integración, frontend, mypy, ruff, tsc, eslint); anotar números finales
- [x] 8.3 Actualizar `CHANGES.md` (estado de C-04, notas para C-07/C-08 sobre el repositorio de profesionales y las fichas inactivas) y verificar `openspec validate user-management --strict`
