import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { at } from '../agenda/fixtures'
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
    const fetchMock = mockApi({})
    setup()

    expect(screen.getByRole('heading', { name: 'Lun 09/11 10:00–10:30' })).toBeInTheDocument()
    expect(screen.getByText('Dra. Ana Álvarez')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeDisabled()
    expect(screen.getByText(ACCENT)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('elegir a Lucía Torres la muestra con Cambiar y habilita Agendar turno', async () => {
    mockApi({ 'GET /patients?q=torres': found([LUCIA]) })
    setup()

    await choose('torres', 'Torres, Lucía')

    expect(screen.getByText('Paciente: Torres, Lucía')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar' }))
    expect(screen.getByRole('searchbox', { name: 'Buscar paciente' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeDisabled()
  })

  it('buscar sin tilde: sin resultados y el aviso de tildes sigue visible', async () => {
    mockApi({ 'GET /patients?q=perez': found([]) })
    setup()

    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar paciente' }), {
      target: { value: 'perez' },
    })

    expect(await screen.findByText('No se encontraron pacientes')).toBeInTheDocument()
    expect(screen.getByText(ACCENT)).toBeInTheDocument()
  })

  it('un paciente inactivo no aparece: la búsqueda no pide inactivos', async () => {
    const fetchMock = mockApi({ 'GET /patients?q=gomez': found([]) })
    setup()

    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar paciente' }), {
      target: { value: 'gomez' },
    })

    expect(await screen.findByText('No se encontraron pacientes')).toBeInTheDocument()
    const urls = (fetchMock.mock.calls as [string][]).map((c) => c[0])
    expect(urls.some((url) => url.includes('include_inactive'))).toBe(false)
  })

  it('Cerrar no envía pedidos de escritura', async () => {
    const fetchMock = mockApi({ 'GET /patients?q=torres': found([LUCIA]) })
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
    const fetchMock = mockApi({ 'POST /patients': () => jsonResponse(LAURA, 201) })
    setup()

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo paciente' }))
    fillLaura()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Paciente: Ruiz, Laura')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agendar turno' })).toBeEnabled()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('DOCUMENT_TAKEN deja el formulario con los datos y ningún paciente elegido', async () => {
    mockApi({
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
    mockApi({})
    setup()

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo paciente' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.getByRole('searchbox', { name: 'Buscar paciente' })).toBeInTheDocument()
  })
})

describe('BookingPanel: agendar', () => {
  it('envía un solo POST con el inicio de la franja y avisa con nombre y franja', async () => {
    const fetchMock = mockApi({
      'GET /patients?q=perez': found([JUAN]),
      'POST /appointments': () => jsonResponse(RECORD, 201),
    })
    const handlers = setup()
    await choose('perez', 'Perez, Juan')

    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))

    await waitFor(() => {
      expect(handlers.onBooked).toHaveBeenCalledWith('Perez, Juan', SLOT.startsAt)
    })
    const post = fetchMock.mock.calls.find(
      (c) => (c[1] as RequestInit | undefined)?.method === 'POST',
    )
    expect(JSON.parse((post?.[1] as RequestInit).body as string)).toEqual({
      patient_id: 'pac-1',
      professional_id: 'p-1',
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
    mockApi({
      'GET /patients?q=perez': found([JUAN]),
      'POST /appointments': () => jsonResponse({ error: { code, message: 'x' } }, status),
    })
    const handlers = setup()
    await choose('perez', 'Perez, Juan')

    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(text)
    expect(screen.getByText('Paciente: Perez, Juan')).toBeInTheDocument()
    expect(handlers.onRejected).toHaveBeenCalledTimes(1)
    expect(handlers.onBooked).not.toHaveBeenCalled()
  })

  it('red caída: aviso de conexión, panel abierto y se puede reintentar', async () => {
    let down = true
    mockApi({
      'GET /patients?q=perez': found([JUAN]),
      'POST /appointments': () => {
        if (down) throw new TypeError('network')
        return jsonResponse(RECORD, 201)
      },
    })
    const handlers = setup()
    await choose('perez', 'Perez, Juan')

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
    mockApi({
      'POST /patients': () => jsonResponse(LAURA, 201),
      'POST /appointments': () =>
        jsonResponse({ error: { code: 'SLOT_TAKEN', message: 'x' } }, 409),
    })
    setup()
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo paciente' }))
    fillLaura()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await screen.findByText('Paciente: Ruiz, Laura')

    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Ese horario se acaba de ocupar')
    expect(screen.getByText('Paciente: Ruiz, Laura')).toBeInTheDocument()
  })

  it('un doble clic envía un solo POST /appointments', async () => {
    const fetchMock = mockApi({
      'GET /patients?q=perez': found([JUAN]),
      'POST /appointments': () => jsonResponse(RECORD, 201),
    })
    const handlers = setup()
    await choose('perez', 'Perez, Juan')

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
