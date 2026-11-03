/** URL base de la API, o null si VITE_API_URL falta o está vacía (nunca se inventa una). */
function apiBase(): string | null {
  const raw: unknown = import.meta.env.VITE_API_URL
  if (typeof raw !== 'string') return null
  const trimmed = raw.trim().replace(/\/+$/, '')
  return trimmed === '' ? null : trimmed
}

/** Arma la URL completa de un endpoint; null si la API no está configurada. */
export function apiUrl(path: string): string | null {
  const base = apiBase()
  if (base === null) return null
  return `${base}/${path.replace(/^\/+/, '')}`
}
