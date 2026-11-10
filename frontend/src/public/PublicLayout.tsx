import type { ReactNode } from 'react'
import { ToothMark } from '../ui/ToothMark'

/** Marco de las páginas públicas: sin barra de navegación interna ni datos de sesión. */
export function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <main className="page page--public">
      <p className="public-brand">
        <ToothMark />
        Sistema Odontológico
      </p>
      {children}
    </main>
  )
}
