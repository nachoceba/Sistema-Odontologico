import type { ReactNode, RefObject } from 'react'
import { Dialog } from '../ui/Dialog'

/** Diálogo modal de la agenda: usa la base común de diálogos y enfoca la opción segura o el título. */
export function Modal({
  title,
  onClose,
  safeRef,
  children,
}: {
  title: string
  onClose: () => void
  /** Botón que recibe el foco al abrir; si falta, el foco va al título. */
  safeRef?: RefObject<HTMLButtonElement | null>
  children: ReactNode
}) {
  return (
    <Dialog title={title} onClose={onClose} safeRef={safeRef} titleFocusable>
      {children}
    </Dialog>
  )
}
