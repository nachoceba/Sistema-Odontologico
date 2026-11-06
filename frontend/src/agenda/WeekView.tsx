import { DayColumn, type DayActions } from './DayColumn'
import type { DayColumn as DayColumnModel } from './grid'

interface WeekViewProps extends DayActions {
  columns: readonly DayColumnModel[]
  today: string
  onSelectDay: (date: string) => void
}

/** Los siete días de lunes a domingo, cada uno armado con sus propias franjas (DD-15). */
export function WeekView({ columns, today, onSelectDay, ...actions }: WeekViewProps) {
  return (
    <div className="week-grid">
      {columns.map((column) => (
        <DayColumn
          key={column.date}
          column={column}
          highlight={column.date === today}
          onSelectDay={onSelectDay}
          {...actions}
        />
      ))}
    </div>
  )
}
