import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode, type RefObject } from 'react'

const FOCUSABLE =
  'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'

/**
 * Base común de los diálogos modales: `role="dialog"`, `aria-modal`, foco inicial en la opción
 * segura (o en el título), Escape cierra, Tab y Shift+Tab no sacan el foco del diálogo y, al
 * cerrarse, el foco vuelve al elemento que lo abrió (P-11).
 */
export function Dialog({
  title,
  onClose,
  safeRef,
  titleFocusable = false,
  children,
}: {
  title: string
  onClose: () => void
  /** Botón que recibe el foco al abrir; si falta, el foco va al título. */
  safeRef?: RefObject<HTMLButtonElement | null>
  /** El título admite foco programático (`tabIndex={-1}`). */
  titleFocusable?: boolean
  children: ReactNode
}) {
  const titleId = useId()
  const titleRef = useRef<HTMLHeadingElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const opener = document.activeElement
    if (safeRef?.current) safeRef.current.focus()
    else titleRef.current?.focus()
    return () => {
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus()
    }
  }, [safeRef])

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      onClose()
      return
    }
    if (event.key !== 'Tab') return
    const items = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [])
    const first = items[0]
    const last = items[items.length - 1]
    if (first === undefined || last === undefined) return
    const active = document.activeElement
    const inside = active instanceof HTMLElement && items.includes(active)
    if (event.shiftKey && (active === first || !inside)) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && (active === last || !inside)) {
      event.preventDefault()
      first.focus()
    }
  }

  return (
    <div className="dialog-backdrop">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="dialog"
        onKeyDown={onKeyDown}
      >
        <h2 id={titleId} tabIndex={titleFocusable ? -1 : undefined} ref={titleRef}>
          {title}
        </h2>
        {children}
      </div>
    </div>
  )
}
