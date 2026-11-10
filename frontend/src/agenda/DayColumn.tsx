import { useId } from 'react'
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
  originLabel,
} from './messages'

function range(startsAt: string, endsAt: string): string {
  return `${formatLocalTime(startsAt)}–${formatLocalTime(endsAt)}`
}

/** Acciones opcionales de C-10; sin ellas la columna es de solo lectura como en C-09. */
export interface DayActions {
  onBookSlot?: (slot: { startsAt: string; endsAt: string }) => void
  canBook?: (slot: { startsAt: string }) => boolean
  onSelectAppointment?: (id: string) => void
}

function AppointmentLine({
  item,
  onSelect,
}: {
  item: AppointmentItem
  onSelect: ((id: string) => void) | undefined
}) {
  const origin = originLabel(item)
  const content = (
    <>
      <span className="appointment-text">{`${range(item.startsAt, item.endsAt)} ${item.patientName}`}</span>
      {item.treatmentName === null ? null : (
        <>
          {' '}
          <span className="appointment-treatment" title={item.treatmentName}>
            {`· ${item.treatmentName}`}
          </span>
        </>
      )}{' '}
      <span className="status-tag">{STATUS_LABELS[item.status]}</span>
      {origin === null ? null : (
        <>
          {' '}
          <span className={item.pendingUntil === null ? 'origin-tag' : 'origin-tag origin-tag--pending'}>
            {origin}
          </span>
        </>
      )}
      {item.conflict === null ? null : (
        <span className="conflict-tag">{CONFLICT_LABELS[item.conflict]}</span>
      )}
    </>
  )
  return (
    <li className={`appointment appointment--${item.status}`}>
      {onSelect === undefined ? (
        content
      ) : (
        <button
          type="button"
          className="appointment-button"
          onClick={() => {
            onSelect(item.id)
          }}
        >
          {content}
        </button>
      )}
    </li>
  )
}

function Row({ row, actions }: { row: GridRow; actions: DayActions }) {
  const timeId = useId()
  const { onBookSlot, canBook, onSelectAppointment } = actions
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
          <AppointmentLine item={row.appointment} onSelect={onSelectAppointment} />
        </ul>
      </li>
    )
  }
  return (
    <li className={`slot slot--${row.kind}`}>
      <span className="slot-time" id={timeId}>
        {range(row.startsAt, row.endsAt)}
      </span>{' '}
      <span className="slot-label">{row.kind === 'busy' ? BUSY_LABEL : FREE_LABEL}</span>
      {row.kind === 'free' && onBookSlot !== undefined && canBook?.({ startsAt: row.startsAt }) === true ? (
        <>
          {' '}
          <button
            type="button"
            className="book-button"
            aria-describedby={timeId}
            onClick={() => {
              onBookSlot({ startsAt: row.startsAt, endsAt: row.endsAt })
            }}
          >
            Agendar
          </button>
        </>
      ) : null}
      {row.appointments.length === 0 ? null : (
        <ul className="appointment-list">
          {row.appointments.map((item) => (
            <AppointmentLine key={item.id} item={item} onSelect={onSelectAppointment} />
          ))}
        </ul>
      )}
    </li>
  )
}

interface DayColumnProps extends DayActions {
  column: DayColumnModel
  /** Resalta el día de hoy. */
  highlight?: boolean
  /** En la semana, el título del día abre la vista "Día" (solo navegación). */
  onSelectDay?: (date: string) => void
}

/** Una columna de día; con las props de acciones permite agendar y elegir turnos (C-10). */
export function DayColumn({
  column,
  highlight = false,
  onSelectDay,
  ...actions
}: DayColumnProps) {
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
          <Row key={row.key} row={row} actions={actions} />
        ))}
      </ul>
    </section>
  )
}
