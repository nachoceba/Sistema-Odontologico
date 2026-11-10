import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { clearToken, readToken, saveToken } from '../auth/session'
import { BASE, DENTIST, jsonResponse } from '../test-utils'
import { at, turno } from './fixtures'
import { DR_B, DRA, installAgendaApi, type AgendaWorld } from './testApi'

const ADMIN = {
  id: 'u-admin',
  email: 'admin@example.com',
  full_name: 'Admin Demo',
  role: 'admin',
  professional_id: null,
}
const RECEPTIONIST = { ...ADMIN, id: 'u-rec', full_name: 'Rec Demo', role: 'receptionist' }
const DENTIST_NO_FILE = { ...DENTIST, id: 'u-2', professional_id: null }
const INACTIVE = { id: 'p-0', display_name: 'Dr. Zeta Baja', license_number: null, active: false }

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

describe('acceso y profesional mostrado', () => {
  it('recepción elige al Dr. B y la dirección cambia', async () => {
    const api = installAgendaApi(
      world({
        appointments: [
          turno(10, 0, 10, 30, { professional_id: 'p-2', patient_last_name: 'Rossi' }),
        ],
      }),
    )
    open('/agenda')
    await screen.findByLabelText('Profesional')
    expect((await screen.findAllByText('Libre')).length).toBeGreaterThan(0)

    fireEvent.change(screen.getByLabelText('Profesional'), { target: { value: 'p-2' } })

    expect(await screen.findByText('10:00–10:30 Rossi, Juan')).toBeInTheDocument()
    expect(location()).toContain('profesional=p-2')
    expect(api.calls.some((c) => c.startsWith('GET /professionals/p-2/slots'))).toBe(true)
  })

  it('por defecto muestra al primer profesional activo y marca al inactivo', async () => {
    const api = installAgendaApi(world({ me: ADMIN, professionals: [INACTIVE, DRA, DR_B] }))
    open('/agenda')

    await screen.findAllByText('Libre')

    const picker = screen.getByLabelText('Profesional')
    expect(
      within(picker).getByRole('option', { name: 'Dr. Zeta Baja (inactivo)' }),
    ).toBeInTheDocument()
    expect(picker).toHaveValue('p-1')
    expect(api.calls.some((c) => c.startsWith('GET /professionals/p-1/slots'))).toBe(true)
    expect(api.calls.some((c) => c.includes('/professionals/p-0/'))).toBe(false)
  })

  it('un profesional inactivo se ve con su aviso y sus turnos', async () => {
    installAgendaApi(
      world({
        professionals: [INACTIVE, DRA],
        appointments: [
          turno(10, 0, 10, 30, { professional_id: 'p-0', patient_last_name: 'Gomez' }),
        ],
      }),
    )
    open('/agenda?profesional=p-0')

    expect(
      await screen.findByText('Profesional inactivo: no se le pueden dar turnos nuevos'),
    ).toBeInTheDocument()
    expect(await screen.findByText('10:00–10:30 Gomez, Juan')).toBeInTheDocument()
  })

  it('la odontóloga ve solo su agenda, sin selector y sin pedir otros profesionales', async () => {
    const api = installAgendaApi(world({ me: DENTIST, professionals: [DRA] }))
    open('/agenda')

    await screen.findAllByText('Libre')

    expect(screen.queryByLabelText('Profesional')).not.toBeInTheDocument()
    expect(screen.getByText('Dra. Ana Álvarez')).toBeInTheDocument()
    expect(api.calls.some((c) => c.includes('p-2'))).toBe(false)
  })

  it('la odontóloga con la dirección de otro profesional ve la suya y no se pide la ajena', async () => {
    const api = installAgendaApi(world({ me: DENTIST, professionals: [DRA] }))
    open('/agenda?profesional=p-2')

    await screen.findAllByText('Libre')

    expect(api.calls.some((c) => c.includes('p-2'))).toBe(false)
    expect(api.calls.some((c) => c.startsWith('GET /professionals/p-1/slots'))).toBe(true)
  })

  it('un odontólogo sin ficha ve el aviso y no se piden turnos ni franjas', async () => {
    const api = installAgendaApi(world({ me: DENTIST_NO_FILE, professionals: [] }))
    open('/agenda')

    expect(
      await screen.findByText('No tenés una ficha de profesional asociada'),
    ).toBeInTheDocument()
    expect(api.calls.filter((c) => c.includes('/slots') || c.includes('/appointments'))).toEqual(
      [],
    )
  })

  it('sin profesionales cargados lo dice y no pide turnos', async () => {
    const api = installAgendaApi(world({ professionals: [] }))
    open('/agenda')

    expect(await screen.findByText('Todavía no hay profesionales cargados')).toBeInTheDocument()
    expect(api.calls.some((c) => c.includes('/slots'))).toBe(false)
  })

  it('sin sesión lleva a /login', async () => {
    clearToken()
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse({ status: 'ok' }))),
    )
    open('/agenda')

    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeInTheDocument()
  })
})

describe('carga y errores', () => {
  it('muestra Cargando… mientras espera', async () => {
    installAgendaApi(world())
    open('/agenda')

    expect(screen.getByText('Cargando…')).toBeInTheDocument()
    await screen.findAllByText('Libre')
    expect(screen.queryByText('Cargando…')).not.toBeInTheDocument()
  })

  it('red caída: aviso y Reintentar vuelve a pedir las franjas', async () => {
    let down = true
    installAgendaApi(
      world({
        override: (_method, path) => (down && path.includes('/slots') ? Response.error() : undefined),
      }),
    )
    open('/agenda')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudo conectar con el servidor',
    )
    down = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect((await screen.findAllByText('Libre')).length).toBeGreaterThan(0)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('403 al pedir los turnos: aviso de permiso y la sesión sigue abierta', async () => {
    installAgendaApi(
      world({
        override: (_method, path) =>
          path.startsWith('/appointments')
            ? jsonResponse({ error: { code: 'FORBIDDEN', message: 'x' } }, 403)
            : undefined,
      }),
    )
    open('/agenda')

    expect(await screen.findByRole('alert')).toHaveTextContent('No tenés permiso para esta acción')
    expect(readToken()).toBe('tok')
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument()
  })
})

describe('barra de navegación y pedidos de la agenda', () => {
  it('recepción ve Pacientes, Profesionales y Salir pero no Usuarios', async () => {
    installAgendaApi(world())
    open('/agenda')

    expect(await screen.findByText('Hola, Rec Demo')).toBeInTheDocument()
    expect(screen.getByText('Recepción')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Pacientes' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Profesionales' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Salir' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument()
  })

  it('el administrador ve además Usuarios', async () => {
    installAgendaApi(world({ me: ADMIN }))
    open('/agenda')

    expect(await screen.findByRole('link', { name: 'Usuarios' })).toBeInTheDocument()
  })

  it('mirar no escribe: recorrer la semana y abrir dos detalles solo hace GET', async () => {
    const api = installAgendaApi(
      world({
        appointments: [turno(10, 0, 10, 30), turno(11, 0, 11, 30, { status: 'cancelled' })],
      }),
    )
    open('/agenda?vista=semana&fecha=2026-11-09')

    fireEvent.click(await screen.findByRole('button', { name: /10:00–10:30 Perez, Juan/ }))
    await screen.findByRole('complementary')
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar' }))
    fireEvent.click(screen.getByRole('button', { name: /11:00–11:30 Perez, Juan/ }))
    await screen.findByRole('complementary')
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    await waitFor(() => {
      expect(api.calls.filter((c) => c.startsWith('GET /appointments?')).length).toBeGreaterThan(1)
    })

    expect(api.calls.every((c) => c.startsWith('GET '))).toBe(true)
  })

  it('después de agendar la agenda se vuelve a pedir sin apretar Actualizar', async () => {
    const api = installAgendaApi(world({ patients: [{ id: 'pac-1', first_name: 'Juan', last_name: 'Perez' }] }))
    open('/agenda?fecha=2026-11-10')
    await screen.findAllByText('Libre')
    const before = api.calls.filter((c) => c.startsWith('GET /appointments?')).length

    fireEvent.click(screen.getAllByRole('button', { name: 'Agendar' })[0] as HTMLElement)
    fireEvent.change(await screen.findByRole('searchbox', { name: 'Buscar paciente' }), {
      target: { value: 'perez' },
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Perez, Juan' }))
    const select = await screen.findByLabelText('Tratamiento')
    await screen.findByRole('option', { name: 'Consulta' })
    fireEvent.change(select, { target: { value: 't-consulta' } })
    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))

    expect(await screen.findByText('09:00–09:30 Perez, Juan')).toBeInTheDocument()
    expect(api.calls.filter((c) => c.startsWith('GET /appointments?')).length).toBeGreaterThan(
      before,
    )
    expect(api.posts.map((p) => p.path)).toEqual(['/appointments'])
  })

  it('la odontóloga solo envía como escritura dos POST de asistencia', async () => {
    vi.setSystemTime(new Date('2026-11-09T17:00:00Z')) // 14:00 en el consultorio
    const first = turno(10, 0, 10, 30)
    const second = turno(11, 0, 11, 30)
    const api = installAgendaApi(
      world({ me: DENTIST, professionals: [DRA], appointments: [first, second] }),
    )
    open('/agenda')

    for (const name of [/10:00–10:30 Perez, Juan/, /11:00–11:30 Perez, Juan/]) {
      fireEvent.click(await screen.findByRole('button', { name }))
      fireEvent.click(await screen.findByRole('button', { name: 'Ausente' }))
      fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Ausente' }))
      await screen.findByText('Asistencia registrada')
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      })
    }

    const writes = api.calls.filter((c) => !c.startsWith('GET '))
    expect(writes).toEqual([
      `POST /appointments/${first.id}/attendance`,
      `POST /appointments/${second.id}/attendance`,
    ])
  })

  it('nunca se envían PUT, PATCH ni DELETE al usar las acciones', async () => {
    const juan = turno(15, 0, 15, 30)
    const api = installAgendaApi(world({ appointments: [juan] }))
    open('/agenda')

    fireEvent.click(await screen.findByRole('button', { name: /15:00–15:30 Perez, Juan/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar' }))
    fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'Motivo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }))
    await screen.findByText('Turno cancelado')

    expect(api.calls.some((c) => /^(PUT|PATCH|DELETE) /.test(c))).toBe(false)
  })

  it('Actualizar trae un turno nuevo', async () => {
    const data = world()
    installAgendaApi(data)
    open('/agenda')
    await screen.findAllByText('Libre')
    expect(screen.queryByText('15:00–15:30 Perez, Juan')).not.toBeInTheDocument()

    data.appointments.push(turno(15, 0, 15, 30, { starts_at: at(15), ends_at: at(15, 30) }))
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))

    expect(await screen.findByText('15:00–15:30 Perez, Juan')).toBeInTheDocument()
    expect(screen.getAllByText('Ocupado')).toHaveLength(1)
  })
})
