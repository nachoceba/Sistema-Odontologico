// Chequeo del bundle construido (spec runtime-configuration, DD-111): ningun secreto en dist/.
// Node puro, sin dependencias. Uso: `node scripts/check-bundle.mjs [carpeta]` (por defecto dist).
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Nombres y patrones que no pueden aparecer en ningun archivo del bundle. */
export const FORBIDDEN_TEXTS = [
  'JWT_SECRET_KEY',
  'SMTP_PASSWORD',
  'SEED_DEMO_PASSWORD',
  'POSTGRES_PASSWORD',
  'DATABASE_URL',
  'postgresql',
]

function listFiles(folder) {
  const found = []
  for (const entry of readdirSync(folder, { withFileTypes: true })) {
    const path = join(folder, entry.name)
    if (entry.isDirectory()) found.push(...listFiles(path))
    else found.push(path)
  }
  return found.sort()
}

/** Hallazgos `{ file, text }` (ruta relativa con `/`) de cada texto prohibido en cada archivo. */
export function scanBundle(folder) {
  if (!existsSync(folder)) throw new Error(`La carpeta del bundle no existe: ${folder}`)
  const findings = []
  for (const path of listFiles(folder)) {
    const content = readFileSync(path, 'latin1')
    const file = relative(folder, path).split(sep).join('/')
    for (const text of FORBIDDEN_TEXTS) {
      if (content.includes(text)) findings.push({ file, text })
    }
  }
  return findings
}

function main() {
  const folder = process.argv[2] ?? 'dist'
  const findings = scanBundle(folder)
  if (findings.length === 0) {
    console.log(`Bundle limpio: ${folder} no contiene secretos.`)
    return 0
  }
  for (const { file, text } of findings) {
    console.error(`Secreto en el bundle: ${file} contiene "${text}"`)
  }
  return 1
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    process.exit(main())
  } catch (error) {
    console.error(error instanceof Error ? error.message : error)
    process.exit(1)
  }
}
