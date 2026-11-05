import type { Appointment, Slot, SlotStatus } from '../api/appointments'

/** Instante UTC (ISO) de una hora local del consultorio (UTC-3) del día dado de noviembre 2026. */
export function at(hour: number, minute = 0, day = 9): string {
  return new Date(Date.UTC(2026, 10, day, hour + 3, minute)).toISOString().replace('.000Z', 'Z')
}

type Block = readonly [number, number] // [hora de inicio, hora de fin]

/**
 * Franjas de un día completo (00:00 a 24:00) de `step` minutos: libres dentro de los tramos,
 * ocupadas en los inicios de `busy` ("HH:MM") y fuera de horario en el resto.
 */
export function daySlots(
  blocks: readonly Block[],
  { day = 9, step = 30, busy = [] as string[], endMinute = 0 } = {},
): Slot[] {
  const slots: Slot[] = []
  for (let minute = 0; minute < 24 * 60; minute += step) {
    const hour = Math.floor(minute / 60)
    const label = `${String(hour).padStart(2, '0')}:${String(minute % 60).padStart(2, '0')}`
    const insideBlock = blocks.some(
      ([from, to]) => minute >= from * 60 && minute + step <= to * 60 + endMinute,
    )
    const status: SlotStatus = !insideBlock
      ? 'OUTSIDE_HOURS'
      : busy.includes(label)
        ? 'BUSY'
        : 'FREE'
    slots.push({
      starts_at: at(hour, minute % 60, day),
      ends_at: at(Math.floor((minute + step) / 60), (minute + step) % 60, day),
      status,
    })
  }
  return slots
}

let counter = 0

export function turno(
  startHour: number,
  startMinute: number,
  endHour: number,
  endMinute: number,
  overrides: Partial<Appointment> = {},
  day = 9,
): Appointment {
  counter += 1
  return {
    id: `a-${String(counter)}`,
    patient_id: 'pac-1',
    patient_first_name: 'Juan',
    patient_last_name: 'Perez',
    professional_id: 'p-1',
    starts_at: at(startHour, startMinute, day),
    ends_at: at(endHour, endMinute, day),
    status: 'scheduled',
    cancel_reason: null,
    created_by: 'u-rec',
    ...overrides,
  }
}
