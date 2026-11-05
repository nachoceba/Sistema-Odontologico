import { parseIsoDate } from './dates'

export type AgendaView = 'dia' | 'semana'

interface DateNavigatorProps {
  date: string
  view: AgendaView
  onPrevious: () => void
  onNext: () => void
  onToday: () => void
  onDate: (date: string) => void
  onView: (view: AgendaView) => void
  onRefresh: () => void
}

/** Anterior, Siguiente y Hoy, campo de fecha, elección de vista y "Actualizar". */
export function DateNavigator({
  date,
  view,
  onPrevious,
  onNext,
  onToday,
  onDate,
  onView,
  onRefresh,
}: DateNavigatorProps) {
  return (
    <div className="agenda-toolbar">
      <button type="button" onClick={onPrevious}>
        Anterior
      </button>
      <button type="button" onClick={onToday}>
        Hoy
      </button>
      <button type="button" onClick={onNext}>
        Siguiente
      </button>
      <label>
        Fecha{' '}
        <input
          type="date"
          value={date}
          onChange={(event) => {
            const parsed = parseIsoDate(event.target.value)
            if (parsed !== null) onDate(parsed)
          }}
        />
      </label>
      <button
        type="button"
        aria-pressed={view === 'dia'}
        onClick={() => {
          onView('dia')
        }}
      >
        Día
      </button>
      <button
        type="button"
        aria-pressed={view === 'semana'}
        onClick={() => {
          onView('semana')
        }}
      >
        Semana
      </button>
      <button type="button" onClick={onRefresh}>
        Actualizar
      </button>
    </div>
  )
}
