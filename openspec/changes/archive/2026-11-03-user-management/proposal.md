# Proposal: user-management (C-04)

> **Gobernanza ALTA** (usuarios, roles y contraseñas). Este change solo propone: no se escribe código hasta que la usuaria confirme las decisiones P-1 a P-14 de `design.md` (grupo 0 de `tasks.md`).

## Why

Hoy las únicas cuentas son las cuatro del seed: no hay forma de dar de alta a una recepcionista u odontólogo nuevo, corregir un nombre o cortar el acceso de alguien que se fue sin tocar la base a mano. US-002 pide que el administrador cree, edite y desactive usuarios, y la matriz RBAC (`03_actores_y_roles.md`, DD-48) reserva esa gestión al rol `admin`. C-03 ya dejó el login, `current_user`, `require_role`, el hash argon2 y un repositorio de cuentas de solo lectura; falta la escritura y la pantalla.

## What Changes

- **API de usuarios** bajo `/api/v1/users`, solo para `admin` (`require_role(Role.ADMIN)`), con test de permisos por rol en cada endpoint:
  - `GET /users`: listado de cuentas (activas e inactivas) sin hash.
  - `POST /users`: alta con email, nombre, rol y contraseña inicial (P-1). La contraseña se guarda solo como hash argon2 y nunca aparece en ninguna respuesta.
  - `PATCH /users/{id}`: editar nombre, email (P-3) y rol (P-4).
  - `POST /users/{id}/deactivate` y `POST /users/{id}/reactivate`: baja y alta lógica (P-8); no hay borrado físico.
  - `PUT /users/{id}/password`: el administrador asigna una contraseña nueva (P-2).
- **Alta de odontólogo atómica**: al crear un usuario `dentist` se crea su fila `professionals` (nombre a mostrar y matrícula opcional, P-10) en la misma transacción; si una de las dos inserciones falla, no queda ninguna.
- **Reglas de dominio puras** en `app/domain/users/`: email normalizado y único sin distinguir mayúsculas (DD-38), cambios de rol permitidos (P-4), protección de la propia cuenta, que garantiza que siempre quede un administrador activo (P-5), efecto sobre la ficha del profesional al desactivar (P-6, P-7).
- **Repositorio de cuentas con escritura**: el repositorio de C-03 suma listar, crear (con ficha), actualizar, activar/desactivar y cambiar el hash, en memoria y PostgreSQL, con la batería de contrato ampliada.
- **Repositorio de profesionales mínimo** (solo lectura: listar y buscar por id) para que C-07 y C-08 no tengan que definirlo (P-13).
- **Rehash al iniciar sesión** con `check_needs_rehash` (pendiente de C-03, DD-55; P-12).
- **Errores nuevos** en el formato uniforme: `USER_NOT_FOUND` (404), `EMAIL_TAKEN`, `ROLE_CHANGE_NOT_ALLOWED`, `SELF_MODIFICATION_NOT_ALLOWED` (409).
- **Frontend**: pantalla `/usuarios` (solo admin) con listado, alta, edición, desactivar/reactivar y asignar contraseña; enlace visible solo para el administrador (P-11).
- **Sin cambios de esquema ni migraciones. Sin variables de entorno nuevas. Sin dependencias nuevas.**

## Capabilities

### New Capabilities
- `user-management`: gestión de cuentas por el administrador vía API (listar, crear, editar, desactivar, reactivar, asignar contraseña), alta atómica de la ficha del odontólogo y reglas de protección (propia cuenta, último administrador, cambios de rol).
- `professional-repository`: puerto de solo lectura de fichas de profesionales (listar y buscar por id) con implementación en memoria y PostgreSQL y batería de contrato.
- `frontend-user-management`: pantalla `/usuarios` del administrador y su acceso desde la navegación.

### Modified Capabilities
- `user-account-repository`: suma operaciones de escritura (listar, crear con ficha en una transacción, actualizar, activar/desactivar, cambiar hash) y el rechazo de emails duplicados.
- `error-model`: la tabla de códigos a estados HTTP suma `USER_NOT_FOUND` (404) y `EMAIL_TAKEN`, `ROLE_CHANGE_NOT_ALLOWED`, `SELF_MODIFICATION_NOT_ALLOWED` (409); el 422 de validación deja de repetir los valores enviados (para no devolver contraseñas).
- `user-authentication`: el login actualiza el hash de la contraseña cuando los parámetros de argon2 cambiaron (P-12).

## Impact

- **Backend**: `app/domain/users/` (nuevo: tipos, reglas, errores), `app/domain/auth/ports.py` (puerto con escritura) o un puerto nuevo (ver design D-2), `app/domain/professionals/` (puerto de lectura), `app/application/users.py` (caso de uso `gestionar_usuarios`), `app/application/auth.py` (rehash), `app/api/users.py` (router nuevo), `app/api/router.py`, `app/api/errors.py`, `app/api/dependencies.py`, `app/infrastructure/in_memory/` y `app/infrastructure/db/repositories/` (usuarios y profesionales), tests unitarios, de API, de contrato y de integración.
- **Frontend**: `src/pages/UsersPage.tsx` y componentes del formulario, ruta `/usuarios` en `src/App.tsx`, enlace en la página provisoria de agenda; tests de Vitest.
- **Base de datos**: sin migraciones; se usan `users` y `professionals` tal como las dejó C-02 (índice `uq_users_email_lower`, `professionals.user_id` único, claves `ON DELETE RESTRICT`).
- **KB**: al confirmar P-1..P-14 se registran DD nuevas (desde DD-56) en `09_decisiones_y_supuestos.md` y se actualiza CHANGES.md.
- **Changes siguientes**: C-07 y C-08 usan el repositorio de profesionales; C-13 revisa la política de contraseñas junto con el límite de intentos (DD-47).
