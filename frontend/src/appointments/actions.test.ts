import { describe, expect, it } from 'vitest'
import type { Role } from '../auth/AuthContext'
import { appointmentActions, slotActions } from './actions'

const NOW = new Date('2026-11-09T13:00:00Z') // 10:00 en el consultorio
const BEFORE = '2026-11-09T12:30:00Z'
const AFTER = '2026-11-09T13:30:00Z'

describe('slotActions', () => {
  const base = { professionalActive: true, now: NOW, slot: { startsAt: AFTER } }

  it.each<[Role, boolean]>([
    ['admin', true],
    ['receptionist', true],
    ['dentist', false],
  ])('franja libre futura: %s -> agendar %s', (role, book) => {
    expect(slotActions({ ...base, role })).toEqual({ book })
  })

  it('una franja que ya empezó no se agenda', () => {
    expect(slotActions({ ...base, role: 'receptionist', slot: { startsAt: BEFORE } }).book).toBe(false)
  })

  it('una franja que empieza justo ahora no se agenda', () => {
    expect(
      slotActions({ ...base, role: 'receptionist', slot: { startsAt: NOW.toISOString() } }).book,
    ).toBe(false)
  })

  it('un profesional inactivo no recibe turnos nuevos', () => {
    expect(slotActions({ ...base, role: 'admin', professionalActive: false }).book).toBe(false)
  })
})

describe('appointmentActions', () => {
  const none = { cancel: false, reschedule: false, markAttendance: false }
  const future = { status: 'scheduled' as const, startsAt: AFTER, professionalId: 'p-1' }
  const started = { status: 'scheduled' as const, startsAt: BEFORE, professionalId: 'p-1' }
  const base = { ownProfessionalId: null, professionalActive: true, now: NOW }

  it.each<[Role]>([['admin'], ['receptionist']])(
    '%s: turno agendado futuro permite cancelar y reprogramar, no marcar',
    (role) => {
      expect(appointmentActions({ ...base, role, appointment: future })).toEqual({
        cancel: true,
        reschedule: true,
        markAttendance: false,
      })
    },
  )

  it('recepción: turno agendado iniciado solo permite marcar', () => {
    expect(appointmentActions({ ...base, role: 'receptionist', appointment: started })).toEqual({
      cancel: false,
      reschedule: false,
      markAttendance: true,
    })
  })

  it('turno en su inicio exacto: marca sí, cancela y reprograma no (DD-23)', () => {
    const exact = { ...future, startsAt: NOW.toISOString() }
    expect(appointmentActions({ ...base, role: 'receptionist', appointment: exact })).toEqual({
      cancel: false,
      reschedule: false,
      markAttendance: true,
    })
  })

  it('odontóloga con su turno iniciado solo marca', () => {
    expect(
      appointmentActions({ ...base, role: 'dentist', ownProfessionalId: 'p-1', appointment: started }),
    ).toEqual({ cancel: false, reschedule: false, markAttendance: true })
  })

  it('odontóloga con su turno futuro no tiene nada', () => {
    expect(
      appointmentActions({ ...base, role: 'dentist', ownProfessionalId: 'p-1', appointment: future }),
    ).toEqual(none)
  })

  it('odontólogo con un turno ajeno no tiene nada', () => {
    expect(
      appointmentActions({ ...base, role: 'dentist', ownProfessionalId: 'p-2', appointment: started }),
    ).toEqual(none)
  })

  it('profesional inactivo: cancela y marca, no reprograma', () => {
    expect(
      appointmentActions({
        ...base,
        role: 'receptionist',
        professionalActive: false,
        appointment: future,
      }),
    ).toEqual({ cancel: true, reschedule: false, markAttendance: false })
    expect(
      appointmentActions({
        ...base,
        role: 'receptionist',
        professionalActive: false,
        appointment: started,
      }).markAttendance,
    ).toBe(true)
  })

  it.each(['cancelled', 'completed', 'no_show'] as const)('un turno %s no ofrece acciones', (status) => {
    for (const role of ['admin', 'receptionist', 'dentist'] as const) {
      expect(
        appointmentActions({
          ...base,
          role,
          ownProfessionalId: 'p-1',
          appointment: { ...started, status },
        }),
      ).toEqual(none)
    }
  })
})
