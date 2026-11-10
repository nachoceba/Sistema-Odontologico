import { describe, expect, it } from 'vitest'
import { at, daySlots, turno } from './fixtures'
import { buildDayColumn, type GridRow } from './grid'

const DATE = '2026-11-09'
const EMPTY = { timeOff: [], conflicts: [] }
const DRA_A = [
  [9, 13],
  [14, 18],
] as const

function summary(rows: GridRow[]): string[] {
  return rows.map((row) => `${row.kind} ${row.startsAt}`)
}

describe('buildDayColumn: vista del día', () => {
  it('día de la Dra. A: de 09:00 a 18:00, un turno a las 10:00 y una banda 13:00-14:00', () => {
    const juan = turno(10, 0, 10, 30)
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots(DRA_A, { busy: ['10:00'] }),
      appointments: [juan],
      ...EMPTY,
    })

    expect(column.header).toEqual({ kind: 'normal' })
    expect(column.rows[0]).toMatchObject({ kind: 'free', startsAt: at(9) })
    expect(column.rows.at(-1)).toMatchObject({ kind: 'free', endsAt: at(18) })
    const busy = column.rows.find((row) => row.kind === 'busy')
    expect(busy).toMatchObject({ startsAt: at(10), appointments: [{ id: juan.id }] })
    const outside = column.rows.filter((row) => row.kind === 'outside')
    expect(outside).toHaveLength(1)
    expect(outside[0]).toMatchObject({ startsAt: at(13), endsAt: at(14) })
    // 9:00-13:00 son 8 franjas, 14:00-18:00 son 8 franjas más la banda: 17 filas
    expect(column.rows).toHaveLength(17)
    expect(column.rows.filter((row) => row.kind === 'free')).toHaveLength(15)
  })

  it('sin tramos ni turnos: sin atención este día y ninguna fila', () => {
    const column = buildDayColumn({
      date: '2026-11-15',
      slots: daySlots([], { day: 15 }),
      appointments: [],
      ...EMPTY,
    })

    expect(column.header).toEqual({ kind: 'no_hours' })
    expect(column.rows).toEqual([])
  })

  it('resto de tramo que no alcanza para un slot: termina en 10:30 sin banda final', () => {
    // tramo 09:00-10:45: el servidor marca libres 09:00, 09:30 y 10:00 y fuera el resto
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([[9, 10]], { endMinute: 45 }),
      appointments: [],
      ...EMPTY,
    })

    expect(column.rows.map((row) => row.kind)).toEqual(['free', 'free', 'free'])
    expect(column.rows.at(-1)).toMatchObject({ startsAt: at(10), endsAt: at(10, 30) })
  })

  it('turno desalineado: se ve en su hora y las dos franjas que ocupa dicen ocupado', () => {
    const odd = turno(9, 15, 9, 45)
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([[9, 11]], { busy: ['09:00', '09:30'] }),
      appointments: [odd],
      ...EMPTY,
    })

    expect(column.rows.map((row) => row.kind)).toEqual(['busy', 'busy', 'free', 'free'])
    const [first, second] = column.rows
    expect(first).toMatchObject({ appointments: [{ id: odd.id, startsAt: at(9, 15), endsAt: at(9, 45) }] })
    expect(second).toMatchObject({ kind: 'busy', appointments: [] })
  })

  it('turno fuera de horario: aparece en su hora y estira el rango', () => {
    const late = turno(19, 0, 19, 30)
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([[9, 12]]),
      appointments: [late],
      ...EMPTY,
    })

    expect(column.rows.at(-1)).toMatchObject({ kind: 'appointment', startsAt: at(19) })
    expect(column.rows.at(-2)).toMatchObject({ kind: 'outside', startsAt: at(12), endsAt: at(19) })
    expect(column.rows[0]).toMatchObject({ kind: 'free', startsAt: at(9) })
  })

  it('turno antes del primer tramo: estira el rango hacia atrás', () => {
    const early = turno(7, 0, 7, 30)
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([[9, 11]]),
      appointments: [early],
      ...EMPTY,
    })

    expect(summary(column.rows).slice(0, 2)).toEqual([`appointment ${at(7)}`, `outside ${at(7, 30)}`])
    expect(column.rows[1]).toMatchObject({ endsAt: at(9) })
  })

  it('turno que cruza la medianoche: aparece en los dos días', () => {
    const crossing = turno(23, 45, 0, 15, {
      ends_at: at(0, 15, 10),
    })
    const monday = buildDayColumn({
      date: DATE,
      slots: daySlots([[22, 24]]),
      appointments: [crossing],
      ...EMPTY,
    })
    const tuesday = buildDayColumn({
      date: '2026-11-10',
      slots: daySlots([[0, 2]], { day: 10 }),
      appointments: [crossing],
      ...EMPTY,
    })

    expect(monday.rows.some((row) => row.kind === 'appointment' && row.appointment.id === crossing.id)).toBe(true)
    expect(tuesday.rows.some((row) => row.kind === 'appointment' && row.appointment.id === crossing.id)).toBe(true)
  })

  it('un turno de otro día no entra', () => {
    const other = turno(10, 0, 10, 30, {}, 10)
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([[9, 11]]),
      appointments: [other],
      ...EMPTY,
    })

    expect(column.rows.every((row) => row.kind === 'free')).toBe(true)
  })
})

describe('buildDayColumn: turnos y sus estados', () => {
  const slots = () => daySlots([[9, 13]], { busy: [] })

  it('cancelado deja la franja libre y se ve a su lado', () => {
    const cancelled = turno(11, 0, 11, 30, { status: 'cancelled', cancel_reason: 'aviso' })
    const column = buildDayColumn({ date: DATE, slots: slots(), appointments: [cancelled], ...EMPTY })

    const row = column.rows.find((r) => r.startsAt === at(11))
    expect(row).toMatchObject({ kind: 'free', appointments: [{ id: cancelled.id, status: 'cancelled' }] })
  })

  it('atendido y ausente se ven con su estado en su hora', () => {
    const done = turno(9, 0, 9, 30, { status: 'completed' })
    const absent = turno(9, 30, 10, 0, { status: 'no_show', patient_last_name: 'Gomez' })
    const column = buildDayColumn({ date: DATE, slots: slots(), appointments: [done, absent], ...EMPTY })

    expect(column.rows[0]).toMatchObject({ appointments: [{ status: 'completed', patientName: 'Perez, Juan' }] })
    expect(column.rows[1]).toMatchObject({ appointments: [{ status: 'no_show', patientName: 'Gomez, Juan' }] })
  })

  it('cancelado y nuevo turno en la misma hora: la franja queda ocupada por el agendado', () => {
    const cancelled = turno(11, 0, 11, 30, { status: 'cancelled', patient_last_name: 'Gomez', patient_first_name: 'Ana' })
    const juan = turno(11, 0, 11, 30)
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([[9, 13]], { busy: ['11:00'] }),
      appointments: [cancelled, juan],
      ...EMPTY,
    })

    const row = column.rows.find((r) => r.startsAt === at(11))
    expect(row?.kind).toBe('busy')
    expect(row).toMatchObject({
      appointments: [
        { id: cancelled.id, status: 'cancelled', patientName: 'Gomez, Ana' },
        { id: juan.id, status: 'scheduled', patientName: 'Perez, Juan' },
      ],
    })
  })

  it('el nombre es apellido y nombre solamente', () => {
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([[9, 13]], { busy: ['10:00'] }),
      appointments: [turno(10, 0, 10, 30)],
      ...EMPTY,
    })
    const busy = column.rows.find((r) => r.kind === 'busy')
    expect(Object.keys((busy as { appointments: object[] }).appointments[0] ?? {}).sort()).toEqual(
      [
        'conflict',
        'endsAt',
        'id',
        'origin',
        'patientName',
        'pendingUntil',
        'startsAt',
        'status',
        'treatmentName',
      ],
    )
  })
})

describe('buildDayColumn: licencias y conflictos', () => {
  const LEAVE = { id: 't-1', starts_on: '2026-11-09', ends_on: '2026-11-10', reason: 'Congreso' }

  it('día de licencia con motivo: encabezado de licencia y ninguna franja', () => {
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([]),
      appointments: [],
      timeOff: [LEAVE],
      conflicts: [],
    })

    expect(column.header).toEqual({ kind: 'time_off', reason: 'Congreso' })
    expect(column.rows).toEqual([])
  })

  it('licencia sin motivo, y el último día de la licencia cuenta (inclusivo)', () => {
    const column = buildDayColumn({
      date: '2026-11-10',
      slots: daySlots([], { day: 10 }),
      appointments: [],
      timeOff: [{ ...LEAVE, reason: null }],
      conflicts: [],
    })
    expect(column.header).toEqual({ kind: 'time_off', reason: null })
  })

  it('el día siguiente a la licencia no la muestra', () => {
    const column = buildDayColumn({
      date: '2026-11-11',
      slots: daySlots([[9, 10]], { day: 11 }),
      appointments: [],
      timeOff: [LEAVE],
      conflicts: [],
    })
    expect(column.header).toEqual({ kind: 'normal' })
  })

  it('turno agendado en licencia: se ve con "en licencia" bajo el encabezado de licencia', () => {
    const booked = turno(10, 0, 10, 30)
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([]),
      appointments: [booked],
      timeOff: [LEAVE],
      conflicts: [
        {
          appointment_id: booked.id,
          patient_id: 'pac-1',
          professional_id: 'p-1',
          starts_at: booked.starts_at,
          ends_at: booked.ends_at,
          reason: 'TIME_OFF',
        },
      ],
    })

    expect(column.header).toEqual({ kind: 'time_off', reason: 'Congreso' })
    expect(column.rows).toHaveLength(1)
    expect(column.rows[0]).toMatchObject({ kind: 'appointment', appointment: { conflict: 'TIME_OFF' } })
  })

  it('turno fuera del horario nuevo: fila propia con el aviso de fuera de horario', () => {
    const late = turno(17, 30, 18, 0)
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([[9, 13]]),
      appointments: [late],
      timeOff: [],
      conflicts: [
        {
          appointment_id: late.id,
          patient_id: 'pac-1',
          professional_id: 'p-1',
          starts_at: late.starts_at,
          ends_at: late.ends_at,
          reason: 'OUTSIDE_WORKING_HOURS',
        },
      ],
    })

    expect(column.rows.at(-1)).toMatchObject({
      kind: 'appointment',
      startsAt: at(17, 30),
      appointment: { conflict: 'OUTSIDE_WORKING_HOURS' },
    })
  })

  it('turno pasado en licencia sin aviso: no está en conflictos, se ve sin aviso', () => {
    const past = turno(10, 0, 10, 30)
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([]),
      appointments: [past],
      timeOff: [LEAVE],
      conflicts: [],
    })

    expect(column.header).toEqual({ kind: 'time_off', reason: 'Congreso' })
    expect(column.rows[0]).toMatchObject({ appointment: { conflict: null } })
  })

  it('un turno cancelado nunca lleva aviso aunque figure en conflictos', () => {
    const cancelled = turno(10, 0, 10, 30, { status: 'cancelled' })
    const column = buildDayColumn({
      date: DATE,
      slots: daySlots([]),
      appointments: [cancelled],
      timeOff: [],
      conflicts: [
        {
          appointment_id: cancelled.id,
          patient_id: 'pac-1',
          professional_id: 'p-1',
          starts_at: cancelled.starts_at,
          ends_at: cancelled.ends_at,
          reason: 'TIME_OFF',
        },
      ],
    })
    expect(column.rows[0]).toMatchObject({ appointment: { conflict: null } })
  })
})
