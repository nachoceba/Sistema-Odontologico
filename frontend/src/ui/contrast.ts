/** Contraste entre dos colores hexadecimales según la fórmula de WCAG 2.2 (1,0 a 21,0). */

function parseHex(color: string): [number, number, number] {
  const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(color.trim())
  if (match === null) throw new Error(`Color no válido: ${color}`)
  const digits = match[1] ?? ''
  const full =
    digits.length === 3
      ? digits
          .split('')
          .map((digit) => digit + digit)
          .join('')
      : digits
  return [0, 2, 4].map((start) => parseInt(full.slice(start, start + 2), 16) / 255) as [
    number,
    number,
    number,
  ]
}

function linear(channel: number): number {
  return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
}

function luminance(color: string): number {
  const [red, green, blue] = parseHex(color)
  return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)
}

export function contrastRatio(first: string, second: string): number {
  const a = luminance(first)
  const b = luminance(second)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}
