# Spec Delta: runtime-configuration

## Purpose

Cargar y validar la configuración del sistema desde variables de entorno, definir el contrato del archivo de ejemplo versionado y mantener los secretos fuera del repositorio y del frontend (regla dura 5).

## ADDED Requirements

### Requirement: Configuración validada al arrancar

Los procesos del backend (API, worker y beat) SHALL leer su configuración desde variables de entorno y MUST negarse a arrancar si una variable obligatoria falta o tiene un valor inválido. El mensaje de error MUST nombrar la variable afectada y MUST NOT mostrar el valor de una variable sensible.

Variables obligatorias: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, `CLINIC_TIMEZONE`, `CORS_ORIGINS`. Opcionales con valor por defecto: `JWT_ALGORITHM` (`HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES` (`30`), `SMTP_USER` y `SMTP_PASSWORD` (vacías), `SMTP_USE_TLS` (`false`).

Reglas de validez: `JWT_SECRET_KEY` de al menos 32 caracteres; `JWT_ALGORITHM` solo `HS256` (DD-11); `ACCESS_TOKEN_EXPIRE_MINUTES` entero mayor que cero; `SMTP_PORT` entero entre 1 y 65535; `CLINIC_TIMEZONE` una zona IANA existente; `CORS_ORIGINS` una lista no vacía de orígenes separados por coma.

#### Scenario: Configuración completa (esperado)
- **WHEN** el proceso arranca con todas las variables de `.env.example` completadas con valores válidos y una `JWT_SECRET_KEY` de 48 caracteres
- **THEN** la configuración se carga y expone `CLINIC_TIMEZONE = America/Argentina/Buenos_Aires`, `ACCESS_TOKEN_EXPIRE_MINUTES = 30` y `CORS_ORIGINS = ["http://localhost:5173"]`

#### Scenario: Falta una variable obligatoria (error)
- **WHEN** el proceso arranca sin `DATABASE_URL`
- **THEN** no arranca y el error menciona `DATABASE_URL`

#### Scenario: Clave JWT demasiado corta sin revelar su valor (error)
- **WHEN** el proceso arranca con `JWT_SECRET_KEY` de 10 caracteres
- **THEN** no arranca, el error menciona `JWT_SECRET_KEY` y el texto del error no contiene el valor de la clave

#### Scenario: Zona horaria inexistente (error)
- **WHEN** el proceso arranca con `CLINIC_TIMEZONE = America/Inexistente`
- **THEN** no arranca y el error menciona `CLINIC_TIMEZONE`

#### Scenario: Algoritmo JWT no permitido (error)
- **WHEN** el proceso arranca con `JWT_ALGORITHM = none`
- **THEN** no arranca y el error menciona `JWT_ALGORITHM`

#### Scenario: Varios orígenes CORS (borde)
- **WHEN** `CORS_ORIGINS = "http://localhost:5173, http://127.0.0.1:5173"`
- **THEN** la configuración expone exactamente esos dos orígenes, sin espacios

#### Scenario: Credenciales SMTP vacías en desarrollo (borde)
- **WHEN** `SMTP_USER` y `SMTP_PASSWORD` están vacías o ausentes
- **THEN** la configuración se carga y ambas quedan vacías

### Requirement: El dominio no depende de la configuración

Importar y probar el código de dominio y de los repositorios en memoria MUST NOT requerir variables de entorno: la configuración SHALL cargarse recién cuando un proceso o un test la pide.

#### Scenario: Tests de dominio sin entorno
- **WHEN** se corre la batería de tests unitarios y de contrato existente sin ninguna variable de entorno del sistema definida
- **THEN** todos los tests pasan

### Requirement: Archivo de ejemplo completo y sin secretos

El repositorio SHALL versionar un `.env.example` en la raíz que declare cada variable que lee la configuración del backend, las de PostgreSQL (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) y `VITE_API_URL`. Las variables sensibles (`JWT_SECRET_KEY`, `SMTP_PASSWORD`) MUST quedar vacías; las credenciales de base del ejemplo MUST ser ficticias de desarrollo. El archivo `.env` MUST estar ignorado por git.

#### Scenario: Toda variable de la configuración figura en el ejemplo
- **WHEN** se comparan las variables que lee la configuración del backend con las declaradas en `.env.example`
- **THEN** no falta ninguna

#### Scenario: Secretos vacíos en el ejemplo
- **WHEN** se lee `.env.example`
- **THEN** `JWT_SECRET_KEY` y `SMTP_PASSWORD` no tienen valor

#### Scenario: `.env` ignorado por git
- **WHEN** existe un archivo `.env` en la raíz del repositorio
- **THEN** git lo ignora y no aparece como archivo a commitear

### Requirement: Ningún secreto llega al frontend

Ninguna variable con prefijo `VITE_` MUST contener un secreto: el nombre de una variable `VITE_` MUST NOT incluir `SECRET`, `PASSWORD`, `TOKEN`, `KEY` ni `DATABASE`. El servicio del frontend MUST recibir solo `VITE_API_URL` como variable propia del proyecto.

#### Scenario: Solo variables públicas con prefijo VITE_
- **WHEN** se revisan las variables `VITE_` de `.env.example`
- **THEN** la única es `VITE_API_URL`

#### Scenario: Variable secreta con prefijo VITE_ (error)
- **WHEN** alguien agrega `VITE_JWT_SECRET_KEY` a `.env.example`
- **THEN** el chequeo automático de configuración falla nombrando esa variable

#### Scenario: El contenedor del frontend no recibe secretos
- **WHEN** se inspecciona la configuración resuelta del servicio `frontend` en el entorno de contenedores
- **THEN** su entorno no contiene `JWT_SECRET_KEY`, `SMTP_PASSWORD`, `DATABASE_URL` ni `POSTGRES_PASSWORD`
