import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import {
  BASE,
  CONSULTA_PUB,
  DRA_A,
  LIMPIEZA_PUB,
  LUCIA,
  REGISTERED,
  SLOT_1030,
  SLOT_1100,
  SLOTS_URL,
  TREATMENTS_URL,
  fillForm,
  jsonResponse,
  mockApi,
  pickSlot,
  pickTreatment,
  renderBooking,
  useFixedClock,
} from './harness'

const PROFESSIONALS = { 'GET /public/professionals': () => jsonResponse([DRA_A]) }
const error = (status: number, code: string) =>
  jsonResponse({ error: { code, message: 'x' } }, status)

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  useFixedClock()
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('PublicBookingPage: profesional, día y franja', () => {
  it('muestra "Cargando…" y después los profesionales como botones', async () => {
    mockApi(PROFESSIONALS)

    renderBooking()

    expect(screen.getByRole('status')).toHaveTextContent('Cargando…')
    expect(await screen.findByRole('button', { name: 'Dra. A' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Reservar un turno' })).toBeInTheDocument()
  })

  it('un error al listar profesionales muestra un aviso y deja reintentar', async () => {
    let calls = 0
    mockApi({
      'GET /public/professionals': () => {
        calls += 1
        return calls === 1 ? error(500, 'INTERNAL_ERROR') : jsonResponse([DRA_A])
      },
    })

    renderBooking()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos cargar los profesionales',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('button', { name: 'Dra. A' })).toBeInTheDocument()
  })

  it('sin profesionales ofrecidos lo dice', async () => {
    mockApi({ 'GET /public/professionals': () => jsonResponse([]) })

    renderBooking()

    expect(await screen.findByText(/no hay profesionales disponibles/i)).toBeInTheDocument()
  })

  it('ofrece hoy y los 13 días siguientes y pide las franjas de hoy', async () => {
    const fetchMock = mockApi({
      ...PROFESSIONALS,
      [SLOTS_URL]: () => jsonResponse([SLOT_1030, SLOT_1100]),
    })
    renderBooking()

    await pickTreatment()

    expect(await screen.findByRole('button', { name: '10:30' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '11:00' })).toBeInTheDocument()
    const days = within(screen.getByLabelText('Día')).getAllByRole('option')
    expect(days).toHaveLength(14)
    expect(days[0]).toHaveTextContent('Lun 09/11')
    expect(days[13]).toHaveTextContent('Dom 22/11')
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/public/professionals/p-1/slots?date=2026-11-09`,
      expect.anything(),
    )
  })

  it('cambiar el día pide las franjas de ese día', async () => {
    mockApi({
      ...PROFESSIONALS,
      [SLOTS_URL]: () => jsonResponse([SLOT_1030]),
      'GET /public/professionals/p-1/slots?date=2026-11-10': () =>
        jsonResponse([{ starts_at: '2026-11-10T12:00:00Z', ends_at: '2026-11-10T12:30:00Z' }]),
    })
    renderBooking()
    await pickTreatment()
    await screen.findByRole('button', { name: '10:30' })

    fireEvent.change(screen.getByLabelText('Día'), { target: { value: '2026-11-10' } })

    expect(await screen.findByRole('button', { name: '09:00' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '10:30' })).not.toBeInTheDocument()
  })

  it('un día sin franjas dice que pruebe con otro', async () => {
    mockApi({ ...PROFESSIONALS, [SLOTS_URL]: () => jsonResponse([]) })
    renderBooking()

    await pickTreatment()

    expect(
      await screen.findByText('No hay horarios libres para este día. Pruebe con otro.'),
    ).toBeInTheDocument()
  })

  it('un error al pedir franjas muestra un aviso con la opción de reintentar', async () => {
    let calls = 0
    mockApi({
      ...PROFESSIONALS,
      [SLOTS_URL]: () => {
        calls += 1
        return calls === 1 ? error(500, 'INTERNAL_ERROR') : jsonResponse([SLOT_1030])
      },
    })
    renderBooking()

    await pickTreatment()

    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar los horarios')
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('button', { name: '10:30' })).toBeInTheDocument()
  })

  it('ningún pedido lleva Authorization aunque la recepción tenga sesión', async () => {
    saveToken('tok-rec')
    const fetchMock = mockApi({ ...PROFESSIONALS, [SLOTS_URL]: () => jsonResponse([SLOT_1030]) })
    renderBooking()

    await pickSlot()

    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    for (const call of fetchMock.mock.calls) {
      const init = call[1] as RequestInit | undefined
      expect(new Headers(init?.headers).has('Authorization')).toBe(false)
    }
  })
})

describe('PublicBookingPage: datos del paciente y envío', () => {
  function world(post: () => Response | Promise<Response>) {
    return mockApi({
      ...PROFESSIONALS,
      [SLOTS_URL]: () => jsonResponse([SLOT_1030, SLOT_1100]),
      'POST /public/appointments': post,
    })
  }

  function postsOf(fetchMock: ReturnType<typeof mockApi>) {
    return fetchMock.mock.calls.filter(
      (call) => (call[1] as RequestInit | undefined)?.method === 'POST',
    )
  }

  it('pide siempre DNI, nombre, apellido, email y teléfono opcional, sin consultar el DNI', async () => {
    const fetchMock = world(() => jsonResponse(REGISTERED, 202))
    renderBooking()
    await pickSlot()
    const before = fetchMock.mock.calls.length

    fillForm(LUCIA)

    expect(screen.getByLabelText('DNI')).toBeRequired()
    expect(screen.getByLabelText('Nombre')).toBeRequired()
    expect(screen.getByLabelText('Apellido')).toBeRequired()
    expect(screen.getByLabelText('Email')).toBeRequired()
    expect(screen.getByLabelText('Teléfono (opcional)')).not.toBeRequired()
    expect(fetchMock.mock.calls.length).toBe(before)
    expect(
      screen.getByText('Turno elegido: Dra. A, Limpieza dental, lunes 09/11/2026, 10:30'),
    ).toBeInTheDocument()
  })

  it('el campo trampa está oculto para personas y lectores y fuera del orden de Tab', async () => {
    world(() => jsonResponse(REGISTERED, 202))
    renderBooking()
    await pickSlot()

    const trap = document.querySelector<HTMLInputElement>('input[name="website"]')

    expect(trap).not.toBeNull()
    expect(trap?.tabIndex).toBe(-1)
    expect(trap?.closest('[aria-hidden="true"]')).not.toBeNull()
    expect(trap?.value).toBe('')
    const focusable = Array.from(
      document.querySelectorAll<HTMLElement>('input, button, select'),
    ).filter((element) => element.tabIndex >= 0)
    expect(focusable).not.toContain(trap)
  })

  it('envía los datos en el formato de la API con el campo trampa vacío', async () => {
    const fetchMock = world(() => jsonResponse(REGISTERED, 202))
    renderBooking()
    await pickSlot()
    fillForm(LUCIA)

    fireEvent.click(screen.getByRole('button', { name: 'Reservar turno' }))

    await screen.findByRole('heading', { name: 'Turno registrado exitosamente' })
    const [url, init] = postsOf(fetchMock)[0] as [string, RequestInit]
    expect(url).toBe(`${BASE}/public/appointments`)
    expect(JSON.parse(init.body as string)).toEqual({
      professional_id: 'p-1',
      treatment_id: 't-2',
      starts_at: SLOT_1030.starts_at,
      document_number: '40999888',
      first_name: 'Lucía',
      last_name: 'Díaz',
      email: 'lucia@example.com',
      phone: '11 5555-1234',
      website: '',
    })
  })

  it('BOOKING_NOT_POSSIBLE muestra el aviso genérico y conserva los datos escritos', async () => {
    world(() => error(409, 'BOOKING_NOT_POSSIBLE'))
    renderBooking()
    await pickSlot()
    fillForm(LUCIA)

    fireEvent.click(screen.getByRole('button', { name: 'Reservar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Verifique sus datos ingresados.')
    expect(screen.getByLabelText('DNI')).toHaveValue('40999888')
    expect(screen.getByLabelText('Apellido')).toHaveValue('Díaz')
    expect(screen.getByRole('button', { name: 'Reservar turno' })).toBeEnabled()
  })

  it.each(['SLOT_TAKEN', 'SLOT_UNAVAILABLE'])(
    '%s avisa que el horario ya no está disponible y recarga las franjas',
    async (code) => {
      let slotCalls = 0
      mockApi({
        ...PROFESSIONALS,
        [SLOTS_URL]: () => {
          slotCalls += 1
          return jsonResponse(slotCalls === 1 ? [SLOT_1030, SLOT_1100] : [SLOT_1100])
        },
        'POST /public/appointments': () => error(409, code),
      })
      renderBooking()
      await pickSlot()
      fillForm(LUCIA)

      fireEvent.click(screen.getByRole('button', { name: 'Reservar turno' }))

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Ese horario ya no está disponible. Elija otro.',
      )
      expect(await screen.findByRole('button', { name: '11:00' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: '10:30' })).not.toBeInTheDocument()
    },
  )

  it('después de un horario ocupado el paciente conserva sus datos al elegir otra franja', async () => {
    mockApi({
      ...PROFESSIONALS,
      [SLOTS_URL]: () => jsonResponse([SLOT_1100]),
      'POST /public/appointments': () => error(409, 'SLOT_TAKEN'),
    })
    renderBooking()
    await pickTreatment()
    fireEvent.click(await screen.findByRole('button', { name: '11:00' }))
    await screen.findByLabelText('DNI')
    fillForm(LUCIA)
    fireEvent.click(screen.getByRole('button', { name: 'Reservar turno' }))
    await screen.findByRole('alert')

    fireEvent.click(await screen.findByRole('button', { name: '11:00' }))

    expect(await screen.findByLabelText('DNI')).toHaveValue('40999888')
  })

  it('un 429 muestra el aviso de demasiados intentos', async () => {
    world(() => error(429, 'TOO_MANY_REQUESTS'))
    renderBooking()
    await pickSlot()
    fillForm(LUCIA)

    fireEvent.click(screen.getByRole('button', { name: 'Reservar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Hizo muchos intentos. Espere un rato y vuelva a probar.',
    )
  })

  it.each([500, 422, 400])(
    'un %i muestra el aviso general y no repite lo escrito',
    async (status) => {
      world(() => error(status, 'OTHER'))
      renderBooking()
      await pickSlot()
      fillForm(LUCIA)

      fireEvent.click(screen.getByRole('button', { name: 'Reservar turno' }))

      const alert = await screen.findByRole('alert')
      expect(alert).toHaveTextContent('No pudimos registrar el turno. Pruebe de nuevo más tarde.')
      expect(alert.textContent).not.toContain('40999888')
    },
  )

  it('un error de red también muestra el aviso general', async () => {
    world(() => Promise.reject(new TypeError('Failed to fetch')))
    renderBooking()
    await pickSlot()
    fillForm(LUCIA)

    fireEvent.click(screen.getByRole('button', { name: 'Reservar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos registrar el turno')
  })

  it('un doble clic en "Reservar turno" envía un solo pedido y deshabilita el botón', async () => {
    let release: (response: Response) => void = () => undefined
    const fetchMock = world(
      () =>
        new Promise<Response>((resolve) => {
          release = resolve
        }),
    )
    renderBooking()
    await pickSlot()
    fillForm(LUCIA)
    const button = screen.getByRole('button', { name: 'Reservar turno' })

    fireEvent.click(button)
    fireEvent.click(button)
    fireEvent.submit(button.closest('form') as HTMLFormElement)

    expect(postsOf(fetchMock)).toHaveLength(1)
    expect(button).toBeDisabled()
    release(jsonResponse(REGISTERED, 202))
    await screen.findByRole('heading', { name: 'Turno registrado exitosamente' })
    expect(postsOf(fetchMock)).toHaveLength(1)
  })
})

describe('PublicBookingPage: tratamiento (C-17)', () => {
  it('después del profesional muestra sus tratamientos y todavía no el día ni las franjas', async () => {
    const fetchMock = mockApi({ ...PROFESSIONALS, [SLOTS_URL]: () => jsonResponse([SLOT_1030]) })
    renderBooking()

    fireEvent.click(await screen.findByRole('button', { name: 'Dra. A' }))

    expect(await screen.findByRole('button', { name: 'Consulta' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Limpieza dental' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Día')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '10:30' })).not.toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining('/slots'),
      expect.anything(),
    )
  })

  it('al elegir el tratamiento aparecen el día y las franjas, y el turno elegido lo incluye', async () => {
    mockApi({ ...PROFESSIONALS, [SLOTS_URL]: () => jsonResponse([SLOT_1030]) })
    renderBooking()

    await pickSlot()

    expect(screen.getByRole('button', { name: 'Limpieza dental' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(
      screen.getByText('Turno elegido: Dra. A, Limpieza dental, lunes 09/11/2026, 10:30'),
    ).toBeInTheDocument()
  })

  it('cambiar de tratamiento conserva el día y borra la franja', async () => {
    mockApi({
      ...PROFESSIONALS,
      [SLOTS_URL]: () => jsonResponse([SLOT_1030]),
      'GET /public/professionals/p-1/slots?date=2026-11-10': () =>
        jsonResponse([{ starts_at: '2026-11-10T12:00:00Z', ends_at: '2026-11-10T12:30:00Z' }]),
    })
    renderBooking()
    await pickTreatment()
    fireEvent.change(await screen.findByLabelText('Día'), { target: { value: '2026-11-10' } })
    fireEvent.click(await screen.findByRole('button', { name: '09:00' }))
    await screen.findByLabelText('DNI')

    fireEvent.click(screen.getByRole('button', { name: 'Consulta' }))

    expect(screen.getByLabelText('Día')).toHaveValue('2026-11-10')
    expect(screen.queryByLabelText('DNI')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '09:00' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('cambiar de profesional borra el tratamiento y la franja y pide los tratamientos del nuevo', async () => {
    const DR_B = { id: 'p-2', display_name: 'Dr. B' }
    mockApi({
      'GET /public/professionals': () => jsonResponse([DRA_A, DR_B]),
      [SLOTS_URL]: () => jsonResponse([SLOT_1030]),
      'GET /public/professionals/p-2/treatments': () => jsonResponse([CONSULTA_PUB]),
    })
    renderBooking()
    await pickSlot()

    fireEvent.click(screen.getByRole('button', { name: 'Dr. B' }))

    expect(await screen.findByRole('button', { name: 'Consulta' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(screen.queryByRole('button', { name: 'Limpieza dental' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Día')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('DNI')).not.toBeInTheDocument()
  })

  it('muestra la carga de los tratamientos y, si fallan, un aviso con reintento', async () => {
    let calls = 0
    mockApi({
      ...PROFESSIONALS,
      [TREATMENTS_URL]: () => {
        calls += 1
        return calls === 1 ? error(500, 'INTERNAL_ERROR') : jsonResponse([CONSULTA_PUB])
      },
    })
    renderBooking()
    fireEvent.click(await screen.findByRole('button', { name: 'Dra. A' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos cargar los tratamientos',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByRole('button', { name: 'Consulta' })).toBeInTheDocument()
  })

  it('TREATMENT_NOT_AVAILABLE avisa, vuelve a pedir la lista, borra el tratamiento y conserva los datos', async () => {
    let calls = 0
    mockApi({
      ...PROFESSIONALS,
      [SLOTS_URL]: () => jsonResponse([SLOT_1030]),
      [TREATMENTS_URL]: () => {
        calls += 1
        return jsonResponse(calls === 1 ? [CONSULTA_PUB, LIMPIEZA_PUB] : [CONSULTA_PUB])
      },
      'POST /public/appointments': () => error(409, 'TREATMENT_NOT_AVAILABLE'),
    })
    renderBooking()
    await pickSlot()
    fillForm(LUCIA)

    fireEvent.click(screen.getByRole('button', { name: 'Reservar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El tratamiento elegido ya no está disponible. Elija otro.',
    )
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Limpieza dental' })).not.toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: 'Consulta' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    // Elegir otro tratamiento y la franja devuelve el formulario con los datos escritos.
    fireEvent.click(screen.getByRole('button', { name: 'Consulta' }))
    fireEvent.click(await screen.findByRole('button', { name: '10:30' }))
    expect(await screen.findByLabelText('DNI')).toHaveValue('40999888')
    expect(screen.getByLabelText('Apellido')).toHaveValue('Díaz')
  })
})
