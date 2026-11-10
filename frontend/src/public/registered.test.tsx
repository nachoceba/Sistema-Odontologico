import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken } from '../auth/session'
import {
  BASE,
  DRA_A,
  LUCIA,
  REGISTERED,
  SLOT_1030,
  SLOTS_URL,
  fillForm,
  jsonResponse,
  mockApi,
  pickSlot,
  renderBooking,
  useFixedClock,
  type Person,
} from './harness'

const NOTICE =
  'Está pendiente de confirmación. Revise su email: tiene que confirmarlo con el enlace que le enviamos antes de las 13:00.'
const RELEASE =
  'Si no lo confirma a tiempo, el horario se libera. Para cambiarlo o cancelarlo, comuníquese con el consultorio.'
const MARIA: Person = {
  document: '27123456',
  first: 'María',
  last: 'Gómez',
  email: 'maria.gomez@otro.example',
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  useFixedClock()
  mockApi({
    'GET /public/professionals': () => jsonResponse([DRA_A]),
    [SLOTS_URL]: () => jsonResponse([SLOT_1030]),
    'POST /public/appointments': () => jsonResponse(REGISTERED, 202),
  })
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

async function register(person: Person): Promise<HTMLElement> {
  await pickSlot()
  fillForm(person)
  fireEvent.click(screen.getByRole('button', { name: 'Reservar turno' }))
  await screen.findByRole('heading', { name: 'Turno registrado exitosamente' })
  return screen.getByRole('main')
}

describe('pantalla de turno registrado', () => {
  it('muestra el título, el plazo con la hora local, el profesional y el horario elegido', async () => {
    renderBooking()

    const main = await register(LUCIA)

    expect(
      screen.getByRole('heading', { name: 'Turno registrado exitosamente' }),
    ).toBeInTheDocument()
    expect(main).toHaveTextContent(NOTICE)
    expect(main).toHaveTextContent('Dra. A')
    expect(main).toHaveTextContent('lunes 09/11/2026, 10:30')
    expect(main).toHaveTextContent(RELEASE)
  })

  it('reemplaza el formulario', async () => {
    renderBooking()

    await register(LUCIA)

    expect(screen.queryByLabelText('DNI')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reservar turno' })).not.toBeInTheDocument()
  })

  it('no muestra el email, el nombre, el apellido ni el documento escritos', async () => {
    renderBooking()

    const main = await register(LUCIA)

    for (const secret of ['lucia@example.com', 'Lucía', 'Díaz', '40999888', '5555-1234']) {
      expect(main.textContent).not.toContain(secret)
    }
  })

  it('el foco queda en el título para que lo anuncie el lector de pantalla', async () => {
    renderBooking()

    await register(LUCIA)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Turno registrado exitosamente' })).toHaveFocus()
    })
  })

  it('el aviso es idéntico, texto por texto, para dos personas distintas', async () => {
    const first = renderBooking()
    const noticeA = (await register(LUCIA)).textContent
    first.unmount()
    renderBooking()

    const noticeB = (await register(MARIA)).textContent

    expect(noticeA).toBe(noticeB)
    expect(noticeB).toContain('Turno registrado exitosamente')
  })
})
