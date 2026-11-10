import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { at } from '../agenda/fixtures'
import type { Treatment } from '../api/treatments'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import { BookingPanel } from './BookingPanel'

const SLOT = { startsAt: at(10), endsAt: at(10, 30) }
const LUCIA = {
  id: 'pac-3',
  first_name: 'Lucía',
  last_name: 'Torres',
  document_number: '30111999',
  email: 'lucia@example.com',
  phone: null,
  birth_date: null,
  active: true,
}
const JUAN = { ...LUCIA, id: 'pac-1', first_name: 'Juan', last_name: 'Perez' }
const LAURA = { ...LUCIA, id: 'pac-9', first_name: 'Laura', last_name: 'Ruiz' }
const RECORD = {
  id: 'a-new',
  patient_id: 'pac-1',
  professional_id: 'p-1',
  starts_at: SLOT.startsAt,
  ends_at: SLOT.endsAt,
  status: 'scheduled',
  cancel_reason: null,
  created_by: 'u-rec',
  origin: 'staff',
  pending_until: null,
  treatment_id: 't-limpieza',
}
const CONSULTA: Treatment = { id: 't-consulta', name: 'Consulta', active: true }
const LIMPIEZA: Treatment = { id: 't-limpieza', name: 'Limpieza dental', active: true }
const BLANQUEAMIENTO: Treatment = { id: 't-blanq', name: 'Blanqueamiento', active: false }
const TREATMENTS_PATH = 'GET /professionals/p-1/treatments'
const TREATMENTS_API = {
  [TREATMENTS_PATH]: () => jsonResponse([CONSULTA, LIMPIEZA, BLANQUEAMIENTO]),
}
const ACCENT =
  'La búsqueda distingue tildes: si el apellido lleva tilde, escribilo con tilde (por ejemplo, Pérez)'

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  saveToken('tok')
})

afterEach(() => {
  clearToken()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

function setup() {
  const handlers = { onBooked: vi.fn(), onRejected: vi.fn(), onClose: vi.fn() }
  render(
    <BookingPanel
      slot={SLOT}
      professionalId="p-1"
      professionalName="Dra. Ana Álvarez"
      {...handlers}
    />,
  )
  return handlers
}

const found = (items: unknown[]) => () => jsonResponse({ items, truncated: false })

async function pickTreatment(name = 'Limpieza dental') {
  const select = await screen.findByLabelText('Tratamiento')
  const option = await screen.findByRole('option', { name })
  fireEvent.change(select, { target: { value: (option as HTMLOptionElement).value } })
}

async function choose(query: string, name: string) {
  fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar paciente' }), {
    target: { value: query },
  })
  fireEvent.click(await screen.findByRole('button', { name }))
}

function fillLaura() {
  fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Laura' } })
  fireEvent.change(screen.getByLabelText('Apellido'), { target: { value: 'Ruiz' } })
  fireEvent.change(screen.getByLabelText('Documento'), { target: { value: '30999888' } })
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'laura@example.com' } })
}

describe('BookingPanel: elegir paciente', () => {
  it('muestra la franja, el profesional y Agendar turno deshabilitado sin paciente', () => {
    const fetchMock = mockApi({ ...TREATMENTS_API })
    setup()

    expect(screen.getByRole('heading', { name: 'Lun 09/11 10:00–10:30' })).toBeInTheDocument()
    expect(screen.getByText('Dra. Ana Álvarez')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeDisabled()
    expect(screen.getByText(ACCENT)).toBeInTheDocument()
    const writes = fetchMock.mock.calls.filter(
      (c) => ((c[1] as RequestInit | undefined)?.method ?? 'GET') !== 'GET',
    )
    expect(writes).toEqual([])
  })

  it('elegir a Lucía Torres la muestra con Cambiar y habilita Agendar turno', async () => {
    mockApi({ ...TREATMENTS_API, 'GET /patients?q=torres': found([LUCIA]) })
    setup()

    await choose('torres', 'Torres, Lucía')

    expect(screen.getByText('Paciente: Torres, Lucía')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeDisabled()
    await pickTreatment()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar' }))
    expect(screen.getByRole('searchbox', { name: 'Buscar paciente' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeDisabled()
  })

  it('buscar sin tilde: sin resultados y el aviso de tildes sigue visible', async () => {
    mockApi({ ...TREATMENTS_API, 'GET /patients?q=perez': found([]) })
    setup()

    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar paciente' }), {
      target: { value: 'perez' },
    })

    expect(await screen.findByText('No se encontraron pacientes')).toBeInTheDocument()
    expect(screen.getByText(ACCENT)).toBeInTheDocument()
  })

  it('un paciente inactivo no aparece: la búsqueda no pide inactivos', async () => {
    const fetchMock = mockApi({ ...TREATMENTS_API, 'GET /patients?q=gomez': found([]) })
    setup()

    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar paciente' }), {
      target: { value: 'gomez' },
    })

    expect(await screen.findByText('No se encontraron pacientes')).toBeInTheDocument()
    const urls = (fetchMock.mock.calls as [string][]).map((c) => c[0])
    expect(urls.some((url) => url.includes('include_inactive'))).toBe(false)
  })

  it('Cerrar no envía pedidos de escritura', async () => {
    const fetchMock = mockApi({ ...TREATMENTS_API, 'GET /patients?q=torres': found([LUCIA]) })
    const handlers = setup()
    await choose('torres', 'Torres, Lucía')

    fireEvent.click(screen.getByRole('button', { name: 'Cerrar' }))

    expect(handlers.onClose).toHaveBeenCalledTimes(1)
    const writes = fetchMock.mock.calls.filter(
      (c) => ((c[1] as RequestInit | undefined)?.method ?? 'GET') !== 'GET',
    )
    expect(writes).toEqual([])
  })
})

describe('BookingPanel: crear paciente', () => {
  it('Nuevo paciente con alta correcta deja a Ruiz, Laura elegida', async () => {
    const fetchMock = mockApi({ ...TREATMENTS_API, 'POST /patients': () => jsonResponse(LAURA, 201) })
    setup()

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo paciente' }))
    fillLaura()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Paciente: Ruiz, Laura')).toBeInTheDocument()
    await pickTreatment()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeEnabled()
    const posts = fetchMock.mock.calls.filter(
      (c) => (c[1] as RequestInit | undefined)?.method === 'POST',
    )
    expect(posts).toHaveLength(1)
  })

  it('DOCUMENT_TAKEN deja el formulario con los datos y ningún paciente elegido', async () => {
    mockApi({ ...TREATMENTS_API,
      'POST /patients': () =>
        jsonResponse({ error: { code: 'DOCUMENT_TAKEN', message: 'x' } }, 409),
    })
    setup()

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo paciente' }))
    fillLaura()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Ya existe un paciente con ese documento')).toBeInTheDocument()
    expect(screen.getByLabelText('Apellido')).toHaveValue('Ruiz')
    expect(screen.queryByText(/^Paciente: /)).not.toBeInTheDocument()
  })

  it('Cancelar en el formulario vuelve a la búsqueda', () => {
    mockApi({ ...TREATMENTS_API })
    setup()

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo paciente' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.getByRole('searchbox', { name: 'Buscar paciente' })).toBeInTheDocument()
  })
})

describe('BookingPanel: agendar', () => {
  it('envía un solo POST con el inicio de la franja y avisa con nombre y franja', async () => {
    const fetchMock = mockApi({ ...TREATMENTS_API,
      'GET /patients?q=perez': found([JUAN]),
      'POST /appointments': () => jsonResponse(RECORD, 201),
    })
    const handlers = setup()
    await choose('perez', 'Perez, Juan')
    await pickTreatment()

    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))

    await waitFor(() => {
      expect(handlers.onBooked).toHaveBeenCalledWith(
        'Perez, Juan',
        SLOT.startsAt,
        'Limpieza dental',
      )
    })
    const post = fetchMock.mock.calls.find(
      (c) => (c[1] as RequestInit | undefined)?.method === 'POST',
    )
    expect(JSON.parse((post?.[1] as RequestInit).body as string)).toEqual({
      patient_id: 'pac-1',
      professional_id: 'p-1',
      treatment_id: 't-limpieza',
      starts_at: SLOT.startsAt,
    })
  })

  it.each([
    ['SLOT_TAKEN', 409, 'Ese horario se acaba de ocupar. Elegí otro horario'],
    [
      'INSUFFICIENT_NOTICE',
      400,
      'Ese horario ya pasó o no respeta la anticipación mínima del consultorio',
    ],
    ['PATIENT_DOUBLE_BOOKED', 409, 'El paciente ya tiene otro turno en ese horario'],
  ])('%s: mensaje, panel abierto, paciente conservado y recarga', async (code, status, text) => {
    mockApi({ ...TREATMENTS_API,
      'GET /patients?q=perez': found([JUAN]),
      'POST /appointments': () => jsonResponse({ error: { code, message: 'x' } }, status),
    })
    const handlers = setup()
    await choose('perez', 'Perez, Juan')
    await pickTreatment()

    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(text)
    expect(screen.getByText('Paciente: Perez, Juan')).toBeInTheDocument()
    expect(handlers.onRejected).toHaveBeenCalledTimes(1)
    expect(handlers.onBooked).not.toHaveBeenCalled()
  })

  it('red caída: aviso de conexión, panel abierto y se puede reintentar', async () => {
    let down = true
    mockApi({ ...TREATMENTS_API,
      'GET /patients?q=perez': found([JUAN]),
      'POST /appointments': () => {
        if (down) throw new TypeError('network')
        return jsonResponse(RECORD, 201)
      },
    })
    const handlers = setup()
    await choose('perez', 'Perez, Juan')
    await pickTreatment()

    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
    expect(handlers.onRejected).not.toHaveBeenCalled()

    down = false
    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))
    await waitFor(() => {
      expect(handlers.onBooked).toHaveBeenCalledTimes(1)
    })
  })

  it('paciente creado y turno rechazado: Laura Ruiz sigue elegida', async () => {
    mockApi({ ...TREATMENTS_API,
      'POST /patients': () => jsonResponse(LAURA, 201),
      'POST /appointments': () =>
        jsonResponse({ error: { code: 'SLOT_TAKEN', message: 'x' } }, 409),
    })
    setup()
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo paciente' }))
    fillLaura()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await screen.findByText('Paciente: Ruiz, Laura')
    await pickTreatment()

    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Ese horario se acaba de ocupar')
    expect(screen.getByText('Paciente: Ruiz, Laura')).toBeInTheDocument()
  })

  it('un doble clic envía un solo POST /appointments', async () => {
    const fetchMock = mockApi({ ...TREATMENTS_API,
      'GET /patients?q=perez': found([JUAN]),
      'POST /appointments': () => jsonResponse(RECORD, 201),
    })
    const handlers = setup()
    await choose('perez', 'Perez, Juan')
    await pickTreatment()

    const button = screen.getByRole('button', { name: 'Agendar turno' })
    fireEvent.click(button)
    fireEvent.click(button)

    await waitFor(() => {
      expect(handlers.onBooked).toHaveBeenCalledTimes(1)
    })
    const posts = fetchMock.mock.calls.filter(
      (c) => (c[1] as RequestInit | undefined)?.method === 'POST',
    )
    expect(posts).toHaveLength(1)
  })
})

describe('BookingPanel: tratamiento (C-17)', () => {
  it('ofrece solo los activos del profesional, ordenados, y arranca sin elección', async () => {
    mockApi({ ...TREATMENTS_API })
    setup()

    const select = await screen.findByLabelText('Tratamiento')
    await screen.findByRole('option', { name: 'Consulta' })

    const options = screen.getAllByRole('option').map((o) => o.textContent)
    expect(options).toEqual(['Elegí el tratamiento', 'Consulta', 'Limpieza dental'])
    expect(select).toHaveValue('')
  })

  it('con paciente pero sin tratamiento no se puede agendar ni se envía nada', async () => {
    const fetchMock = mockApi({ ...TREATMENTS_API, 'GET /patients?q=perez': found([JUAN]) })
    setup()
    await choose('perez', 'Perez, Juan')
    await screen.findByRole('option', { name: 'Consulta' })

    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeDisabled()
    const posts = fetchMock.mock.calls.filter(
      (c) => (c[1] as RequestInit | undefined)?.method === 'POST',
    )
    expect(posts).toEqual([])
  })

  it('con tratamiento pero sin paciente tampoco se puede agendar', async () => {
    mockApi({ ...TREATMENTS_API })
    setup()

    await pickTreatment('Consulta')

    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeDisabled()
  })

  it('un profesional sin tratamientos activos muestra el aviso y no deja agendar', async () => {
    mockApi({
      [TREATMENTS_PATH]: () => jsonResponse([BLANQUEAMIENTO]),
      'GET /patients?q=perez': found([JUAN]),
    })
    setup()
    await choose('perez', 'Perez, Juan')

    expect(
      await screen.findByText(
        'Este profesional no tiene tratamientos activos. Pedile al administrador que se los asigne.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText('Tratamiento')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeDisabled()
  })

  it('muestra la carga y, si falla el pedido, un error con reintento', async () => {
    let fail = true
    mockApi({
      [TREATMENTS_PATH]: () => (fail ? jsonResponse({}, 500) : jsonResponse([CONSULTA])),
    })
    setup()

    expect(screen.getByRole('status')).toHaveTextContent('Cargando')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudieron cargar los tratamientos',
    )
    fail = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByRole('option', { name: 'Consulta' })).toBeInTheDocument()
  })

  it('TREATMENT_NOT_AVAILABLE avisa, vuelve a pedir la lista y conserva al paciente', async () => {
    let calls = 0
    const fetchMock = mockApi({
      [TREATMENTS_PATH]: () => {
        calls += 1
        return jsonResponse(calls === 1 ? [CONSULTA, LIMPIEZA] : [CONSULTA])
      },
      'GET /patients?q=perez': found([JUAN]),
      'POST /appointments': () =>
        jsonResponse({ error: { code: 'TREATMENT_NOT_AVAILABLE', message: 'x' } }, 409),
    })
    setup()
    await choose('perez', 'Perez, Juan')
    await pickTreatment()

    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ese tratamiento ya no está disponible para este profesional. Elegí otro.',
    )
    await waitFor(() => {
      expect(screen.queryByRole('option', { name: 'Limpieza dental' })).not.toBeInTheDocument()
    })
    expect(screen.getByText('Paciente: Perez, Juan')).toBeInTheDocument()
    expect(screen.getByLabelText('Tratamiento')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeDisabled()
    const gets = fetchMock.mock.calls.filter((c) => String(c[0]).endsWith('/treatments'))
    expect(gets).toHaveLength(2)
  })
})
