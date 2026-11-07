export interface BundleFinding {
  file: string
  text: string
}

export const FORBIDDEN_TEXTS: string[]

export function scanBundle(folder: string): BundleFinding[]
