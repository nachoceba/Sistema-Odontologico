import type { Conflict } from '../api/professionals'
import { formatLocalMoment } from './format'
import { CONFLICTS_MESSAGE } from './messages'

/** Aviso a recepción con los turnos que quedaron fuera del horario o en licencia (RN-HO-04). */
export function ConflictNotice({ conflicts }: { conflicts: Conflict[] }) {
  if (conflicts.length === 0) return null
  return (
    <section aria-label="Turnos en conflicto" className="conflict-notice">
      <p role="status">{CONFLICTS_MESSAGE}</p>
      <ul>
        {conflicts.map((conflict) => (
          <li key={conflict.appointment_id}>
            {formatLocalMoment(conflict.starts_at)}{' '}
            <span className="hint">
              {conflict.reason === 'TIME_OFF' ? '(en licencia)' : '(fuera de horario)'}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
