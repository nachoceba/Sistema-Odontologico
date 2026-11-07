import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { contrastRatio } from './contrast'
import {
  COLOR_PAIRS,
  REQUIRED_TOKENS,
  checkPairs,
  findDuplicateSelectors,
  findLooseColors,
  findMissingTokens,
  parseTokens,
} from './tokens'

// La hoja real como texto: `?raw` devuelve vacío con el procesamiento de CSS de Vitest.
const css = readFileSync(join(process.cwd(), 'src', 'styles.css'), 'utf8')

describe('helpers de tokens (sobre hojas de ejemplo)', () => {
  it('lee los tokens de :root', () => {
    const tokens = parseTokens(
      ':root { --color-bg: #f3faf8; --space-1: 0.25rem; }\n.a { color: red; }',
    )

    expect(tokens).toEqual({ '--color-bg': '#f3faf8', '--space-1': '0.25rem' })
  })

  it('un par que no llega a su mínimo falla y nombra los dos tokens', () => {
    const tokens = { '--color-secondary': '#2f7d4f', '--color-secondary-soft': '#e6f4ea' }

    const failures = checkPairs(tokens, [
      { fg: '--color-secondary', bg: '--color-secondary-soft', min: 4.5 },
    ])

    expect(failures).toHaveLength(1)
    expect(failures[0]).toContain('--color-secondary')
    expect(failures[0]).toContain('--color-secondary-soft')
    expect(failures[0]).toContain('4,44')
  })

  it('un par que cumple no da fallas y un token ausente se nombra', () => {
    const tokens = { '--color-text': '#12302b', '--color-bg': '#f3faf8' }

    expect(checkPairs(tokens, [{ fg: '--color-text', bg: '--color-bg', min: 4.5 }])).toEqual([])
    expect(
      checkPairs(tokens, [{ fg: '--color-text', bg: '--color-nada', min: 4.5 }])[0],
    ).toContain('--color-nada')
  })

  it('detecta colores sueltos fuera de :root y nombra el selector', () => {
    const sheet =
      ':root { --c: #fff; }\n.boton { color: #0b6e8a; }\n.caja { background: rgb(0 0 0 / 40%); }\n.ok { color: var(--c); }'

    expect(findLooseColors(sheet)).toEqual(['.boton', '.caja'])
  })

  it('no toma por color suelto los valores que no lo son', () => {
    expect(
      findLooseColors('.a { background: none; border-color: transparent; color: inherit; }'),
    ).toEqual([])
    expect(findLooseColors('.a { color: white; }')).toEqual(['.a'])
  })

  it('detecta un selector definido dos veces y no confunde el mismo selector en @media', () => {
    const sheet =
      '.hint { color: var(--a); }\n.otro { color: var(--a); }\n.hint { font-size: 1rem; }\n@media (max-width: 40rem) { .otro { width: 100%; } }'

    expect(findDuplicateSelectors(sheet)).toEqual(['.hint'])
  })

  it('informa los tokens que faltan', () => {
    expect(findMissingTokens({ '--color-bg': '#fff' }, ['--color-bg', '--color-text'])).toEqual([
      '--color-text',
    ])
  })
})

describe('styles.css', () => {
  it('se lee completa', () => {
    expect(css.length).toBeGreaterThan(1000)
  })

  const tokens = parseTokens(css)

  it('define todos los tokens de la paleta, la tipografía, los espacios, los radios y las sombras', () => {
    expect(findMissingTokens(tokens, REQUIRED_TOKENS)).toEqual([])
  })

  it('cada par de colores que se usa junto llega a su contraste mínimo', () => {
    expect(checkPairs(tokens, COLOR_PAIRS)).toEqual([])
  })

  it('la lista de pares exige 4,5:1 al texto y 3:1 al foco y al borde de campo', () => {
    const min = (fg: string, bg: string) =>
      COLOR_PAIRS.find((pair) => pair.fg === fg && pair.bg === bg)?.min
    expect(min('--color-text', '--color-bg')).toBe(4.5)
    expect(min('--color-focus', '--color-bg')).toBe(3)
    expect(min('--color-focus', '--color-surface')).toBe(3)
    expect(min('--color-border-input', '--color-surface')).toBe(3)
  })

  it('el texto principal y el botón principal tienen los valores de la spec', () => {
    expect(contrastRatio(tokens['--color-text'] ?? '', tokens['--color-bg'] ?? '')).toBeCloseTo(
      13.38,
      2,
    )
    expect(contrastRatio('#ffffff', tokens['--color-primary'] ?? '')).toBeCloseTo(5.73, 2)
  })

  it('no hay colores sueltos fuera de :root', () => {
    expect(findLooseColors(css)).toEqual([])
  })

  it('ningún selector se define dos veces', () => {
    expect(findDuplicateSelectors(css)).toEqual([])
  })

  it('no carga fuentes ni hojas de estilo externas', () => {
    expect(css).not.toMatch(/@import|url\(\s*['"]?https?:/i)
  })
})
