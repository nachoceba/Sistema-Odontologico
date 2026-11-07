import { describe, expect, it } from 'vitest'
import { contrastRatio } from './contrast'

describe('contrastRatio', () => {
  it('negro sobre blanco da 21:1', () => {
    expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 2)
  })

  it('un color sobre sí mismo da 1:1', () => {
    expect(contrastRatio('#ffffff', '#ffffff')).toBeCloseTo(1, 2)
  })

  it('blanco sobre el verde agua principal da 5,73:1', () => {
    expect(contrastRatio('#ffffff', '#0a7368')).toBeCloseTo(5.73, 2)
  })

  it('el foco anterior sobre el fondo anterior da 1,95:1 (no llega a 3:1)', () => {
    expect(contrastRatio('#f0a500', '#f5f8fa')).toBeCloseTo(1.95, 2)
  })

  it('acepta hexadecimales de 3 dígitos y en mayúsculas', () => {
    expect(contrastRatio('#FFF', '#000')).toBeCloseTo(21, 2)
    expect(contrastRatio('#0A7368', '#FFFFFF')).toBeCloseTo(5.73, 2)
  })

  it('es simétrica: no depende de cuál es el texto y cuál el fondo', () => {
    expect(contrastRatio('#12302b', '#f3faf8')).toBeCloseTo(contrastRatio('#f3faf8', '#12302b'), 10)
  })

  it('rechaza un color que no es hexadecimal', () => {
    expect(() => contrastRatio('rojo', '#ffffff')).toThrow(/rojo/)
  })
})
