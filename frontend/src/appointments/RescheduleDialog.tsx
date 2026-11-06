import { useEffect, useRef, useState } from 'react'
import {
  getDaySlots,
  rescheduleAppointment,
  type Appointment,
  type Slot,
} from '../api/appointments'
import type { Role } from '../auth/AuthContext'
import { formatLocalTime, localDateOf } from '../agenda/dates'
import { slotActions } from './actions'
import {
  BACK_LABEL,
  NO_FREE_SLOTS_MESSAGE,
  RESCHEDULE_SUBMIT_LABEL,
  dayAndTime,
  messageForAppointmentError,
  moveSummary,
} from './messages'
import { Modal } from './Modal'
import { useAppointmentAction } from './useAppointmentAction'

type Offered =
  | { date: string; status: 'ready'; slots: Slot[] }
  | { date: string; status: 'error'; message: string }

/** Reprogramar al mismo profesional: fecha y franjas libres no iniciadas de ese día (P-3, DD-64). */
export function RescheduleDialog({
  appointment,
  role,
  onDone,
  onRejected,
  onClose,
}: {
  appointment: Appointment
  role: Role
  /** Recibe el inicio del nuevo horario. */
  onDone: (startsAt: string) => void
  onRejected: () => void
  onClose: () => void
}) {
  const [date, setDate] = useState(() => localDateOf(appointment.starts_at))
  const [offered, setOffered] = useState<Offered | null>(null)
  const [chosen, setChosen] = useState<string | null>(null)
  const backRef = useRef<HTMLButtonElement>(null)
  const action = useAppointmentAction<string>({ onDone, onRejected })
  const name = `${appointment.patient_last_name}, ${appointment.patient_first_name}`

  useEffect(() => {
    let active = true
    getDaySlots(appointment.professional_id, date).then(
      (slots) => {
        if (active) setOffered({ date, status: 'ready', slots })
      },
      (error: unknown) => {
        if (active) setOffered({ date, status: 'error', message: messageForAppointmentError(error) })
      },
    )
    return () => {
      active = false
    }
  }, [appointment.professional_id, date])

  // Lo pedido para otra fecha se ignora mientras llega la respuesta de la actual.
  const current = offered?.date === date ? offered : null
  const now = new Date()
  const free =
    current?.status === 'ready'
      ? current.slots.filter(
          (slot) =>
            slot.status === 'FREE' &&
            slotActions({
              role,
              professionalActive: true,
              now,
              slot: { startsAt: slot.starts_at },
            }).book,
        )
      : []

  function submit() {
    if (chosen === null) return
    void action.run(async () => {
      await rescheduleAppointment(appointment.id, chosen)
      return chosen
    })
  }

  return (
    <Modal
      title={`Reprogramar el turno de ${name} del ${dayAndTime(appointment.starts_at)}`}
      onClose={onClose}
      safeRef={backRef}
    >
      <label>
        Fecha
        <input
          type="date"
          value={date}
          onChange={(event) => {
            if (event.target.value === '') return
            setDate(event.target.value)
            setChosen(null)
            action.clearError()
          }}
        />
      </label>
      {current === null ? <p role="status">Cargando…</p> : null}
      {current?.status === 'error' ? <p role="alert">{current.message}</p> : null}
      {current?.status === 'ready' && free.length === 0 ? <p>{NO_FREE_SLOTS_MESSAGE}</p> : null}
      {free.length > 0 ? (
        <ul className="slot-choices">
          {free.map((slot) => (
            <li key={slot.starts_at}>
              <button
                type="button"
                className="secondary"
                aria-pressed={chosen === slot.starts_at}
                onClick={() => {
                  setChosen(slot.starts_at)
                }}
              >
                {`${formatLocalTime(slot.starts_at)}–${formatLocalTime(slot.ends_at)}`}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {chosen === null ? null : <p>{moveSummary(appointment.starts_at, chosen)}</p>}
      {action.error === null ? null : <p role="alert">{action.error}</p>}
      <div className="form-actions">
        <button type="button" disabled={chosen === null || action.pending} onClick={submit}>
          {RESCHEDULE_SUBMIT_LABEL}
        </button>
        <button type="button" className="secondary" ref={backRef} onClick={onClose}>
          {BACK_LABEL}
        </button>
      </div>
    </Modal>
  )
}
