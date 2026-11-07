import { contrastRatio } from './contrast'

/** Utilidades para comprobar la hoja de estilos: tokens, contraste, colores sueltos y selectores repetidos. */

export interface ColorPair {
  fg: string
  bg: string
  min: number
}

export const REQUIRED_TOKENS: string[] = [
  '--color-bg',
  '--color-surface',
  '--color-text',
  '--color-text-muted',
  '--color-primary',
  '--color-primary-hover',
  '--color-primary-soft',
  '--color-secondary',
  '--color-secondary-soft',
  '--color-border',
  '--color-border-input',
  '--color-focus',
  '--color-success',
  '--color-success-bg',
  '--color-error',
  '--color-error-bg',
  '--color-warning',
  '--color-warning-bg',
  '--color-pending',
  '--color-pending-bg',
  '--color-outside',
  '--color-accent',
  '--color-backdrop',
  '--font-sans',
  '--font-size-1',
  '--font-size-2',
  '--font-size-3',
  '--font-size-4',
  '--font-size-5',
  '--font-size-6',
  '--space-1',
  '--space-2',
  '--space-3',
  '--space-4',
  '--space-5',
  '--space-6',
  '--radius-sm',
  '--radius-md',
  '--radius-lg',
  '--shadow-sm',
  '--shadow-md',
]

/** Pares que se usan juntos: texto/fondo (4,5), y foco, borde de campo y marcas de estado (3). */
export const COLOR_PAIRS: ColorPair[] = [
  { fg: '--color-text', bg: '--color-bg', min: 4.5 },
  { fg: '--color-text', bg: '--color-surface', min: 4.5 },
  { fg: '--color-text', bg: '--color-primary-soft', min: 4.5 },
  { fg: '--color-text', bg: '--color-outside', min: 4.5 },
  { fg: '--color-text-muted', bg: '--color-bg', min: 4.5 },
  { fg: '--color-text-muted', bg: '--color-surface', min: 4.5 },
  { fg: '--color-text-muted', bg: '--color-outside', min: 4.5 },
  { fg: '--color-primary', bg: '--color-bg', min: 4.5 },
  { fg: '--color-primary', bg: '--color-surface', min: 4.5 },
  { fg: '--color-primary', bg: '--color-primary-soft', min: 4.5 },
  { fg: '--color-surface', bg: '--color-text', min: 4.5 },
  { fg: '--color-surface', bg: '--color-primary', min: 4.5 },
  { fg: '--color-surface', bg: '--color-primary-hover', min: 4.5 },
  { fg: '--color-secondary', bg: '--color-surface', min: 4.5 },
  { fg: '--color-secondary', bg: '--color-secondary-soft', min: 4.5 },
  { fg: '--color-success', bg: '--color-success-bg', min: 4.5 },
  { fg: '--color-success', bg: '--color-surface', min: 4.5 },
  { fg: '--color-error', bg: '--color-error-bg', min: 4.5 },
  { fg: '--color-error', bg: '--color-surface', min: 4.5 },
  { fg: '--color-surface', bg: '--color-error', min: 4.5 },
  { fg: '--color-warning', bg: '--color-warning-bg', min: 4.5 },
  { fg: '--color-warning', bg: '--color-surface', min: 4.5 },
  { fg: '--color-pending', bg: '--color-pending-bg', min: 4.5 },
  { fg: '--color-pending', bg: '--color-surface', min: 4.5 },
  { fg: '--color-focus', bg: '--color-bg', min: 3 },
  { fg: '--color-focus', bg: '--color-surface', min: 3 },
  { fg: '--color-border-input', bg: '--color-surface', min: 3 },
  { fg: '--color-border-input', bg: '--color-bg', min: 3 },
  { fg: '--color-success', bg: '--color-success-bg', min: 3 },
  { fg: '--color-error', bg: '--color-error-bg', min: 3 },
  { fg: '--color-warning', bg: '--color-warning-bg', min: 3 },
  { fg: '--color-pending', bg: '--color-pending-bg', min: 3 },
  { fg: '--color-secondary', bg: '--color-secondary-soft', min: 3 },
]

function stripComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, '')
}

interface Rule {
  context: string
  selector: string
  body: string
}

/** Reglas de la hoja con su contexto (cadena vacía fuera de @media, o el texto del @media). */
function parseRules(css: string): Rule[] {
  const rules: Rule[] = []

  function walk(text: string, context: string): void {
    let index = 0
    while (index < text.length) {
      const open = text.indexOf('{', index)
      if (open === -1) return
      const header = text.slice(index, open).trim()
      let depth = 1
      let cursor = open + 1
      while (cursor < text.length && depth > 0) {
        if (text[cursor] === '{') depth += 1
        else if (text[cursor] === '}') depth -= 1
        cursor += 1
      }
      const body = text.slice(open + 1, cursor - 1)
      if (header.startsWith('@media') || header.startsWith('@supports')) {
        walk(body, header)
      } else if (!header.startsWith('@')) {
        rules.push({ context, selector: header.replace(/\s+/g, ' '), body })
      }
      index = cursor
    }
  }

  walk(stripComments(css), '')
  return rules
}

export function parseTokens(css: string): Record<string, string> {
  const tokens: Record<string, string> = {}
  for (const rule of parseRules(css)) {
    if (rule.selector !== ':root') continue
    for (const match of rule.body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
      tokens[match[1] ?? ''] = (match[2] ?? '').trim()
    }
  }
  return tokens
}

export function findMissingTokens(tokens: Record<string, string>, required: string[]): string[] {
  return required.filter((name) => !(name in tokens))
}

export function checkPairs(tokens: Record<string, string>, pairs: ColorPair[]): string[] {
  const failures: string[] = []
  for (const { fg, bg, min } of pairs) {
    const front = tokens[fg]
    const back = tokens[bg]
    if (front === undefined || back === undefined) {
      failures.push(`Falta el token ${front === undefined ? fg : bg} del par ${fg} sobre ${bg}`)
      continue
    }
    const ratio = contrastRatio(front, back)
    if (ratio < min) {
      const shown = ratio.toFixed(2).replace('.', ',')
      failures.push(`${fg} (${front}) sobre ${bg} (${back}) da ${shown}:1, menos que ${String(min)}:1`)
    }
  }
  return failures
}

const COLOR_VALUE =
  /#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(|\b(?:white|black|red|green|blue|gray|grey|orange|yellow|purple|pink|brown|navy|teal|silver|maroon|lime|aqua|cyan|magenta)\b/i

export function findLooseColors(css: string): string[] {
  return parseRules(css)
    .filter((rule) => rule.selector !== ':root' && COLOR_VALUE.test(rule.body))
    .map((rule) => rule.selector)
}

export function findDuplicateSelectors(css: string): string[] {
  const seen = new Set<string>()
  const duplicates: string[] = []
  for (const rule of parseRules(css)) {
    const key = `${rule.context}|${rule.selector}`
    if (seen.has(key) && !duplicates.includes(rule.selector)) duplicates.push(rule.selector)
    seen.add(key)
  }
  return duplicates
}
