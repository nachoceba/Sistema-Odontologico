import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import type { Appointment } from '../api/appointments'
import type { Conflict } from '../api/professionals'
import { turno } from '../agenda/fixtures'
import { DRA, installAgendaApi, type AgendaWorld } from '../agenda/testApi'
import { jsonResponse } from '../test-utils'
import { DENTIST_A, endSession, lastLocation, open, startSession, world } from './pageHarness'

const LEAVE = [{ id: 't-1', starts_on: '2026-11-12', ends_on: '2026-11-12', reason: 'Congreso' }]

function conflictOf(a: Appointment, reason: Conflict['reason'] = 'TIME_OFF'): Conflict {
  return {
    appointment_id: a.id,
    patient_id: a.patient_id,
    professional_id: a.professional_id,
    starts_at: a.starts_at,
    ends_at: a.ends_at,
    reason,
  }
}

function leaveWorld(overrides: Partial<AgendaWorld> = {}) {
  const nine = turno(9, 0, 9, 30, { patient_last_name: 'Perez' }, 12)
  const ten = turno(10, 0, 10, 30, { patient_last_name: 'Gomez', patient_first_name: 'Ana' }, 12)
  return {
    nine,
    ten,
    data: world({
      appointments: [nine, ten],
      timeOff: LEAVE,
      conflicts: [conflictOf(nine), conflictOf(ten)],
      ...overrides,
    }),
  }
}

const WEEK = '/agenda?vista=semana&fecha=2026-11-02'
const list = () => screen.findByRole('region', { name: /en conflicto/ })

// Miércoles 04/11 a las 12:00 en el consultorio.
beforeEach(() => {
  startSession('2026-11-04T15:00:00Z')
})
afterEach(endSession)

describe('lista de turnos en conflicto', () => {
  it('recepción ve los dos turnos con fecha, nombre, motivo y botones', async () => {
    const api = installAgendaApi(leaveWorld().data)
    open(WEEK)

    const panel = within(await list())
    expect(panel.getByRole('heading', { name: '2 turnos en conflicto' })).toBeInTheDocument()
    expect(await panel.findByText('Jue 12/11 09:00–09:30')).toBeInTheDocument()
    expect(panel.getByText('Jue 12/11 10:00–10:30')).toBeInTheDocument()
    expect(await panel.findByText('Perez, Juan')).toBeInTheDocument()
    expect(await panel.findByText('Gomez, Ana')).toBeInTheDocument()
    expect(panel.getAllByText('En conflicto: en licencia')).toHaveLength(2)
    expect(panel.getAllByRole('button', { name: 'Reprogramar' })).toHaveLength(2)
    expect(panel.getAllByRole('button', { name: 'Cancelar' })).toHaveLength(2)
    expect(panel.getAllByRole('button', { name: 'Ver en la agenda' })).toHaveLength(2)
    expect(api.calls.filter((c) => c.startsWith('GET /appointments/')).length).toBe(2)
  })

  it('con un solo conflicto el título va en singular', async () => {
    const { nine, data } = leaveWorld()
    data.conflicts = [conflictOf(nine)]
    installAgendaApi(data)
    open(WEEK)

    expect(
      within(await list()).getByRole('heading', { name: '1 turno en conflicto' }),
    ).toBeInTheDocument()
  })

  it('un conflicto de otra semana también figura', async () => {
    const later = turno(10, 0, 10, 30, {}, 25)
    installAgendaApi(world({ appointments: [later], conflicts: [conflictOf(later)] }))
    open(WEEK)

    const panel = within(await list())
    expect(await panel.findByText('Mié 25/11 10:00–10:30')).toBeInTheDocument()
  })

  it('sin conflictos no hay aviso', async () => {
    installAgendaApi(world())
    open(WEEK)
    await screen.findAllByText('Libre')

    expect(screen.queryByRole('region', { name: /en conflicto/ })).not.toBeInTheDocument()
  })

  it('cancelar desde la lista deja un solo turno en conflicto', async () => {
    const { nine, data } = leaveWorld()
    const api = installAgendaApi(data)
    open(WEEK)
    const panel = within(await list())
    await panel.findByText('Perez, Juan')

    fireEvent.click(panel.getAllByRole('button', { name: 'Cancelar' })[0] as HTMLElement)
    fireEvent.change(screen.getByLabelText('Motivo'), {
      target: { value: 'La profesional está de licencia' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }))

    expect(await screen.findByText('Turno cancelado')).toBeInTheDocument()
    expect(
      await within(await list()).findByRole('heading', { name: '1 turno en conflicto' }),
    ).toBeInTheDocument()
    expect(within(await list()).getByText('Jue 12/11 10:00–10:30')).toBeInTheDocument()
    expect(api.posts).toEqual([
      {
        path: `/appointments/${nine.id}/cancel`,
        body: { reason: 'La profesional está de licencia' },
      },
    ])
  })

  it('reprogramar desde la lista al 16/11 saca el turno de la lista', async () => {
    const { nine, ten, data } = leaveWorld()
    data.conflicts = [conflictOf(ten)]
    data.appointments = [nine, ten]
    const api = installAgendaApi(data)
    open(WEEK)
    const panel = within(await list())
    await panel.findByText('Gomez, Ana')

    fireEvent.click(panel.getByRole('button', { name: 'Reprogramar' }))
    fireEvent.change(within(screen.getByRole('dialog')).getByLabelText('Fecha'), {
      target: { value: '2026-11-16' },
    })
    fireEvent.click(await screen.findByRole('button', { name: '10:00–10:30' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar turno' }))

    expect(await screen.findByText('Turno reprogramado: Lun 16/11 10:00')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByRole('region', { name: /en conflicto/ })).not.toBeInTheDocument()
    })
    expect(api.posts).toHaveLength(1)
  })

  it('PROFESSIONAL_TIME_OFF al reprogramar deja el turno en la lista', async () => {
    const { data } = leaveWorld({
      override: (method, path) =>
        method === 'POST' && path.endsWith('/reschedule')
          ? jsonResponse({ error: { code: 'PROFESSIONAL_TIME_OFF', message: 'x' } }, 409)
          : undefined,
    })
    installAgendaApi(data)
    open(WEEK)
    const panel = within(await list())
    await panel.findByText('Perez, Juan')

    fireEvent.click(panel.getAllByRole('button', { name: 'Reprogramar' })[0] as HTMLElement)
    fireEvent.change(within(screen.getByRole('dialog')).getByLabelText('Fecha'), {
      target: { value: '2026-11-13' },
    })
    fireEvent.click(await screen.findByRole('button', { name: '11:00–11:30' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El profesional está de licencia ese día',
    )
    expect(
      within(await list()).getByRole('heading', { name: '2 turnos en conflicto' }),
    ).toBeInTheDocument()
  })

  it('Ver en la agenda abre la vista Día de esa fecha', async () => {
    installAgendaApi(leaveWorld().data)
    open(WEEK)
    const panel = within(await list())
    await panel.findByText('Perez, Juan')

    fireEvent.click(panel.getAllByRole('button', { name: 'Ver en la agenda' })[0] as HTMLElement)

    await waitFor(() => {
      expect(lastLocation()).toContain('fecha=2026-11-12')
    })
    expect(lastLocation()).toContain('vista=dia')
  })

  it('con el profesional inactivo ofrece Cancelar y Ver en la agenda, no Reprogramar', async () => {
    const inactive = { ...DRA, active: false }
    const a = turno(10, 0, 10, 30, {}, 12)
    installAgendaApi(
      world({ professionals: [inactive], appointments: [a], conflicts: [conflictOf(a)] }),
    )
    open(WEEK)

    const panel = within(await list())
    await panel.findByText('Perez, Juan')
    expect(panel.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
    expect(panel.getByRole('button', { name: 'Ver en la agenda' })).toBeInTheDocument()
    expect(panel.queryByRole('button', { name: 'Reprogramar' })).not.toBeInTheDocument()
  })

  it('si el nombre no se puede leer el turno sigue listado con Ver en la agenda', async () => {
    const { data } = leaveWorld({
      override: (method, path) =>
        method === 'GET' && path.startsWith('/appointments/')
          ? jsonResponse({ error: { code: 'X', message: 'x' } }, 500)
          : undefined,
    })
    installAgendaApi(data)
    open(WEEK)

    const panel = within(await list())
    expect(await panel.findAllByText('No se pudo cargar el paciente')).toHaveLength(2)
    expect(panel.getAllByRole('button', { name: 'Ver en la agenda' })).toHaveLength(2)
    expect(panel.queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument()
  })
})

describe('turno en conflicto en la grilla', () => {
  it('recepción lo abre con su aviso, Reprogramar y Cancelar', async () => {
    installAgendaApi(leaveWorld().data)
    open('/agenda?fecha=2026-11-12')

    fireEvent.click(await screen.findByRole('button', { name: /10:00–10:30 Gomez, Ana/ }))

    const detail = within(await screen.findByRole('complementary'))
    expect(detail.getByText('En conflicto: en licencia')).toBeInTheDocument()
    expect(detail.getByRole('button', { name: 'Reprogramar' })).toBeInTheDocument()
    expect(detail.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
  })

  it('la odontóloga ve la marca sin aviso ni acciones para resolverlo', async () => {
    installAgendaApi(leaveWorld({ me: DENTIST_A, professionals: [DRA] }).data)
    open('/agenda?fecha=2026-11-12')

    fireEvent.click(await screen.findByRole('button', { name: /10:00–10:30 Gomez, Ana/ }))

    const detail = within(await screen.findByRole('complementary'))
    expect(detail.getByText('En conflicto: en licencia')).toBeInTheDocument()
    expect(detail.queryByRole('button', { name: 'Reprogramar' })).not.toBeInTheDocument()
    expect(detail.queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: /en conflicto/ })).not.toBeInTheDocument()
  })
})
