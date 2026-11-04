# Design: user-management (C-04)

> **Gobernanza ALTA.** Las decisiones P-1 a P-14 fueron **RESUELTAS** por la usuaria el 2026-11-03: eligió la opción recomendada en todas (registradas como DD-56 a DD-61 en `knowledge-base/09_decisiones_y_supuestos.md`). Las specs ya reflejan esas opciones.

## Context

Motivación en `proposal.md`. Estado real del código (verificado el 2026-11-03):

- **Esquema** (C-02): `users` (`id` UUID, `email` con índice único `uq_users_email_lower` sobre `lower(email)`, `password_hash`, `full_name`, `role` enum `user_role`, `active`) y `professionals` (`id`, `user_id` `NOT NULL UNIQUE` FK, `display_name` `NOT NULL`, `license_number` nulable, `active`). Claves `ON DELETE RESTRICT` (DD-39). **No hace falta ninguna migración.**
- **Autenticación** (C-03): `app/core/security.py` tiene `hash_password` y `verify_password` (argon2-cffi, `PasswordHasher()` por defecto), `create/decode_access_token`. `app/api/dependencies.py` tiene `get_user_repository` (sobreescribible en tests), `current_user` (recarga la cuenta en cada request y da 401 si está inactiva o cambió el rol: DD-45, DD-51) y `require_role(*roles)`.
- **Repositorio de cuentas** (C-03): puerto `UserAccountRepository` en `app/domain/auth/ports.py` con solo `get_by_email` y `get_by_id`; `InMemoryUserAccountRepository` (con un `add` para tests) y `SqlAlchemyUserAccountRepository` (abre una sesión por llamada con `session_factory`, join externo a `professionals`, `parse_uuid` para ids mal formados). Batería de contrato `tests/contract/test_user_account_repository.py` con fábricas `in_memory` y `postgres`.
- **No existe** puerto ni repositorio de profesionales; tampoco unidad de trabajo (DD-36 la deja para C-08).
- **Errores**: `app/api/errors.py` con `STATUS_BY_CODE` (default 400) y cuerpo `{"error": {...}}`. El 422 de validación todavía usa el manejador por defecto de FastAPI, que con Pydantic v2 incluye `input` (el valor enviado) en cada error: **un alta con email inválido devolvería la contraseña en el cuerpo del 422**. Este change lo corrige (spec error-model).
- **Inventario de rutas** (`tests/unit/api/test_route_inventory.py`): toda ruta nueva debe depender de `current_user` (lo cumple `require_role`).
- **Frontend**: React 19 + TS + `react-router` (DD-54); `src/api/client.ts` con `apiFetch` (agrega el token; 401 cierra sesión, 403 la conserva) y `messageForStatus`; `AuthProvider`/`useAuth` exponen `user` con `role`; rutas `/login` y `/agenda` (provisoria).
- **KB**: US-002 (crear, editar, desactivar; alta de `dentist` crea profesional), RBAC "Usuarios/roles: CRUD solo admin", RN-AU-02/03, DD-38 (todo profesional tiene cuenta `dentist`; email único sin mayúsculas), DD-39 (baja = `active = false`), DD-53 (el ingreso lo decide `users.active`; un odontólogo con ficha inactiva ve lo suyo), DD-55 (rehash pendiente para C-04).
- La skill `revisor-escenarios-turnos` no aplica (no toca agenda ni turnos más allá de "no se modifican").

## Goals / Non-Goals

**Goals:**
- Gestión completa de cuentas por el administrador con reglas puras y testeables en `domain/`.
- Alta de odontólogo atómica (cuenta + ficha) sin introducir todavía una unidad de trabajo general.
- Ningún camino (respuesta, 422, log) que devuelva una contraseña o un hash.
- Repositorio de profesionales de lectura listo para C-07/C-08.

**Non-Goals:**
- Que cada usuario cambie su propia contraseña, recuperación por email, política de complejidad más allá del largo, límite de intentos (DD-47, C-13).
- Editar la ficha del profesional (nombre a mostrar, matrícula) después del alta, y la pantalla `/profesionales` (C-07).
- Cancelar o reasignar turnos de un odontólogo desactivado (C-08/C-10).
- Borrado físico de cuentas.
- Endpoints de profesionales (C-07).

## Decisiones pendientes (P-1 a P-14)

Cada pregunta en lenguaje simple, con opciones, la recomendada y por qué.

### P-1 — ¿Cómo se define la contraseña inicial de una cuenta nueva? — RESUELTA (opción A)
- **A (recomendada)**: la escribe el administrador en el formulario (entre 8 y 128 caracteres) y se la pasa a la persona en mano. El sistema la guarda solo "cifrada" (hash) y nunca la vuelve a mostrar.
- B: la genera el sistema al azar y la muestra **una sola vez** en la respuesta del alta.
- C: no se pone contraseña: la persona recibe un email con un enlace para elegirla.
**Por qué A**: CHANGES.md pide que la contraseña nunca aparezca en una respuesta; B la expone a propósito (queda en el historial del navegador, en capturas). C depende del proveedor SMTP, que todavía es una pregunta abierta de prioridad Alta (SU-02), y suma tokens de un solo uso. El mínimo de 8 es el usual; el máximo de 128 es el mismo del login (DD-50).

### P-2 — Si alguien olvida su contraseña, ¿el administrador puede asignarle una nueva? — RESUELTA (opción A)
- **A (recomendada)**: sí, con un botón "Asignar contraseña" en la pantalla de usuarios (mismo largo que P-1).
- B: no en C-04; queda para otro change.
**Por qué A**: no hay "olvidé mi contraseña" ni la habrá sin SMTP; sin esto, una contraseña olvidada obliga a tocar la base a mano. Es un endpoint chico que reusa `hash_password`. Que cada persona cambie su propia contraseña queda fuera (se puede sumar después).

### P-3 — ¿Se puede editar el email de una cuenta? — RESUELTA (opción A)
- **A (recomendada)**: sí, con la misma validación del alta y sin repetir el de otra cuenta. La sesión abierta sigue (el pase identifica a la cuenta por su id, no por el email); desde ese momento inicia sesión con el email nuevo.
- B: no; el email es fijo (para cambiarlo hay que crear otra cuenta).
**Por qué A**: el email es el "usuario" del login y los errores de tipeo al crear son comunes; con B, corregirlo obliga a desactivar y crear otra cuenta, y el email mal escrito queda ocupado para siempre.

### P-4 — ¿Se puede cambiar el rol de una cuenta? ¿Y si es odontólogo? — RESUELTA (opción B)
La KB dice que toda ficha de profesional pertenece a una cuenta de odontólogo (DD-38) y que los turnos nunca se borran (DD-39).
- A: solo se cambia entre administrador y recepción; nada entra ni sale de odontólogo.
- **B (recomendada)**: entre administrador y recepción, libre; de administrador o recepción **a** odontólogo, sí, y se crea su ficha en ese momento; **de** odontólogo a otro rol, no (error "No se puede cambiar el rol de un odontólogo").
- C: todo permitido; si un odontólogo deja de serlo, su ficha queda desactivada.
**Por qué B**: permite corregir el error más común (crear como recepción a quien era odontóloga) sin dejar fichas "huérfanas": una ficha con turnos siempre sigue perteneciendo a un odontólogo, y la historia de sus turnos queda intacta. C rompe la regla de DD-38 y deja a alguien que ya no es odontólogo como dueño de una agenda. A obliga a crear otra cuenta (con otro email) para corregir un error de carga. Con cualquier opción, si la persona tenía la sesión abierta, su siguiente clic le pide volver a entrar (ya decidido en C-03, DD-51).

### P-5 — ¿El administrador puede desactivarse o quitarse el rol a sí mismo? — RESUELTA (opción A)
- **A (recomendada)**: no. Ni desactivar su propia cuenta ni cambiar su propio rol. Así siempre queda al menos un administrador activo (el único que podría quitar al último es él mismo).
- B: sí, con una advertencia en pantalla.
- C: se permite, pero el sistema verifica además que quede al menos otro administrador activo.
**Por qué A**: con B el consultorio podría quedarse sin nadie que gestione usuarios y habría que arreglarlo con el seed o a mano en la base. A es una regla simple que ya alcanza; C agrega una consulta y un error más para el mismo resultado. Un administrador sí puede desactivar a **otro** administrador. (Caso extremo aceptado: dos administradores desactivándose mutuamente en el mismo segundo; ver Riesgos.)

### P-6 — Si se desactiva a un odontólogo que tiene turnos a futuro, ¿qué pasa con esos turnos? — RESUELTA (opción A)
- **A (recomendada)**: se permite desactivarlo y los turnos quedan como están; la pantalla avisa al confirmar: "Sus turnos futuros no se cancelan: recepción debe reprogramarlos o cancelarlos".
- B: no se permite desactivarlo mientras tenga turnos futuros (primero hay que moverlos).
- C: al desactivarlo se cancelan automáticamente sus turnos futuros (y se avisa a los pacientes).
**Por qué A**: es coherente con lo que ya se decidió para pacientes (DD-25: desactivar no cancela turnos) y no mete en C-04 la lógica de turnos y emails, que es de C-08 y C-11. C toma una decisión delicada (avisar a pacientes) sin que nadie la revise. B puede bloquear una baja urgente.

### P-7 — Al desactivar la cuenta de un odontólogo, ¿se desactiva también su ficha de profesional? — RESUELTA (opción A)
- **A (recomendada)**: sí, las dos juntas; y al reactivar la cuenta, se reactivan las dos.
- B: no; la cuenta y la ficha son independientes (la ficha se maneja en C-07).
**Por qué A**: así un odontólogo que se fue deja de aparecer como opción para dar turnos nuevos (C-08 listará solo fichas activas), sin un segundo paso que alguien se puede olvidar. Su historial no se pierde (DD-53: con la ficha inactiva, si vuelve, sigue viendo lo suyo).

### P-8 — ¿Se puede reactivar una cuenta? ¿Hay borrado definitivo? — RESUELTA (opción A)
- **A (recomendada)**: se puede desactivar y reactivar las veces que haga falta; **no** hay borrado definitivo.
- B: además, borrado definitivo para cuentas sin historia (sin turnos creados ni ficha con turnos).
**Por qué A**: DD-39 ya dice que la baja es marcar `active = false` y la base impide borrar lo que tiene historia; un botón "borrar" que a veces funciona y a veces no confunde. Reactivar cubre a quien vuelve (licencia larga, error).

### P-9 — ¿El listado de usuarios necesita páginas o filtros? — RESUELTA (opción A)
- **A (recomendada)**: no. Se muestran todas las cuentas (activas e inactivas) ordenadas por nombre, en una sola tabla.
- B: páginas de 20 y filtros por rol y estado en la API.
**Por qué A**: un consultorio tiene pocas cuentas (decenas como mucho). B suma parámetros, tests y pantalla sin beneficio real. Si hiciera falta, se agrega después sin romper nada.

### P-10 — ¿Qué datos de la ficha de profesional se piden al crear un odontólogo? — RESUELTA (opción A)
La ficha tiene "nombre a mostrar" (obligatorio) y "matrícula" (opcional, ficticia).
- **A (recomendada)**: en el mismo formulario del alta aparecen "Nombre a mostrar" (si se deja vacío, se usa el nombre completo) y "Matrícula" (opcional). Editarlos después queda para C-07 (pantalla `/profesionales`).
- B: no se pide nada; la ficha se crea con el nombre completo y sin matrícula, y todo se completa en C-07.
- C: como A, y además se pueden editar desde `/usuarios` en C-04.
**Por qué A**: deja la ficha completa en un solo paso sin meterse en la pantalla de profesionales de C-07. C duplica lo que C-07 va a hacer.

### P-11 — Si alguien que no es administrador escribe `/usuarios` en el navegador, ¿qué ve? — RESUELTA (opción A)
- **A (recomendada)**: el mensaje "No tenés permiso para esta acción" con un enlace a la agenda, sin cerrar su sesión. El enlace "Usuarios" solo lo ve el administrador.
- B: lo manda directamente a `/agenda` sin mensaje.
**Por qué A**: es el mismo mensaje que ya usa el sistema ante un 403 (spec frontend-auth) y explica qué pasó. De todos modos la protección real está en la API (403).

### P-12 — ¿Aprovechamos para "actualizar" las contraseñas guardadas al iniciar sesión? — RESUELTA (opción A)
(Quedó anotado en C-03, DD-55.) El método de cifrado tiene parámetros que con los años conviene subir. Si se suben, las contraseñas viejas siguen funcionando pero quedan con el cifrado anterior.
- **A (recomendada)**: sí. Cuando alguien inicia sesión bien y su contraseña está guardada con parámetros viejos, se guarda de nuevo con los actuales. Si eso falla, igual entra.
- B: no; queda para otro change.
**Por qué A**: es lo que recomienda la documentación de argon2-cffi y necesita justo lo que C-04 agrega (escribir en `users`). Es invisible para la persona que entra.

### P-13 — ¿Creamos ya el "repositorio de profesionales" (leer fichas)? — RESUELTA (opción A)
CHANGES.md dice que se define "en C-04 o en C-07".
- **A (recomendada)**: sí, en C-04, mínimo: listar fichas (todas o solo activas) y buscar una por id, con su batería de contrato en memoria y PostgreSQL. Sin endpoints (los agrega C-07).
- B: no; lo hace C-07 cuando arme `/profesionales`.
**Por qué A**: C-04 es el que crea fichas, así que es el momento natural de fijar cómo se leen; C-07 y C-08 lo usan sin redefinirlo. Es chico (dos métodos).

### P-14 — ¿Hacemos C-04 de una vez o lo partimos? — RESUELTA (opción A)
- **A (recomendada)**: un solo change, por grupos (dominio → repositorios → casos de uso → API → frontend), como C-02 y C-03.
- B: C-04a (backend) y C-04b (pantalla `/usuarios`).
**Por qué A**: es más chico que C-03 y la pantalla depende solo de estos endpoints. Si se elige B, el corte natural es entre los grupos 6 y 7 de `tasks.md`.

**Ya decidido (no se pregunta)**: el pase de sesión de una cuenta desactivada o con el rol cambiado deja de valer en su siguiente llamada (401), porque `current_user` relee la cuenta en cada request (DD-45, DD-51, spec access-control). No hace falta lista negra de tokens.

## Decisions

Decisiones técnicas (no de dominio). Si una respuesta P-n las afecta, se indica.

### D-1 — Capas
- `app/domain/users/` (puro, vigilado por `test_architecture.py`):
  - `types.py`: `NewAccount` (email, full_name, password_hash, role, `professional: NewProfessional | None`), `NewProfessional` (display_name, license_number), `AccountChanges` (campos opcionales: full_name, email, role, active, password_hash; `new_professional` para el paso a `dentist`).
  - `rules.py`: `normalize_email(text) -> str` (recorta, minúsculas) y `is_valid_email(text) -> bool` (3..254, un `@`, sin espacios, texto a ambos lados); `check_role_change(current, new, *, is_self)` (P-4, P-5); `check_can_deactivate(*, is_self)` (P-5); `professional_for_new_dentist(full_name, display_name, license_number) -> NewProfessional` (P-10: nombre a mostrar vacío → nombre completo).
  - `errors.py`: `UserNotFoundError` (`USER_NOT_FOUND`), `EmailTakenError` (`EMAIL_TAKEN`), `RoleChangeNotAllowedError` (`ROLE_CHANGE_NOT_ALLOWED`), `SelfModificationError` (`SELF_MODIFICATION_NOT_ALLOWED`), todos `DomainError`.
- `app/domain/professionals/`: `Professional` (id, user_id, display_name, license_number, active) y puerto `ProfessionalRepository` (`list(*, only_active: bool = False)`, `get_by_id`) (P-13).
- `app/application/users.py`: caso de uso `gestionar_usuarios` como funciones `list_users`, `create_user`, `update_user`, `deactivate_user`, `reactivate_user`, `set_password` que reciben el `Principal` del administrador (para las reglas de "sí mismo"), el repositorio y, si corresponde, el hasher. Hashean con `hash_password`; nunca devuelven el hash al API.
- `app/api/users.py`: router `/users` con `dependencies=[Depends(require_role(Role.ADMIN))]` a nivel router y el `Principal` inyectado en las operaciones que lo necesitan.
**Alternativa**: lógica en el router. Descartada: las reglas quedarían sin tests puros y acopladas a FastAPI.

### D-2 — Puerto de escritura: ampliar `UserAccountRepository`
Se amplía el Protocol existente con `list_all()`, `create(NewAccount) -> UserAccount` y `update(user_id, AccountChanges) -> UserAccount`. Un solo `update` con cambios opcionales (en vez de `set_active`, `set_password_hash`, etc.) mantiene la superficie chica y permite que el repositorio aplique en la misma transacción los efectos sobre la ficha (activo junto con la cuenta, P-7; ficha nueva al pasar a `dentist`, P-4).
**Alternativa**: un puerto nuevo `UserWriteRepository`. Descartada: duplicaría la fábrica, el override en tests y la batería; el login seguiría usando solo los dos métodos de lectura.
**Efecto**: `InMemoryUserAccountRepository.add` deja de ser solo para tests (se mantiene como atajo de fixtures) y el repo en memoria guarda también fichas para emular la transacción.

### D-3 — Atomicidad cuenta + ficha sin unidad de trabajo
`SqlAlchemyUserAccountRepository.create/update` abren **una** sesión con `with session_factory() as session, session.begin():`, insertan/actualizan `UserModel`, hacen `flush()` (para obtener el id generado por la base, DD-37) e insertan/actualizan `ProfessionalModel` en la misma transacción; cualquier excepción hace rollback de todo. La unicidad del email la garantiza el índice `uq_users_email_lower`: se captura `IntegrityError` con ese nombre de constraint y se traduce a `EmailTakenError` (el chequeo previo en la aplicación no alcanza ante dos altas simultáneas). Otras `IntegrityError` se relanzan.
**Test de atomicidad**: en integración, se fuerza la falla de la ficha (por ejemplo, `display_name` nulo inyectado salteando la validación del dominio, o un hook de prueba antes del insert de la ficha) y se verifica que no queda la fila `users`. En memoria, la batería usa una fábrica que puede fallar en la ficha.
**Alternativa**: unidad de trabajo general. Descartada por DD-36 (va en C-08); acá alcanza un método atómico.

### D-4 — Reglas del caso de uso
- **Alta**: normalizar email → validar → `hash_password` → si rol `dentist`, armar `NewProfessional` (P-10) → `repo.create`. Campos de ficha enviados con otro rol se ignoran (spec: "Recepcionista sin ficha").
- **Edición**: cargar la cuenta (`USER_NOT_FOUND` si no existe o el id es inválido) → `check_role_change` → si pasa a `dentist` y no tiene ficha, `NewProfessional` con su nombre → `repo.update`. Mismo rol = sin cambio. Email igual al propio con otras mayúsculas = válido (la comparación de unicidad excluye la misma cuenta).
- **Desactivar/reactivar**: cargar → `check_can_deactivate(is_self)` (solo al desactivar) → `repo.update(active=...)` (idempotente).
- **Contraseña**: cargar → `hash_password` → `repo.update(password_hash=...)`.
- Las reglas de "sí mismo" comparan `principal.user_id` con el id pedido.

### D-5 — Contrato HTTP
- `GET /users` → 200 `list[ManagedUserOut]`: un esquema propio (id, email, full_name, role, active, professional_id). No se toca el `UserOut` de `/auth/me`, cuyos campos fijó DD-51.
- `POST /users` → 201 `ManagedUserOut`. Body: `email` (BeforeValidator que recorta; 3..254; validación `is_valid_email` en un `AfterValidator`), `full_name` (recorta, 1..200), `role` (`Literal["admin","receptionist","dentist"]`), `password` (8..128, sin recortar), `display_name` (opcional, recorta, 1..200), `license_number` (opcional, recorta, 1..50).
- `PATCH /users/{user_id}` → 200 `ManagedUserOut`. Body con `full_name`, `email`, `role` opcionales; `model_fields_set` distingue "no enviado".
- `POST /users/{user_id}/deactivate` y `/reactivate` → 200 `ManagedUserOut`.
- `PUT /users/{user_id}/password` → 204. Body `password` (8..128).
- Se evita `EmailStr` para no sumar `email-validator` (mismo criterio que D-9 de C-03).
- `user_id` es `str` en la ruta: un id mal formado llega al repositorio, que lo trata como inexistente → 404 `USER_NOT_FOUND`.

### D-6 — 422 sin valores enviados (Context7: `/websites/fastapi_tiangolo`, consultado el 2026-11-03)
La documentación confirma que se puede reemplazar el manejador de `RequestValidationError` con `app.add_exception_handler`. En `app/api/errors.py` se registra uno que responde 422 con `{"detail": [{"loc", "msg", "type"} ...]}`: mismo formato que FastAPI (sin uniformar, DD-49) pero **sin** las claves `input` ni `ctx`, que en Pydantic v2 repiten el valor enviado. Aplica a toda la API (login incluido). El test verifica que el texto de la contraseña no aparece en el cuerpo.

### D-7 — Rehash en el login (P-12)
`authenticate` en `app/application/auth.py`: tras verificar bien la contraseña de una cuenta activa, si `needs_rehash(account.password_hash)` (nueva función en `core/security.py` que envuelve `PasswordHasher.check_needs_rehash`, ya consultada en C-03 con Context7 `/hynek/argon2-cffi`), llama a `repo.update(account.id, AccountChanges(password_hash=hash_password(password)))` dentro de `try/except Exception` con un `logger.warning` sin datos sensibles. Test: hash generado con un `PasswordHasher(time_cost=1, memory_cost=8)` (parámetros débiles) → después del login el hash guardado tiene los parámetros por defecto.

### D-8 — Repositorio de profesionales (P-13)
`app/infrastructure/in_memory/professionals.py` y `app/infrastructure/db/repositories/professionals.py` (`select(ProfessionalModel)`, orden `lower(display_name)`, `parse_uuid`). Batería `tests/contract/test_professional_repository.py` con fábricas `in_memory` y `postgres`. Para que en memoria cuentas y fichas sean coherentes, el repositorio en memoria de profesionales puede leer del mismo almacén que el de cuentas (la fábrica de la batería arma ambos).

### D-9 — Frontend
- `src/api/users.ts`: funciones tipadas (`listUsers`, `createUser`, `updateUser`, `deactivateUser`, `reactivateUser`, `setPassword`) sobre `apiFetch`, con un tipo `ApiError` que lleva `status` y `code`. Sin `any`.
- `src/pages/UsersPage.tsx` + `src/users/UserForm.tsx`, `src/users/PasswordForm.tsx`; `src/users/messages.ts` mapea `error.code` → texto (spec). Confirmación con `window.confirm` (simple, testeable con `vi.spyOn`).
- Ruta `/usuarios` dentro de `RequireAuth`; el chequeo de rol vive en un componente `RequireRole` (si `user.role !== 'admin'` muestra el aviso de P-11 sin llamar a la API).
- Enlace "Usuarios" en `AgendaPlaceholderPage` solo para `admin`.
- `vercel-react-best-practices` (solo React): componentes fuera de otros componentes, estado derivado sin `useEffect` innecesarios, ternarios en vez de `&&` con números. `frontend-design`: tabla y formularios sobrios y accesibles (labels asociados, `role="alert"` para errores, foco visible).

### D-10 — Tests de API sin base
Como en C-03 (D-10): los tests de `tests/unit/api/test_users.py` sobreescriben `get_user_repository` con el repositorio en memoria. Una tabla parametrizada recorre **cada** endpoint × (admin, recepción, odontólogo, sin token) para el test de permisos por rol (regla dura 4). Integración: alta de odontólogo real contra PostgreSQL + login con esa cuenta; desactivar + login rechazado.

## Risks / Trade-offs

- [El 422 de FastAPI devuelve lo enviado, incluida la contraseña] → manejador propio sin `input`/`ctx` (D-6), con test.
- [Dos altas simultáneas con el mismo email] → el índice único de la base decide; `IntegrityError` → `EMAIL_TAKEN` (D-3).
- [Dos administradores se desactivan mutuamente en el mismo instante y no queda ninguno] → aceptado (P-5 A); se recupera con el seed o a mano. Bloquear filas no se justifica para un consultorio.
- [Un odontólogo desactivado deja turnos futuros "huérfanos"] → aviso en la confirmación (P-6 A); C-08/C-10 pueden marcar turnos de fichas inactivas.
- [Contraseñas iniciales débiles elegidas por el administrador] → mínimo 8; política más fuerte y límite de intentos se revisan en C-13 (DD-47).
- [El administrador ve qué emails existen (`EMAIL_TAKEN`)] → aceptable: solo lo ve el rol `admin`.
- [Rehash falla y no se nota] → se registra un warning sin datos; el login sigue (D-7).
- [Ampliar el Protocol rompe implementaciones de prueba] → solo existen las dos implementaciones del repo; mypy `--strict` lo detecta.

## Migration Plan

1. Sin migraciones, sin variables de entorno nuevas (`.env.example` no cambia) y sin dependencias nuevas.
2. Para probar a mano: `docker compose up`, seed con `SEED_DEMO_PASSWORD`, entrar como administrador, ir a `/usuarios`, crear una odontóloga, cerrar sesión y entrar con ella; desactivarla y verificar que ya no entra.
3. Rollback: revertir el commit; las cuentas creadas quedan en la base y siguen funcionando con el login de C-03.

## Open Questions

Ninguna diferible: todas las decisiones abiertas están en P-1 a P-14 y bloquean el grupo 1 de `tasks.md`.
