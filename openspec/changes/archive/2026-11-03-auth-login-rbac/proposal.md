# Proposal: auth-login-rbac (C-03)

> **Gobernanza CRÍTICA** (autenticación y autorización). Este change solo propone: no se escribe código hasta que el usuario confirme las decisiones P-1 a P-15 de `design.md` (grupo 0 de `tasks.md`).

## Why

Hoy la API solo tiene el chequeo de salud público y no hay forma de saber quién llama: cualquier endpoint que agreguen C-04, C-06, C-07 y C-08 quedaría abierto. RN-AU-01 exige sesión en todo salvo el login, y como no hay RLS (DD-02) la única barrera es la aplicación. C-02 ya dejó la tabla `users`, el seed con 4 cuentas y `hash_password` (DD-41); falta verificar contraseñas, emitir y validar el JWT (DD-11) y dar a los changes siguientes dependencias reutilizables para exigir sesión y rol.

## What Changes

- **Login** `POST /api/v1/auth/login` (email + contraseña): verifica el hash argon2, rechaza `users.active = false` (RN-AU-03) y devuelve un JWT de acceso firmado (HS256) con el id del usuario, su rol y vencimiento corto. Ante credenciales inválidas o usuario inactivo responde un error genérico, sin revelar cuál dato falló (Flujo 1).
- **Sesión actual** `GET /api/v1/auth/me`: devuelve los datos mínimos del usuario autenticado (sin hash ni secretos).
- **Seguridad en `app/core/security.py`**: se suman `verify_password`, `create_access_token` y `decode_access_token` con PyJWT y argon2-cffi (sin python-jose ni passlib).
- **Dependencias de FastAPI** `current_user()` y `require_role(...)`: toda ruta salvo el login y `GET /api/v1/health` exige un JWT válido; `current_user()` recarga el usuario desde la base en cada request y rechaza usuarios desactivados o con el rol cambiado (el token no es la fuente de verdad del rol).
- **Alcance propio del odontólogo** (RN-AU-04): regla pura en `app/domain/auth/` y una dependencia reutilizable para que C-07 y C-08 la apliquen a horarios y turnos.
- **Inventario de rutas**: un test recorre todas las rutas de la app y falla si alguna (salvo las públicas permitidas) no exige sesión. Es la red de seguridad que reemplaza a la RLS (riesgo R-6).
- **Repositorio de cuentas** (solo lectura): buscar usuario por email (sin distinguir mayúsculas) y por id, con el profesional asociado si es odontólogo; puerto en el dominio, implementación en memoria y en PostgreSQL, batería de contrato.
- **Errores**: códigos nuevos `INVALID_CREDENTIALS` y `NOT_AUTHENTICATED` (401) y `FORBIDDEN` (403) en el formato uniforme `{"error": {...}}`.
- **Frontend**: pantalla `/login`, guardado del token (memoria o `sessionStorage`, P-2), rutas protegidas, redirección a `/agenda` (página provisoria hasta C-10), botón para salir y vuelta al login ante un 401. El indicador de estado de la API pasa a la pantalla de login.
- **Sin variables de entorno nuevas**: `JWT_ALGORITHM` y `ACCESS_TOKEN_EXPIRE_MINUTES` ya existen y se validan desde C-01 (salvo que P-3 elija limitar intentos).
- Dependencias nuevas: `PyJWT` (backend) y `react-router` (frontend, P-14).

## Capabilities

### New Capabilities
- `user-authentication`: login con email y contraseña, emisión y verificación del JWT de acceso y endpoint de sesión actual.
- `access-control`: exigencia de sesión en toda ruta no pública, recarga del usuario en cada request, chequeo de rol (`require_role`), alcance propio del odontólogo e inventario de rutas protegido por test.
- `user-account-repository`: puerto de solo lectura de cuentas de usuario (por email y por id, con profesional asociado), con implementación en memoria y PostgreSQL y batería de contrato.
- `frontend-auth`: pantalla de login, guardado del token, rutas protegidas, redirección por rol y cierre de sesión en el frontend.

### Modified Capabilities
- `error-model`: la tabla de códigos a estados HTTP suma `INVALID_CREDENTIALS` y `NOT_AUTHENTICATED` (401) y `FORBIDDEN` (403); los errores de autenticación usan el mismo cuerpo uniforme.
- `frontend-shell`: el estado de la API ya no se muestra en una pantalla inicial pública propia, sino en la pantalla de login.

## Impact

- **Backend**: `app/core/security.py`, `app/core/errors.py` (nuevos errores), `app/api/errors.py` (tabla de estados), `app/api/auth.py` (nuevo router), `app/api/dependencies.py` (nuevo), `app/api/router.py`, `app/domain/auth/` (nuevo: roles, principal, regla de alcance, puerto), `app/infrastructure/db/repositories/users.py`, `app/infrastructure/in_memory/users.py`, tests unitarios, de API, de contrato y de integración.
- **Frontend**: `src/App.tsx` pasa a enrutar; nuevos módulos de sesión, cliente HTTP con `Authorization: Bearer`, pantalla de login y página provisoria de agenda; tests de Vitest.
- **Dependencias**: `PyJWT>=2.10,<3` en `pyproject.toml` (requiere reconstruir la imagen del backend); `react-router` en `package.json`.
- **KB**: al confirmar P-1..P-15 se registran DD nuevas (desde DD-45) y se actualizan SU-06 y SU-07 en `09_decisiones_y_supuestos.md` / `10_preguntas_abiertas.md`.
- **Sin cambios** en el esquema de la base ni en las migraciones (salvo que P-3 elija bloqueo de cuentas, que no se recomienda).
- **Changes siguientes**: C-04, C-06, C-07 y C-08 usan `require_role` y la regla de alcance propio; cada endpoint nuevo debe registrarse en el inventario de rutas y llevar su test de permisos por rol.
