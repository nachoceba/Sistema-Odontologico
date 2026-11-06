import { useEffect, useRef, useState } from 'react'
import { getAppointment, type Appointment } from '../api/appointments'
import type { Conflict } from '../api/professionals'
import { formatDayLabel, formatLocalTime, localDateOf } from '../agenda/dates'
import { CONFLICT_LABELS } from '../agenda/messages'
import { CANCEL_LABEL, RESCHEDULE_LABEL } from './messages'

type Loaded = Appointment | 'failed'

export const conflictsTitle = (count: number): string =>
  count === 1 ? '1 turno en conflicto' : `${String(count)} turnos en conflicto`

/**
 * Lista de turnos en conflicto del profesional (RN-HO-04, P-8). `GET /conflicts` trae solo
 * `patient_id`: el nombre se pide turno por turno con `GET /appointments/{id}` (DD-79).
 */
export function ConflictsPanel({
  conflicts,
  professionalActive,
  onReschedule,
  onCancel,
  onView,
}: {
  conflicts: readonly Conflict[]
  professionalActive: boolean
  onReschedule: (appointment: Appointment) => void
  onCancel: (appointment: Appointment) => void
  onView: (date: string) => void
}) {
  const [loaded, setLoaded] = useState<Record<string, Loaded>>({})
  const requested = useRef(new Set<string>())
  const idsKey = conflicts.map((c) => c.appointment_id).join(',')

  useEffect(() => {
    const ids = idsKey === '' ? [] : idsKey.split(',')
    for (const id of ids) {
      if (requested.current.has(id)) continue
      requested.current.add(id)
      getAppointment(id).then(
        (appointment) => {
          setLoaded((current) => ({ ...current, [id]: appointment }))
        },
        () => {
          requested.current.delete(id)
          setLoaded((current) => ({ ...current, [id]: 'failed' }))
        },
      )
    }
  }, [idsKey])

  const ordered = [...conflicts].sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at))
  return (
    <section className="conflicts-panel" aria-labelledby="conflicts-title">
      <h2 id="conflicts-title">{conflictsTitle(conflicts.length)}</h2>
      <ul className="conflict-list">
        {ordered.map((conflict) => {
          const patient = loaded[conflict.appointment_id]
          const date = localDateOf(conflict.starts_at)
          return (
            <li key={conflict.appointment_id}>
              <span className="conflict-when">
                {`${formatDayLabel(date)} ${formatLocalTime(conflict.starts_at)}–${formatLocalTime(conflict.ends_at)}`}
              </span>{' '}
              <span className="conflict-patient">
                {patient === undefined
                  ? 'Cargando…'
                  : patient === 'failed'
                    ? 'No se pudo cargar el paciente'
                    : `${patient.patient_last_name}, ${patient.patient_first_name}`}
              </span>{' '}
              <span className="conflict-tag">{CONFLICT_LABELS[conflict.reason]}</span>
              <span className="conflict-actions">
                {patient !== undefined && patient !== 'failed' && professionalActive ? (
                  <button
                    type="button"
                    onClick={() => {
                      onReschedule(patient)
                    }}
                  >
                    {RESCHEDULE_LABEL}
                  </button>
                ) : null}
                {patient !== undefined && patient !== 'failed' ? (
                  <button
                    type="button"
                    className="danger"
                    onClick={() => {
                      onCancel(patient)
                    }}
                  >
                    {CANCEL_LABEL}
                  </button>
                ) : null}
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    onView(date)
                  }}
                >
                  Ver en la agenda
                </button>
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
