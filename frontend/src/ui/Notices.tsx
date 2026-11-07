import type { ReactNode } from 'react'
import { ToothMark } from './ToothMark'

/** Aviso de carga común: conserva `role="status"` y el texto, con el diente pulsando. */
export function LoadingNotice({ children = 'Cargando…' }: { children?: ReactNode }) {
  return (
    <p role="status">
      <ToothMark pulse />
      {children}
    </p>
  )
}

/** Aviso de listado vacío común: conserva `role="status"` y el texto, con el diente quieto. */
export function EmptyNotice({ children }: { children: ReactNode }) {
  return (
    <p role="status">
      <ToothMark />
      {children}
    </p>
  )
}
