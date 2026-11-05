import { DayColumn } from './DayColumn'
import type { DayColumn as DayColumnModel } from './grid'

interface WeekViewProps {
  columns: readonly DayColumnModel[]
  today: string
  onSelectDay: (date: string) => void
}

/** Los siete días de lunes a domingo, cada uno armado con sus propias franjas (DD-15). */
export function WeekView({ columns, today, onSelectDay }: WeekViewProps) {
  return (
    <div className="week-grid">
      {columns.map((column) => (
        <DayColumn
          key={column.date}
          column={column}
          highlight={column.date === today}
          onSelectDay={onSelectDay}
        />
      ))}
    </div>
  )
}
