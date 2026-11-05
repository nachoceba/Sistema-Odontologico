import { useEffect, useId, useRef } from 'react'

/** Diálogo de confirmación accesible: foco en "Cancelar" (lo seguro) y Escape cancela. */
export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: {
  title: string
  message: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
}) {
  const titleId = useId()
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    cancelRef.current?.focus()
  }, [])

  return (
    <div className="dialog-backdrop">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="dialog"
        onKeyDown={(event) => {
          if (event.key === 'Escape') onCancel()
        }}
      >
        <h2 id={titleId}>{title}</h2>
        <p>{message}</p>
        <div className="form-actions">
          <button type="button" onClick={onConfirm}>
            {confirmLabel}
          </button>
          <button type="button" className="secondary" ref={cancelRef} onClick={onCancel}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}
