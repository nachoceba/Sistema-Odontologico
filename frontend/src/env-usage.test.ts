import { describe, expect, it } from 'vitest'
import { findEnvReads } from './env-usage'

// Todos los archivos de src (menos tests), como texto. Es la fuente real que se compila.
const sources = import.meta.glob<string>(['./**/*.{ts,tsx}', '!./**/*.test.{ts,tsx}'], {
  query: '?raw',
  import: 'default',
  eager: true,
})

describe('findEnvReads', () => {
  it('nombra el archivo y la variable que no es VITE_API_URL', () => {
    const files = {
      './otra.ts': 'export const x = import.meta.env.VITE_OTRA',
      './config.ts': 'const raw = import.meta.env.VITE_API_URL',
    }

    expect(findEnvReads(files)).toEqual([
      { file: './otra.ts', variable: 'VITE_OTRA' },
      { file: './config.ts', variable: 'VITE_API_URL' },
    ])
  })

  it('detecta varias lecturas en un archivo y la lectura sin nombre', () => {
    const files = {
      './a.ts': 'const m = import.meta.env.MODE; const all = import.meta.env\nconst d = import.meta.env.DEV',
    }

    expect(findEnvReads(files)).toEqual([
      { file: './a.ts', variable: 'MODE' },
      { file: './a.ts', variable: '(todo el entorno)' },
      { file: './a.ts', variable: 'DEV' },
    ])
  })

  it('no informa archivos que no leen el entorno', () => {
    expect(findEnvReads({ './b.ts': 'export const y = 1' })).toEqual([])
  })
})

describe('código del frontend', () => {
  it('lee solo VITE_API_URL de import.meta.env', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(10)

    const offenders = findEnvReads(sources).filter((read) => read.variable !== 'VITE_API_URL')

    expect(offenders).toEqual([])
  })

  it('al menos config.ts lee VITE_API_URL (la búsqueda ve el código real)', () => {
    expect(findEnvReads(sources)).toContainEqual({
      file: './config.ts',
      variable: 'VITE_API_URL',
    })
  })
})
