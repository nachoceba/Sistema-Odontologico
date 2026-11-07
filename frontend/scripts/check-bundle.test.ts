// @vitest-environment node
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { FORBIDDEN_TEXTS, scanBundle } from './check-bundle.mjs'

let dist = ''

function put(relative: string, content: string): void {
  const target = join(dist, relative)
  mkdirSync(join(target, '..'), { recursive: true })
  writeFileSync(target, content)
}

beforeEach(() => {
  dist = mkdtempSync(join(tmpdir(), 'bundle-'))
})

afterEach(() => {
  rmSync(dist, { recursive: true, force: true })
})

describe('scanBundle', () => {
  it('devuelve el archivo y el texto cuando el bundle nombra un secreto', () => {
    put('assets/index-abc.js', 'const x = "SMTP_PASSWORD"')

    expect(scanBundle(dist)).toEqual([{ file: 'assets/index-abc.js', text: 'SMTP_PASSWORD' }])
  })

  it('no informa nada en una carpeta limpia', () => {
    put('index.html', '<div id="root"></div>')
    put('assets/index-abc.js', 'console.log("hola")')

    expect(scanBundle(dist)).toEqual([])
  })

  it('detecta una cadena de conexión a postgresql', () => {
    put('assets/a.js', 'fetch("postgresql+psycopg://odonto:x@db:5432/odonto")')

    expect(scanBundle(dist)).toEqual([{ file: 'assets/a.js', text: 'postgresql' }])
  })

  it('revisa también los mapas de código (.map) en subcarpetas', () => {
    put('assets/deep/a.js.map', '{"sourcesContent":["const u = DATABASE_URL"]}')

    expect(scanBundle(dist)).toEqual([{ file: 'assets/deep/a.js.map', text: 'DATABASE_URL' }])
  })

  it('informa cada texto prohibido de cada archivo', () => {
    put('a.js', 'JWT_SECRET_KEY SEED_DEMO_PASSWORD')
    put('b.js', 'POSTGRES_PASSWORD')

    expect(scanBundle(dist)).toEqual([
      { file: 'a.js', text: 'JWT_SECRET_KEY' },
      { file: 'a.js', text: 'SEED_DEMO_PASSWORD' },
      { file: 'b.js', text: 'POSTGRES_PASSWORD' },
    ])
  })

  it('falla con un mensaje claro si la carpeta no existe', () => {
    expect(() => scanBundle(join(dist, 'no-existe'))).toThrow(/no existe/)
  })
})

describe('FORBIDDEN_TEXTS', () => {
  it('lista los nombres de secretos de la spec', () => {
    expect([...FORBIDDEN_TEXTS].sort()).toEqual(
      [
        'DATABASE_URL',
        'JWT_SECRET_KEY',
        'POSTGRES_PASSWORD',
        'SEED_DEMO_PASSWORD',
        'SMTP_PASSWORD',
        'postgresql',
      ].sort(),
    )
  })
})
