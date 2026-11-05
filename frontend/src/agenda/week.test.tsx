import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { clearToken, saveToken } from '../auth/session'
import { BASE } from '../test-utils'
import { turno } from './fixtures'
import { DR_B, DRA, installAgendaApi, type AgendaWorld } from './testApi'

const RECEPTIONIST = {
  id: 'u-rec',
  email: 'rec@example.com',
  full_name: 'Rec Demo',
  role: 'receptionist',
  professional_id: null,
}

function Probe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname + location.search}</output>
}

function open(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
      <Probe />
    </MemoryRouter>,
  )
}

function world(overrides: Partial<AgendaWorld> = {}): AgendaWorld {
  return {
    me: RECEPTIONIST,
    professionals: [DRA, DR_B],
    appointments: [],
    timeOff: [],
    conflicts: [],
    ...overrides,
  }
}

const location = () => screen.getByTestId('location').textContent
const day = (label: string) => screen.getByRole('region', { name: label })

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-09T15:00:00Z'))
  clearToken()
  window.sessionStorage.clear()
  saveToken('tok')
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('vista de la semana', () => {
  it('muestra siete columnas de lunes a domingo; sábado y domingo sin atención', async () => {
    const api = installAgendaApi(world())
    open('/agenda?vista=semana&fecha=2026-11-09')

    await screen.findByRole('region', { name: 'Lun 09/11' })

    const labels = screen.getAllByRole('region').map((r) => r.getAttribute('aria-label'))
    expect(labels).toEqual([
      'Lun 09/11',
      'Mar 10/11',
      'Mié 11/11',
      'Jue 12/11',
      'Vie 13/11',
      'Sáb 14/11',
      'Dom 15/11',
    ])
    expect(within(day('Sáb 14/11')).getByText('Sin atención este día')).toBeInTheDocument()
    expect(within(day('Dom 15/11')).getByText('Sin atención este día')).toBeInTheDocument()
    expect(api.calls.filter((c) => c.includes('/slots'))).toHaveLength(7)
    expect(api.calls.filter((c) => c.startsWith('GET /appointments'))).toHaveLength(1)
  })

  it('una fecha de jueves muestra la semana del lunes 09/11 al domingo 15/11', async () => {
    installAgendaApi(world())
    open('/agenda?vista=semana&fecha=2026-11-12')

    await screen.findByRole('region', { name: 'Lun 09/11' })

    expect(screen.getAllByRole('region')).toHaveLength(7)
    expect(screen.getByRole('region', { name: 'Dom 15/11' })).toBeInTheDocument()
  })

  it('destaca el día de hoy', async () => {
    installAgendaApi(world())
    open('/agenda?vista=semana&fecha=2026-11-09')

    await screen.findByRole('region', { name: 'Lun 09/11' })

    expect(day('Lun 09/11')).toHaveClass('day-column--today')
    expect(day('Mar 10/11')).not.toHaveClass('day-column--today')
  })

  it('elegir el miércoles abre la vista Día del 11/11 del mismo profesional', async () => {
    installAgendaApi(world())
    open('/agenda?profesional=p-2&vista=semana&fecha=2026-11-09')
    await screen.findByRole('region', { name: 'Mié 11/11' })

    fireEvent.click(screen.getByRole('button', { name: 'Mié 11/11' }))

    await waitFor(() => {
      expect(screen.getAllByRole('region')).toHaveLength(1)
    })
    expect(location()).toContain('vista=dia')
    expect(location()).toContain('fecha=2026-11-11')
    expect(location()).toContain('profesional=p-2')
  })

  it('licencia del jueves y viernes con su motivo, y un turno en conflicto el jueves', async () => {
    const booked = turno(10, 0, 10, 30, {}, 12)
    installAgendaApi(
      world({
        timeOff: [{ id: 't', starts_on: '2026-11-12', ends_on: '2026-11-13', reason: 'Congreso' }],
        appointments: [booked],
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
      }),
    )
    open('/agenda?vista=semana&fecha=2026-11-09')
    await screen.findByRole('region', { name: 'Jue 12/11' })

    expect(within(day('Jue 12/11')).getByText('Licencia: Congreso')).toBeInTheDocument()
    expect(within(day('Vie 13/11')).getByText('Licencia: Congreso')).toBeInTheDocument()
    expect(within(day('Mié 11/11')).queryByText(/Licencia/)).not.toBeInTheDocument()
    expect(within(day('Jue 12/11')).getByText('En conflicto: en licencia')).toBeInTheDocument()
    expect(within(day('Jue 12/11')).getByText('10:00–10:30 Perez, Juan')).toBeInTheDocument()
  })

  it('cada turno aparece en su día y no en los demás', async () => {
    installAgendaApi(world({ appointments: [turno(10, 0, 10, 30, {}, 11)] }))
    open('/agenda?vista=semana&fecha=2026-11-09')
    await screen.findByRole('region', { name: 'Mié 11/11' })

    expect(within(day('Mié 11/11')).getByText('10:00–10:30 Perez, Juan')).toBeInTheDocument()
    expect(screen.getAllByText('10:00–10:30 Perez, Juan')).toHaveLength(1)
  })
})

describe('navegación entre fechas', () => {
  it('Siguiente en la semana va a la semana del lunes 16/11', async () => {
    installAgendaApi(world())
    open('/agenda?vista=semana&fecha=2026-11-09')
    await screen.findByRole('region', { name: 'Lun 09/11' })

    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))

    expect(await screen.findByRole('region', { name: 'Lun 16/11' })).toBeInTheDocument()
    expect(location()).toContain('fecha=2026-11-16')
  })

  it('Anterior y Siguiente en el día mueven un día', async () => {
    installAgendaApi(world())
    open('/agenda?fecha=2026-11-09')
    await screen.findByRole('region', { name: 'Lun 09/11' })

    fireEvent.click(screen.getByRole('button', { name: 'Anterior' }))
    expect(await screen.findByRole('region', { name: 'Dom 08/11' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByRole('region', { name: 'Mar 10/11' })).toBeInTheDocument()
  })

  it('Hoy usa la fecha del consultorio y no la del navegador', async () => {
    // 01:00 UTC del martes 10/11 son las 22:00 del lunes 09/11 en el consultorio
    vi.setSystemTime(new Date('2026-11-10T01:00:00Z'))
    installAgendaApi(world())
    open('/agenda?fecha=2026-11-20')
    await screen.findByRole('region', { name: 'Vie 20/11' })

    fireEvent.click(screen.getByRole('button', { name: 'Hoy' }))

    expect(await screen.findByRole('region', { name: 'Lun 09/11' })).toBeInTheDocument()
  })

  it('una fecha inválida en la dirección muestra el día de hoy sin error', async () => {
    installAgendaApi(world())
    open('/agenda?fecha=2026-02-30&vista=mes')

    expect(await screen.findByRole('region', { name: 'Lun 09/11' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    await waitFor(() => {
      expect(location()).toContain('fecha=2026-11-09')
    })
    expect(location()).toContain('vista=dia')
  })

  it('recargar mantiene profesional, fecha y vista', async () => {
    installAgendaApi(world())
    const first = open('/agenda?profesional=p-2&vista=semana&fecha=2026-11-16')
    await screen.findByRole('region', { name: 'Lun 16/11' })
    const search = location() ?? ''
    first.unmount()

    open(search)

    expect(await screen.findByRole('region', { name: 'Lun 16/11' })).toBeInTheDocument()
    expect(screen.getByLabelText('Profesional')).toHaveValue('p-2')
    expect(screen.getByRole('button', { name: 'Semana' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('cambiar de vista conserva la fecha y solo se hacen pedidos GET', async () => {
    const api = installAgendaApi(world())
    open('/agenda?fecha=2026-11-12')
    await screen.findByRole('region', { name: 'Jue 12/11' })

    fireEvent.click(screen.getByRole('button', { name: 'Semana' }))

    expect(await screen.findByRole('region', { name: 'Lun 09/11' })).toBeInTheDocument()
    expect(location()).toContain('fecha=2026-11-12')
    expect(api.calls.every((c) => c.startsWith('GET '))).toBe(true)
  })

  it('una respuesta vieja que llega tarde no pisa a la fecha nueva', async () => {
    let releaseSlow: (() => void) | undefined
    const slowGate = new Promise<void>((resolve) => {
      releaseSlow = resolve
    })
    const data = world()
    data.override = (_method, path) =>
      path.startsWith('/professionals/p-1/slots?date=2026-11-09')
        ? slowGate.then(() => new Response('[]', { status: 200 }))
        : undefined
    installAgendaApi(data)
    open('/agenda?fecha=2026-11-09')

    fireEvent.click(await screen.findByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByRole('region', { name: 'Mar 10/11' })).toBeInTheDocument()
    releaseSlow?.()
    await new Promise((resolve) => setTimeout(resolve, 20))

    expect(screen.getByRole('region', { name: 'Mar 10/11' })).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Lun 09/11' })).not.toBeInTheDocument()
  })
})
