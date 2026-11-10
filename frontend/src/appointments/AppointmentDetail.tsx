import type { Appointment, AttendanceStatus } from '../api/appointments'
import type { ConflictReason } from '../api/professionals'
import { formatLocalTime } from '../agenda/dates'
import { CONFLICT_LABELS, ONLINE_LABEL, PENDING_LABEL, STATUS_LABELS } from '../agenda/messages'
import type { AppointmentActions } from './actions'
import {
  CANCEL_LABEL,
  COMPLETED_LABEL,
  NO_SHOW_LABEL,
  NO_TREATMENT_LABEL,
  RESCHEDULE_LABEL,
  dayAndTime,
} from './messages'
import { SidePanel } from './SidePanel'

/** Detalle de un turno con las acciones que le corresponden (P-5). Sin datos de contacto. */
export function AppointmentDetail({
  appointment,
  professionalName,
  conflict,
  actions,
  onCancel,
  onReschedule,
  onAttendance,
  onClose,
}: {
  appointment: Appointment
  professionalName: string
  conflict: ConflictReason | null
  actions: AppointmentActions
  onCancel: () => void
  onReschedule: () => void
  onAttendance: (status: AttendanceStatus) => void
  onClose: () => void
}) {
  const title = `${dayAndTime(appointment.starts_at)}–${formatLocalTime(appointment.ends_at)}`
  return (
    <SidePanel title={title} onClose={onClose}>
      <dl className="detail-list">
        <dt>Paciente</dt>
        <dd>{`${appointment.patient_last_name}, ${appointment.patient_first_name}`}</dd>
        <dt>Profesional</dt>
        <dd>{professionalName}</dd>
        <dt>Tratamiento</dt>
        <dd>{appointment.treatment_name ?? NO_TREATMENT_LABEL}</dd>
        <dt>Estado</dt>
        <dd>
          <span className="status-tag">{STATUS_LABELS[appointment.status]}</span>
          {appointment.status === 'scheduled' && appointment.pending_until !== null ? (
            <>
              {' '}
              <span className="origin-tag origin-tag--pending">{PENDING_LABEL}</span>
            </>
          ) : appointment.origin === 'online' ? (
            <>
              {' '}
              <span className="origin-tag">{ONLINE_LABEL}</span>
            </>
          ) : null}
        </dd>
      </dl>
      {appointment.status === 'scheduled' && appointment.pending_until !== null ? (
        <p>{`${PENDING_LABEL} hasta las ${formatLocalTime(appointment.pending_until)}`}</p>
      ) : null}
      {appointment.status === 'cancelled' && appointment.cancel_reason !== null ? (
        <p>{`Motivo: ${appointment.cancel_reason}`}</p>
      ) : null}
      {conflict === null ? null : <p className="conflict-tag">{CONFLICT_LABELS[conflict]}</p>}
      <div className="form-actions">
        {actions.reschedule ? (
          <button type="button" onClick={onReschedule}>
            {RESCHEDULE_LABEL}
          </button>
        ) : null}
        {actions.markAttendance ? (
          <>
            <button
              type="button"
              onClick={() => {
                onAttendance('completed')
              }}
            >
              {COMPLETED_LABEL}
            </button>
            <button
              type="button"
              onClick={() => {
                onAttendance('no_show')
              }}
            >
              {NO_SHOW_LABEL}
            </button>
          </>
        ) : null}
        {actions.cancel ? (
          <button type="button" className="danger" onClick={onCancel}>
            {CANCEL_LABEL}
          </button>
        ) : null}
      </div>
    </SidePanel>
  )
}
