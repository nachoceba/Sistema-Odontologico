const KEY = 'auth_token'

// Si sessionStorage no está disponible (modo privado, bloqueado), la sesión vive solo en memoria.
let memoryToken: string | null = null

/** Guarda el token en sessionStorage (P-2); nunca en localStorage ni en cookies. */
export function saveToken(token: string): void {
  memoryToken = token
  try {
    window.sessionStorage.setItem(KEY, token)
  } catch {
    // Se conserva solo en memoria.
  }
}

export function readToken(): string | null {
  try {
    const stored = window.sessionStorage.getItem(KEY)
    if (stored !== null) return stored
  } catch {
    // Cae a la copia en memoria.
  }
  return memoryToken
}

export function clearToken(): void {
  memoryToken = null
  try {
    window.sessionStorage.removeItem(KEY)
  } catch {
    // Nada que borrar si el almacenamiento no responde.
  }
}
