import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import ConfirmBookingPage from './ConfirmBookingPage'
import { BASE, Probe, jsonResponse, mockApi } from './harness'

const CONFIRMED = {
  starts_at: '2026-11-09T13:30:00Z',
  ends_at: '2026-11-09T14:00:00Z',
  professional_display_name: 'Dra. A',
  treatment_name: 'Limpieza dental',
}
const URL_POST = 'POST /public/appointment-confirmations'
const error = (status: number, code: string) =>
  jsonResponse({ error: { code, message: 'x' } }, status)

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ConfirmBookingPage />
      <Probe />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('ConfirmBookingPage', () => {
  it('al abrirse muestra el título y el botón y no hace ningún pedido', () => {
    const fetchMock = mockApi({})

    renderAt('/turnos/confirmar#token=abc')

    expect(screen.getByRole('heading', { name: 'Confirmar su turno' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirmar mi turno' })).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('al tocar el botón envía el token en el cuerpo, sin Authorization, y confirma', async () => {
    saveToken('tok-rec')
    const fetchMock = mockApi({ [URL_POST]: () => jsonResponse(CONFIRMED) })
    renderAt('/turnos/confirmar#token=abc')

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar mi turno' }))

    const title = await screen.findByRole('heading', { name: 'Turno confirmado' })
    await waitFor(() => {
      expect(title).toHaveFocus()
    })
    const main = screen.getByRole('main')
    expect(main).toHaveTextContent(
      'Su turno quedó confirmado. Le enviamos la confirmación por email.',
    )
    expect(main).toHaveTextContent('Dra. A')
    expect(main).toHaveTextContent('lunes 09/11/2026, 10:30')
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).not.toContain('abc')
    expect(JSON.parse(init.body as string)).toEqual({ token: 'abc' })
    expect(new Headers(init.headers).has('Authorization')).toBe(false)
    await waitFor(() => {
      expect(screen.getByTestId('location').textContent).toBe('/turnos/confirmar')
    })
  })

  it('muestra la fila Tratamiento cuando la API devuelve el nombre y la omite si es nulo', async () => {
    mockApi({ [URL_POST]: () => jsonResponse(CONFIRMED) })
    const first = renderAt('/turnos/confirmar#token=abc')
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar mi turno' }))
    await screen.findByRole('heading', { name: 'Turno confirmado' })
    expect(screen.getByRole('main')).toHaveTextContent('Tratamiento')
    expect(screen.getByRole('main')).toHaveTextContent('Limpieza dental')
    first.unmount()

    mockApi({ [URL_POST]: () => jsonResponse({ ...CONFIRMED, treatment_name: null }) })
    renderAt('/turnos/confirmar#token=abc')
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar mi turno' }))
    await screen.findByRole('heading', { name: 'Turno confirmado' })
    expect(screen.getByRole('main')).not.toHaveTextContent('Tratamiento')
  })

  it('un doble clic envía un solo pedido', () => {
    const fetchMock = mockApi({
      [URL_POST]: () => new Promise<Response>(() => undefined),
    })
    renderAt('/turnos/confirmar#token=abc')
    const button = screen.getByRole('button', { name: 'Confirmar mi turno' })

    fireEvent.click(button)
    fireEvent.click(button)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(button).toBeDisabled()
  })

  it('un 410 muestra "Enlace no válido" con el enlace a /turnos y borra el fragmento', async () => {
    mockApi({ [URL_POST]: () => error(410, 'CONFIRMATION_LINK_INVALID') })
    renderAt('/turnos/confirmar#token=abc')

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar mi turno' }))

    expect(await screen.findByRole('heading', { name: 'Enlace no válido' })).toBeInTheDocument()
    expect(
      screen.getByText(
        'El enlace no es válido, ya se usó o venció. Si todavía quiere el turno, vuelva a reservarlo.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Reservar un turno' })).toHaveAttribute(
      'href',
      '/turnos',
    )
    await waitFor(() => {
      expect(screen.getByTestId('location').textContent).toBe('/turnos/confirmar')
    })
  })

  it.each(['/turnos/confirmar', '/turnos/confirmar#', '/turnos/confirmar#otro=1'])(
    'sin token en la dirección (%s) muestra el aviso de enlace no válido y no pide nada',
    (path) => {
      const fetchMock = mockApi({})

      renderAt(path)

      expect(screen.getByRole('heading', { name: 'Enlace no válido' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Reservar un turno' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Confirmar mi turno' })).not.toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalled()
    },
  )

  it('un 429 muestra el aviso de demasiados intentos y deja volver a tocar el botón', async () => {
    mockApi({ [URL_POST]: () => error(429, 'TOO_MANY_REQUESTS') })
    renderAt('/turnos/confirmar#token=abc')

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar mi turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Hizo muchos intentos. Espere un rato y vuelva a probar.',
    )
    expect(screen.getByRole('button', { name: 'Confirmar mi turno' })).toBeEnabled()
  })

  it('un 500 muestra el aviso general y permite reintentar con el mismo token', async () => {
    let calls = 0
    const fetchMock = mockApi({
      [URL_POST]: () => {
        calls += 1
        return calls === 1 ? error(500, 'INTERNAL_ERROR') : jsonResponse(CONFIRMED)
      },
    })
    renderAt('/turnos/confirmar#token=abc')
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar mi turno' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos confirmar el turno. Pruebe de nuevo más tarde.',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar mi turno' }))

    expect(await screen.findByRole('heading', { name: 'Turno confirmado' })).toBeInTheDocument()
    const bodies = fetchMock.mock.calls.map((call) => (call[1] as RequestInit).body)
    expect(bodies).toEqual([JSON.stringify({ token: 'abc' }), JSON.stringify({ token: 'abc' })])
  })

  it('un error de red muestra el aviso general', async () => {
    mockApi({ [URL_POST]: () => Promise.reject(new TypeError('Failed to fetch')) })
    renderAt('/turnos/confirmar#token=abc')

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar mi turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos confirmar el turno')
  })
})
