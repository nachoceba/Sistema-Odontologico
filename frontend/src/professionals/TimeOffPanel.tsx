import { useRef, useState, type SyntheticEvent } from 'react'
import { addTimeOff, deleteTimeOff, type Conflict, type TimeOff } from '../api/professionals'
import { ApiError } from '../api/users'
import { formatDate } from './format'
import {
  CONFIRM_DELETE_MESSAGE,
  DATES_REQUIRED_MESSAGE,
  END_BEFORE_START_MESSAGE,
  messageForError,
} from './messages'

function byStart(a: TimeOff, b: TimeOff): number {
  return a.starts_on.localeCompare(b.starts_on)
}

/** Licencias del profesional; el administrador carga y borra (no se editan, DD-70). */
export function TimeOffPanel({
  professionalId,
  initial,
  editable,
  onConflicts,
}: {
  professionalId: string
  initial: TimeOff[]
  editable: boolean
  onConflicts: (conflicts: Conflict[]) => void
}) {
  const [entries, setEntries] = useState<TimeOff[]>(initial)
  const [startsOn, setStartsOn] = useState('')
  const [endsOn, setEndsOn] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const inFlight = useRef(false)

  async function handleAdd(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    setError(null)
    if (startsOn === '' || endsOn === '') {
      setError(DATES_REQUIRED_MESSAGE)
      return
    }
    if (endsOn < startsOn) {
      setError(END_BEFORE_START_MESSAGE)
      return
    }
    inFlight.current = true
    try {
      const trimmed = reason.trim()
      const saved = await addTimeOff(professionalId, {
        starts_on: startsOn,
        ends_on: endsOn,
        ...(trimmed === '' ? {} : { reason: trimmed }),
      })
      setEntries((current) => [...current, saved.time_off].sort(byStart))
      onConflicts(saved.conflicts)
      setStartsOn('')
      setEndsOn('')
      setReason('')
    } catch (failure) {
      setError(messageForError(failure))
    } finally {
      inFlight.current = false
    }
  }

  async function handleDelete(entry: TimeOff) {
    if (!window.confirm(CONFIRM_DELETE_MESSAGE)) return
    setError(null)
    try {
      await deleteTimeOff(professionalId, entry.id)
      setEntries((current) => current.filter((e) => e.id !== entry.id))
      onConflicts([])
    } catch (failure) {
      setError(messageForError(failure))
      if (failure instanceof ApiError && failure.code === 'TIME_OFF_NOT_FOUND') {
        setEntries((current) => current.filter((e) => e.id !== entry.id))
      }
    }
  }

  return (
    <section aria-labelledby="time-off-heading">
      <h3 id="time-off-heading">Licencias</h3>
      {entries.length === 0 ? <p className="hint">Sin licencias cargadas</p> : null}
      <ul className="time-off-list">
        {entries.map((entry) => (
          <li key={entry.id}>
            <span>
              {formatDate(entry.starts_on)} al {formatDate(entry.ends_on)}
            </span>{' '}
            <span>{entry.reason ?? 'Sin motivo'}</span>
            {editable ? (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  void handleDelete(entry)
                }}
              >
                Borrar
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      {editable ? (
        <form
          className="user-form"
          onSubmit={(event) => {
            void handleAdd(event)
          }}
        >
          <label htmlFor="time-off-start">Desde</label>
          <input
            id="time-off-start"
            type="date"
            value={startsOn}
            onChange={(event) => {
              setStartsOn(event.target.value)
            }}
          />
          <label htmlFor="time-off-end">Hasta</label>
          <input
            id="time-off-end"
            type="date"
            value={endsOn}
            onChange={(event) => {
              setEndsOn(event.target.value)
            }}
          />
          <label htmlFor="time-off-reason">Motivo (opcional)</label>
          <input
            id="time-off-reason"
            value={reason}
            maxLength={500}
            onChange={(event) => {
              setReason(event.target.value)
            }}
          />
          <div className="form-actions">
            <button type="submit">Agregar licencia</button>
          </div>
        </form>
      ) : null}
      {error === null ? null : <p role="alert">{error}</p>}
    </section>
  )
}
