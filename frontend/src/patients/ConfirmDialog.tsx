import { useRef } from 'react'
import { Dialog } from '../ui/Dialog'

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
  const cancelRef = useRef<HTMLButtonElement>(null)

  return (
    <Dialog title={title} onClose={onCancel} safeRef={cancelRef}>
      <p>{message}</p>
      <div className="form-actions">
        <button type="button" onClick={onConfirm}>
          {confirmLabel}
        </button>
        <button type="button" className="secondary" ref={cancelRef} onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </Dialog>
  )
}
