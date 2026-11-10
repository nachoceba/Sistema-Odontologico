import type {
  Appointment,
  AppointmentOrigin,
  AppointmentStatus,
  Slot,
} from '../api/appointments'
import type { Conflict, ConflictReason, TimeOff } from '../api/professionals'

/** Un turno listo para dibujar; los instantes siguen en UTC y la hora local la pone la vista. */
export interface AppointmentItem {
  id: string
  startsAt: string
  endsAt: string
  status: AppointmentStatus
  /** `Apellido, Nombre` (DD-79); nunca datos de contacto. */
  patientName: string
  conflict: ConflictReason | null
  origin: AppointmentOrigin
  /** Instante UTC hasta el que espera la confirmación del paciente, o null. */
  pendingUntil: string | null
  /** Nombre del tratamiento (C-17); null en los turnos anteriores. */
  treatmentName: string | null
}

/**
 * Filas de una columna de día. `free` y `busy` son franjas del servidor; `appointments` lleva
 * los turnos que empiezan en ella (los cancelados, atendidos y ausentes van al lado de la
 * franja). `appointment` es un turno que no cae en ninguna franja libre u ocupada.
 */
export type GridRow =
  | { kind: 'free'; key: string; startsAt: string; endsAt: string; appointments: AppointmentItem[] }
  | { kind: 'busy'; key: string; startsAt: string; endsAt: string; appointments: AppointmentItem[] }
  | { kind: 'outside'; key: string; startsAt: string; endsAt: string }
  | {
      kind: 'appointment'
      key: string
      startsAt: string
      endsAt: string
      appointment: AppointmentItem
    }

export type DayHeader =
  | { kind: 'normal' }
  | { kind: 'no_hours' }
  | { kind: 'time_off'; reason: string | null }

export interface DayColumn {
  date: string
  header: DayHeader
  rows: GridRow[]
}

export interface DayColumnInput {
  date: string
  slots: readonly Slot[]
  appointments: readonly Appointment[]
  timeOff: readonly TimeOff[]
  conflicts: readonly Conflict[]
}

function headerFor(date: string, timeOff: readonly TimeOff[], hasHours: boolean): DayHeader {
  const leave = timeOff.find((entry) => entry.starts_on <= date && date <= entry.ends_on)
  if (leave !== undefined) return { kind: 'time_off', reason: leave.reason }
  return hasHours ? { kind: 'normal' } : { kind: 'no_hours' }
}

const ms = (instant: string): number => Date.parse(instant)

function toItem(
  appointment: Appointment,
  conflictById: ReadonlyMap<string, ConflictReason>,
): AppointmentItem {
  return {
    id: appointment.id,
    startsAt: appointment.starts_at,
    endsAt: appointment.ends_at,
    status: appointment.status,
    patientName: `${appointment.patient_last_name}, ${appointment.patient_first_name}`,
    conflict: appointment.status === 'scheduled' ? (conflictById.get(appointment.id) ?? null) : null,
    origin: appointment.origin,
    pendingUntil: appointment.status === 'scheduled' ? appointment.pending_until : null,
    treatmentName: appointment.treatment_name,
  }
}

function overlaps(aStart: string, aEnd: string, bStart: string, bEnd: string): boolean {
  return ms(aStart) < ms(bEnd) && ms(bStart) < ms(aEnd)
}

/**
 * Arma la columna de un día (design D-3, DD-80): franjas libres y ocupadas, bandas de "fuera de
 * horario" juntas y recortadas a la primera y última franja con atención (o turno), y los turnos
 * que no calzan con una franja como filas propias.
 */
export function buildDayColumn(input: DayColumnInput): DayColumn {
  const { slots } = input
  const conflictById = new Map<string, ConflictReason>(
    input.conflicts.map((conflict) => [conflict.appointment_id, conflict.reason]),
  )
  const dayStart = slots[0]?.starts_at
  const dayEnd = slots.at(-1)?.ends_at
  const items =
    dayStart === undefined || dayEnd === undefined
      ? []
      : input.appointments
          .filter((a) => overlaps(a.starts_at, a.ends_at, dayStart, dayEnd))
          .map((a) => toItem(a, conflictById))

  const worked = slots.filter((slot) => slot.status !== 'OUTSIDE_HOURS')
  const starts = [...worked.map((s) => ms(s.starts_at)), ...items.map((i) => ms(i.startsAt))]
  const ends = [...worked.map((s) => ms(s.ends_at)), ...items.map((i) => ms(i.endsAt))]
  if (starts.length === 0 || dayStart === undefined || dayEnd === undefined) {
    return { date: input.date, header: headerFor(input.date, input.timeOff, false), rows: [] }
  }
  const low = Math.max(Math.min(...starts), ms(dayStart))
  const high = Math.min(Math.max(...ends), ms(dayEnd))

  const rows: GridRow[] = []
  const visible = slots.filter((s) => ms(s.ends_at) > low && ms(s.starts_at) < high)

  // Cada turno `scheduled` se pone en la primera franja ocupada que toca; el resto, en la franja
  // donde empieza.
  const homeOf = new Map<string, number>()
  items.forEach((item) => {
    const busyIndex = visible.findIndex(
      (s) => s.status === 'BUSY' && overlaps(s.starts_at, s.ends_at, item.startsAt, item.endsAt),
    )
    const startIndex = visible.findIndex(
      (s) =>
        s.status !== 'OUTSIDE_HOURS' && ms(s.starts_at) <= ms(item.startsAt) && ms(item.startsAt) < ms(s.ends_at),
    )
    const index = item.status === 'scheduled' ? busyIndex : startIndex
    if (index >= 0) homeOf.set(item.id, index)
  })

  const standalone = items.filter((item) => !homeOf.has(item.id))

  let band: { startsAt: string; endsAt: string } | null = null
  const flushBand = (): void => {
    if (band !== null) {
      rows.push({ kind: 'outside', key: `outside-${band.startsAt}`, ...band })
      band = null
    }
  }
  visible.forEach((slot, index) => {
    if (slot.status === 'OUTSIDE_HOURS') {
      // La fila propia de un turno ocupa su hora: la banda se corta ahí.
      if (standalone.some((item) => overlaps(slot.starts_at, slot.ends_at, item.startsAt, item.endsAt))) {
        flushBand()
        return
      }
      band = band === null ? { startsAt: slot.starts_at, endsAt: slot.ends_at } : { ...band, endsAt: slot.ends_at }
      return
    }
    flushBand()
    const here = items.filter((item) => homeOf.get(item.id) === index)
    rows.push({
      kind: slot.status === 'BUSY' ? 'busy' : 'free',
      key: `slot-${slot.starts_at}`,
      startsAt: slot.starts_at,
      endsAt: slot.ends_at,
      appointments: here,
    })
  })
  flushBand()

  standalone.forEach((item) => {
      rows.push({
        kind: 'appointment',
        key: `appointment-${item.id}`,
        startsAt: item.startsAt,
        endsAt: item.endsAt,
        appointment: item,
    })
  })

  const order = { outside: 0, free: 1, busy: 1, appointment: 2 } as const
  rows.sort((a, b) => ms(a.startsAt) - ms(b.startsAt) || order[a.kind] - order[b.kind])
  return { date: input.date, header: headerFor(input.date, input.timeOff, true), rows }
}
