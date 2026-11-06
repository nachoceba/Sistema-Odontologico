import { useEffect, useId, useRef, type ReactNode } from 'react'

/**
 * Diálogo modal accesible de la agenda: `role="dialog"`, `aria-modal`, foco inicial en la
 * opción segura (`safeRef`) y Escape cierra, igual que `ConfirmDialog`.
 */
export function Modal({
  title,
  onClose,
  safeRef,
  children,
}: {
  title: string
  onClose: () => void
  /** Botón que recibe el foco al abrir; si falta, el foco va al título. */
  safeRef?: React.RefObject<HTMLButtonElement | null>
  children: ReactNode
}) {
  const titleId = useId()
  const titleRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (safeRef?.current) safeRef.current.focus()
    else titleRef.current?.focus()
  }, [safeRef])

  return (
    <div className="dialog-backdrop">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="dialog"
        onKeyDown={(event) => {
          if (event.key === 'Escape') onClose()
        }}
      >
        <h2 id={titleId} tabIndex={-1} ref={titleRef}>
          {title}
        </h2>
        {children}
      </div>
    </div>
  )
}
