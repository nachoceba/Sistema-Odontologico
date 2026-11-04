import { useRef, useState } from 'react'
import { replaceWorkingHours, type Conflict, type WorkingBlock } from '../api/professionals'
import { DAY_NAMES } from './format'
import { HOURS_SAVED_MESSAGE, HOURS_INCOMPLETE_MESSAGE, messageForError } from './messages'
import { ApiError } from '../api/users'

interface Row {
  key: number
  weekday: number
  start: string
  end: string
}

let lastRowKey = 0

function newKey(): number {
  lastRowKey += 1
  return lastRowKey
}

function toRows(source: WorkingBlock[]): Row[] {
  return source.map((b) => ({
    key: newKey(),
    weekday: b.weekday,
    start: b.start_time,
    end: b.end_time,
  }))
}

const DEFAULT_START = '09:00'
const DEFAULT_END = '13:00'

/** Primer número del mensaje de la API ("Los tramos 1 y 2…") = posición 1-based del tramo enviado. */
function firstBlockPosition(message: string): number | null {
  const match = /\d+/.exec(message)
  return match === null ? null : Number(match[0])
}

/** Semana de tramos; sin permiso de edición todo queda deshabilitado. */
export function WeekEditor({
  professionalId,
  blocks,
  editable,
  onConflicts,
}: {
  professionalId: string
  blocks: WorkingBlock[]
  editable: boolean
  onConflicts: (conflicts: Conflict[]) => void
}) {
  const [rows, setRows] = useState<Row[]>(() => toRows(blocks))
  const [saved, setSaved] = useState(false)
  const [generalError, setGeneralError] = useState<string | null>(null)
  const [dayError, setDayError] = useState<{ weekday: number; message: string } | null>(null)
  const inFlight = useRef(false)

  function edit(key: number, changes: Partial<Row>) {
    setSaved(false)
    setRows((current) => current.map((r) => (r.key === key ? { ...r, ...changes } : r)))
  }

  function addRow(weekday: number) {
    setSaved(false)
    setRows((current) => [
      ...current,
      { key: newKey(), weekday, start: DEFAULT_START, end: DEFAULT_END },
    ])
  }

  function removeRow(key: number) {
    setSaved(false)
    setRows((current) => current.filter((r) => r.key !== key))
  }

  async function handleSave() {
    if (inFlight.current) return
    setSaved(false)
    setGeneralError(null)
    setDayError(null)
    // Orden estable por día: la posición del tramo en el pedido es la que cita la API.
    const ordered = rows.map((r, index) => ({ r, index })).sort((a, b) =>
      a.r.weekday === b.r.weekday ? a.index - b.index : a.r.weekday - b.r.weekday,
    )
    if (ordered.some(({ r }) => r.start === '' || r.end === '')) {
      setGeneralError(HOURS_INCOMPLETE_MESSAGE)
      return
    }
    inFlight.current = true
    try {
      const result = await replaceWorkingHours(
        professionalId,
        ordered.map(({ r }) => ({ weekday: r.weekday, start_time: r.start, end_time: r.end })),
      )
      setRows(toRows(result.blocks))
      onConflicts(result.conflicts)
      setSaved(result.conflicts.length === 0)
    } catch (failure) {
      const message = messageForError(failure)
      const position =
        failure instanceof ApiError && failure.code === 'INVALID_WORKING_HOURS'
          ? firstBlockPosition(message)
          : null
      const target = position === null ? undefined : ordered[position - 1]
      if (target === undefined) setGeneralError(message)
      else setDayError({ weekday: target.r.weekday, message })
    } finally {
      inFlight.current = false
    }
  }

  return (
    <section aria-labelledby="week-heading">
      <h3 id="week-heading">Horario semanal</h3>
      {DAY_NAMES.map((dayName, weekday) => {
        const dayRows = rows.filter((r) => r.weekday === weekday)
        return (
          <fieldset key={dayName} className="week-day" disabled={!editable}>
            <legend>{dayName}</legend>
            {dayRows.length === 0 ? <p className="hint">Sin atención</p> : null}
            {dayRows.map((row, index) => {
              const position = String(index + 1)
              return (
                <div key={row.key} className="block-row">
                  <input
                    type="time"
                    aria-label={`${dayName}, tramo ${position}, inicio`}
                    value={row.start}
                    onChange={(event) => {
                      edit(row.key, { start: event.target.value })
                    }}
                  />
                  <input
                    type="time"
                    aria-label={`${dayName}, tramo ${position}, fin`}
                    value={row.end}
                    onChange={(event) => {
                      edit(row.key, { end: event.target.value })
                    }}
                  />
                  {editable ? (
                    <button
                      type="button"
                      className="secondary"
                      aria-label={`Quitar tramo ${position} del ${dayName.toLowerCase()}`}
                      onClick={() => {
                        removeRow(row.key)
                      }}
                    >
                      Quitar
                    </button>
                  ) : null}
                </div>
              )
            })}
            {editable ? (
              <button
                type="button"
                className="secondary"
                aria-label={`Agregar tramo el ${dayName.toLowerCase()}`}
                onClick={() => {
                  addRow(weekday)
                }}
              >
                Agregar tramo
              </button>
            ) : null}
            {dayError?.weekday === weekday ? <p role="alert">{dayError.message}</p> : null}
          </fieldset>
        )
      })}
      {generalError === null ? null : <p role="alert">{generalError}</p>}
      {saved ? <p role="status">{HOURS_SAVED_MESSAGE}</p> : null}
      {editable ? (
        <button
          type="button"
          onClick={() => {
            void handleSave()
          }}
        >
          Guardar horario
        </button>
      ) : null}
    </section>
  )
}
