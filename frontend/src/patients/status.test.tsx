import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi, renderApp } from '../test-utils'

const ADMIN = {
  id: 'u-admin',
  email: 'admin@example.com',
  full_name: 'Admin Demo',
  role: 'admin',
  professional_id: null,
}
const RECEPTIONIST = { ...ADMIN, id: 'u-rec', full_name: 'Rec Demo', role: 'receptionist' }
const JUAN = {
  id: 'pac-1',
  first_name: 'Juan',
  last_name: 'Pérez',
  document_number: '30111222',
  email: 'juan@example.com',
  phone: '011-5550-0001',
  birth_date: null,
  active: true,
}
const ANA = { ...JUAN, id: 'pac-2', first_name: 'Ana', last_name: 'Gómez', active: false }
const TURN = {
  id: 'a-1',
  professional_id: 'p-1',
  starts_at: '2026-11-05T13:00:00Z', // jueves 05/11 10:00 en Buenos Aires
  ends_at: '2026-11-05T13:30:00Z',
  status: 'scheduled',
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  window.sessionStorage.clear()
  saveToken('tok')
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

function rowOf(name: string): HTMLElement {
  return screen.getByText(name).closest('tr') as HTMLElement
}

function writes(fetchMock: ReturnType<typeof vi.fn>): string[] {
  return (fetchMock.mock.calls as [string, RequestInit][])
    .filter((call) => ['POST', 'DELETE', 'PATCH'].includes(call[1]?.method ?? 'GET'))
    .map((call) => `${call[1].method ?? ''} ${call[0].replace(BASE, '')}`)
}

describe('desactivar, reactivar y borrar pacientes', () => {
  it('desactivar pide confirmación, deja a Juan Inactivo y avisa sus turnos en hora local', async () => {
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
      'POST /patients/pac-1/deactivate': () =>
        jsonResponse({ patient: { ...JUAN, active: false }, upcoming_appointments: [TURN] }),
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')

    fireEvent.click(within(rowOf('Pérez, Juan')).getByRole('button', { name: 'Desactivar' }))
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent('¿Desactivar a Juan Pérez? Sus turnos no se cancelan.')
    expect(writes(fetchMock)).toEqual([])
    fireEvent.click(within(dialog).getByRole('button', { name: 'Desactivar' }))

    expect(await screen.findByText('jue 05/11 10:00')).toBeInTheDocument()
    expect(
      screen.getByRole('status', { name: 'Turnos del paciente desactivado' }),
    ).toHaveTextContent(
      'Este paciente tiene 1 turno agendado. Para reprogramarlo, reactivalo primero; si no, cancelalo desde la agenda',
    )
    expect(rowOf('Pérez, Juan')).toHaveTextContent('Inactivo')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(writes(fetchMock)).toEqual(['POST /patients/pac-1/deactivate'])
  })

  it('con varios turnos usa el plural del aviso del diseño', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
      'POST /patients/pac-1/deactivate': () =>
        jsonResponse({
          patient: { ...JUAN, active: false },
          upcoming_appointments: [TURN, { ...TURN, id: 'a-2', starts_at: '2026-11-06T13:00:00Z' }],
        }),
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')

    fireEvent.click(within(rowOf('Pérez, Juan')).getByRole('button', { name: 'Desactivar' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Desactivar' }))

    expect(
      await screen.findByText(
        'Este paciente tiene 2 turnos agendados. Para reprogramarlos, reactivalo primero; si no, cancelalos desde la agenda',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('vie 06/11 10:00')).toBeInTheDocument()
  })

  it('sin turnos futuros no muestra el aviso', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
      'POST /patients/pac-1/deactivate': () =>
        jsonResponse({ patient: { ...JUAN, active: false }, upcoming_appointments: [] }),
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')

    fireEvent.click(within(rowOf('Pérez, Juan')).getByRole('button', { name: 'Desactivar' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Desactivar' }))

    await waitFor(() => {
      expect(rowOf('Pérez, Juan')).toHaveTextContent('Inactivo')
    })
    expect(screen.queryByText(/Este paciente tiene/)).not.toBeInTheDocument()
  })

  it('cancelar la confirmación no llama a la API y Juan sigue Activo', async () => {
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')

    fireEvent.click(within(rowOf('Pérez, Juan')).getByRole('button', { name: 'Desactivar' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(rowOf('Pérez, Juan')).toHaveTextContent('Activo')
    expect(writes(fetchMock)).toEqual([])
  })

  it('Escape también cierra la confirmación sin llamar a la API', async () => {
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')

    fireEvent.click(within(rowOf('Pérez, Juan')).getByRole('button', { name: 'Desactivar' }))
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(writes(fetchMock)).toEqual([])
  })

  it('reactivar actúa sin confirmación y deja a Ana Activa', async () => {
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [ANA], truncated: false }),
      'POST /patients/pac-2/reactivate': () => jsonResponse({ ...ANA, active: true }),
    })
    renderApp('/pacientes')
    await screen.findByText('Gómez, Ana')

    fireEvent.click(within(rowOf('Gómez, Ana')).getByRole('button', { name: 'Reactivar' }))

    await waitFor(() => {
      expect(rowOf('Gómez, Ana')).toHaveTextContent('Activo')
    })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(writes(fetchMock)).toEqual(['POST /patients/pac-2/reactivate'])
  })

  it('el administrador borra con confirmación y la fila desaparece', async () => {
    let listed = [JUAN, ANA]
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(ADMIN),
      'GET /patients': () => jsonResponse({ items: listed, truncated: false }),
      'DELETE /patients/pac-2': () => {
        listed = [JUAN]
        return new Response(null, { status: 204 })
      },
    })
    renderApp('/pacientes')
    await screen.findByText('Gómez, Ana')

    fireEvent.click(within(rowOf('Gómez, Ana')).getByRole('button', { name: 'Borrar' }))
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent('¿Borrar a Ana Gómez? Esta acción no se puede deshacer.')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Borrar' }))

    await waitFor(() => {
      expect(screen.queryByText('Gómez, Ana')).not.toBeInTheDocument()
    })
    expect(screen.getByText('Pérez, Juan')).toBeInTheDocument()
    expect(writes(fetchMock)).toEqual(['DELETE /patients/pac-2'])
  })

  it('borrar con turnos muestra el aviso del 409 y Juan sigue en la tabla', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(ADMIN),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
      'DELETE /patients/pac-1': () =>
        jsonResponse({ error: { code: 'PATIENT_HAS_APPOINTMENTS', message: 'x' } }, 409),
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')

    fireEvent.click(within(rowOf('Pérez, Juan')).getByRole('button', { name: 'Borrar' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Borrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se puede borrar: tiene turnos. Desactivalo en su lugar',
    )
    expect(screen.getByText('Pérez, Juan')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('si el paciente ya no existe avisa y vuelve a pedir la lista', async () => {
    let listed = [JUAN]
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: listed, truncated: false }),
      'POST /patients/pac-1/deactivate': () => {
        listed = []
        return jsonResponse({ error: { code: 'PATIENT_NOT_FOUND', message: 'x' } }, 404)
      },
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')

    fireEvent.click(within(rowOf('Pérez, Juan')).getByRole('button', { name: 'Desactivar' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Desactivar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('El paciente ya no existe')
    await waitFor(() => {
      expect(screen.queryByText('Pérez, Juan')).not.toBeInTheDocument()
    })
  })

  it('el foco queda dentro de la confirmación: Tab y Shift+Tab dan la vuelta (P-11)', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')
    fireEvent.click(within(rowOf('Pérez, Juan')).getByRole('button', { name: 'Desactivar' }))
    const dialog = within(screen.getByRole('dialog'))
    const first = dialog.getByRole('button', { name: 'Desactivar' })
    const last = dialog.getByRole('button', { name: 'Cancelar' })

    last.focus()
    fireEvent.keyDown(last, { key: 'Tab' })
    expect(document.activeElement).toBe(first)

    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(last)
  })

  it('al cancelar la confirmación el foco vuelve al botón que la abrió', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
    })
    renderApp('/pacientes')
    await screen.findByText('Pérez, Juan')
    const opener = within(rowOf('Pérez, Juan')).getByRole('button', { name: 'Desactivar' })
    opener.focus()
    fireEvent.click(opener)

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(document.activeElement).toBe(opener)
  })
})
