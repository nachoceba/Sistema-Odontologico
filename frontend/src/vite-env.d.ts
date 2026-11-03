/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL pública de la API (única variable VITE_ del proyecto; nunca un secreto). */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
