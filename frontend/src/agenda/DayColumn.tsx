import { formatDayLabel, formatLocalTime } from './dates'
import type { AppointmentItem, DayColumn as DayColumnModel, GridRow } from './grid'
import {
  BUSY_LABEL,
  CONFLICT_LABELS,
  FREE_LABEL,
  NO_HOURS_MESSAGE,
  OUTSIDE_LABEL,
  STATUS_LABELS,
  leaveLabel,
} from './messages'

function range(startsAt: string, endsAt: string): string {
  return `${formatLocalTime(startsAt)}–${formatLocalTime(endsAt)}`
}

function AppointmentLine({ item }: { item: AppointmentItem }) {
  return (
    <li className={`appointment appointment--${item.status}`}>
      <span className="appointment-text">{`${range(item.startsAt, item.endsAt)} ${item.patientName}`}</span>{' '}
      <span className="status-tag">{STATUS_LABELS[item.status]}</span>
      {item.conflict === null ? null : (
        <span className="conflict-tag">{CONFLICT_LABELS[item.conflict]}</span>
      )}
    </li>
  )
}

function Row({ row }: { row: GridRow }) {
  if (row.kind === 'outside') {
    return (
      <li className="slot slot--outside">
        {`${OUTSIDE_LABEL} ${range(row.startsAt, row.endsAt)}`}
      </li>
    )
  }
  if (row.kind === 'appointment') {
    return (
      <li className="slot slot--appointment">
        <ul className="appointment-list">
          <AppointmentLine item={row.appointment} />
        </ul>
      </li>
    )
  }
  return (
    <li className={`slot slot--${row.kind}`}>
      <span className="slot-time">{range(row.startsAt, row.endsAt)}</span>{' '}
      <span className="slot-label">{row.kind === 'busy' ? BUSY_LABEL : FREE_LABEL}</span>
      {row.appointments.length === 0 ? null : (
        <ul className="appointment-list">
          {row.appointments.map((item) => (
            <AppointmentLine key={item.id} item={item} />
          ))}
        </ul>
      )}
    </li>
  )
}

interface DayColumnProps {
  column: DayColumnModel
  /** Resalta el día de hoy. */
  highlight?: boolean
  /** En la semana, el título del día abre la vista "Día" (solo navegación). */
  onSelectDay?: (date: string) => void
}

/** Una columna de día de solo lectura; C-10 le suma las acciones sobre franjas y turnos. */
export function DayColumn({ column, highlight = false, onSelectDay }: DayColumnProps) {
  const label = formatDayLabel(column.date)
  const { header } = column
  return (
    <section
      className={highlight ? 'day-column day-column--today' : 'day-column'}
      aria-label={label}
    >
      <h3 className="day-title">
        {onSelectDay === undefined ? (
          label
        ) : (
          <button
            type="button"
            className="link-button"
            onClick={() => {
              onSelectDay(column.date)
            }}
          >
            {label}
          </button>
        )}
      </h3>
      {header.kind === 'time_off' ? <p className="day-banner day-banner--leave">{leaveLabel(header.reason)}</p> : null}
      {header.kind === 'no_hours' ? <p className="day-banner">{NO_HOURS_MESSAGE}</p> : null}
      <ul className="slot-list">
        {column.rows.map((row) => (
          <Row key={row.key} row={row} />
        ))}
      </ul>
    </section>
  )
}
