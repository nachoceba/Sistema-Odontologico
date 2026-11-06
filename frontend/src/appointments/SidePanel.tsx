import { useEffect, useId, useRef, type ReactNode } from 'react'
import { CLOSE_LABEL } from './messages'

/**
 * Panel lateral de la agenda (a la derecha en pantallas anchas, a ancho completo en el teléfono).
 * El foco pasa al título al abrirse y Escape lo cierra, como `ConfirmDialog`.
 */
export function SidePanel({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  const titleId = useId()
  const titleRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    titleRef.current?.focus()
  }, [])

  return (
    <aside
      className="side-panel"
      aria-labelledby={titleId}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose()
      }}
    >
      <h2 id={titleId} className="side-panel-title" tabIndex={-1} ref={titleRef}>
        {title}
      </h2>
      {children}
      <div className="form-actions">
        <button type="button" className="secondary" onClick={onClose}>
          {CLOSE_LABEL}
        </button>
      </div>
    </aside>
  )
}
