/**
 * Búsqueda de lecturas del entorno de Vite en el código fuente (spec runtime-configuration).
 * Solo se permite leer la URL pública de la API; cualquier otra variable podría ser un secreto
 * que termine dentro del bundle. Función pura: la usa el test que recorre `src/`.
 */
export interface EnvRead {
  file: string
  variable: string
}

const WHOLE_ENV = '(todo el entorno)'
// El punto escapado evita que este archivo se encuentre a sí mismo.
const ENV_READ = /import\.meta\.env(?:\.([A-Za-z0-9_]+))?/g

/** Lecturas del entorno por archivo, en orden de aparición. */
export function findEnvReads(files: Record<string, string>): EnvRead[] {
  const reads: EnvRead[] = []
  for (const [file, source] of Object.entries(files)) {
    for (const match of source.matchAll(ENV_READ)) {
      reads.push({ file, variable: match[1] ?? WHOLE_ENV })
    }
  }
  return reads
}
