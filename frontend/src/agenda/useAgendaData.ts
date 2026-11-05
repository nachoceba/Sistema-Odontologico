import { useEffect, useState } from 'react'
import { getDaySlots, listAppointments } from '../api/appointments'
import { listConflicts, listTimeOff } from '../api/professionals'
import { NETWORK_MESSAGE, messageForError } from '../users/messages'
import { buildDayColumn, type DayColumn } from './grid'

export type AgendaData =
  | { status: 'loading' }
  | { status: 'error'; message: string; retryable: boolean }
  | { status: 'ready'; columns: DayColumn[] }

async function load(professionalId: string, dates: readonly string[]): Promise<AgendaData> {
  try {
    const [slotsByDay, timeOff, conflicts] = await Promise.all([
      Promise.all(dates.map((date) => getDaySlots(professionalId, date))),
      listTimeOff(professionalId),
      listConflicts(professionalId),
    ])
    // El rango de turnos sale de los límites de las franjas, que calcula el servidor (D-4).
    const first = slotsByDay.find((slots) => slots.length > 0)?.[0]
    const last = [...slotsByDay].reverse().find((slots) => slots.length > 0)?.at(-1)
    const appointments =
      first === undefined || last === undefined
        ? []
        : await listAppointments(professionalId, first.starts_at, last.ends_at)
    return {
      status: 'ready',
      columns: dates.map((date, index) =>
        buildDayColumn({
          date,
          slots: slotsByDay[index] ?? [],
          appointments,
          timeOff,
          conflicts,
        }),
      ),
    }
  } catch (error) {
    const message = messageForError(error)
    return { status: 'error', message, retryable: message === NETWORK_MESSAGE }
  }
}

/**
 * Pide franjas, licencias, conflictos y turnos (solo GET). Una respuesta vieja se descarta si
 * mientras tanto cambió el profesional, los días o `reloadKey` (D-4).
 */
export function useAgendaData(
  professionalId: string | null,
  dates: readonly string[],
  reloadKey: number,
): AgendaData {
  const datesKey = dates.join(',')
  const requestKey = `${professionalId ?? ''}|${datesKey}|${String(reloadKey)}`
  const [result, setResult] = useState<{ key: string; data: AgendaData } | null>(null)

  useEffect(() => {
    if (professionalId === null) return
    let active = true
    void load(professionalId, datesKey.split(',')).then((data) => {
      if (active) setResult({ key: requestKey, data })
    })
    return () => {
      active = false
    }
  }, [professionalId, datesKey, requestKey])

  return result?.key === requestKey ? result.data : { status: 'loading' }
}
