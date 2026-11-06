import { useRef, useState } from 'react'
import { cancelAppointment, type Appointment } from '../api/appointments'
import {
  BACK_LABEL,
  CANCEL_SUBMIT_LABEL,
  REASON_MAX_LENGTH,
  REASON_REQUIRED_MESSAGE,
  dayAndTime,
} from './messages'
import { Modal } from './Modal'
import { useAppointmentAction } from './useAppointmentAction'

/** Cancelar un turno con motivo obligatorio (US-008, DD-65, P-2). */
export function CancelDialog({
  appointment,
  onDone,
  onRejected,
  onClose,
}: {
  appointment: Appointment
  onDone: () => void
  onRejected: () => void
  onClose: () => void
}) {
  const [reason, setReason] = useState('')
  const [missing, setMissing] = useState(false)
  const backRef = useRef<HTMLButtonElement>(null)
  const action = useAppointmentAction({ onDone, onRejected })
  const name = `${appointment.patient_last_name}, ${appointment.patient_first_name}`

  function submit() {
    const trimmed = reason.trim()
    if (trimmed === '') {
      setMissing(true)
      return
    }
    setMissing(false)
    void action.run(() => cancelAppointment(appointment.id, trimmed))
  }

  return (
    <Modal
      title={`Cancelar el turno de ${name} del ${dayAndTime(appointment.starts_at)}`}
      onClose={onClose}
      safeRef={backRef}
    >
      <label>
        Motivo
        <textarea
          value={reason}
          maxLength={REASON_MAX_LENGTH}
          rows={3}
          onChange={(event) => {
            setReason(event.target.value)
          }}
        />
      </label>
      {missing ? <p className="field-error">{REASON_REQUIRED_MESSAGE}</p> : null}
      {action.error === null ? null : <p role="alert">{action.error}</p>}
      <div className="form-actions">
        <button type="button" className="danger" disabled={action.pending} onClick={submit}>
          {CANCEL_SUBMIT_LABEL}
        </button>
        <button type="button" className="secondary" ref={backRef} onClick={onClose}>
          {BACK_LABEL}
        </button>
      </div>
    </Modal>
  )
}
