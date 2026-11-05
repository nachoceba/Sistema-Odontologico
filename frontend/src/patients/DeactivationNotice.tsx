import type { UpcomingAppointment } from '../api/patients'
import { formatLocalMoment } from '../professionals/format'

function noticeText(count: number): string {
  return count === 1
    ? 'Este paciente tiene 1 turno agendado. Para reprogramarlo, reactivalo primero; si no, cancelalo desde la agenda'
    : `Este paciente tiene ${String(count)} turnos agendados. Para reprogramarlos, reactivalo primero; si no, cancelalos desde la agenda`
}

/** Turnos futuros de un paciente recién desactivado, en hora del consultorio (DD-76). */
export function DeactivationNotice({ appointments }: { appointments: UpcomingAppointment[] }) {
  if (appointments.length === 0) return null
  return (
    <section role="status" aria-label="Turnos del paciente desactivado" className="notice">
      <p>{noticeText(appointments.length)}</p>
      <ul>
        {appointments.map((appointment) => (
          <li key={appointment.id}>{formatLocalMoment(appointment.starts_at)}</li>
        ))}
      </ul>
    </section>
  )
}
