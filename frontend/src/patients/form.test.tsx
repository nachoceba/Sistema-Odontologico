import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi, renderApp } from '../test-utils'

const RECEPTIONIST = {
  id: 'u-rec',
  email: 'recepcion@example.com',
  full_name: 'Rec Demo',
  role: 'receptionist',
  professional_id: null,
}
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
const LAURA = {
  id: 'pac-9',
  first_name: 'Laura',
  last_name: 'Ruiz',
  document_number: '40222333',
  email: 'laura@example.com',
  phone: null,
  birth_date: null,
  active: true,
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

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

function fillLaura() {
  fill('Nombre', 'Laura')
  fill('Apellido', 'Ruiz')
  fill('Documento', '40.222.333')
  fill('Email', 'laura@example.com')
}

async function openNewForm() {
  fireEvent.click(await screen.findByRole('button', { name: 'Nuevo paciente' }))
  return screen.getByRole('form', { name: 'Alta de paciente' })
}

function postCalls(fetchMock: ReturnType<typeof vi.fn>): [string, RequestInit][] {
  return (fetchMock.mock.calls as [string, RequestInit][]).filter(
    (call) => call[1]?.method === 'POST' || call[1]?.method === 'PATCH',
  )
}

describe('formulario de alta y edición de pacientes', () => {
  it('el alta envía POST y el paciente nuevo aparece en la tabla', async () => {
    let listed = [JUAN]
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: listed, truncated: false }),
      'POST /patients': () => {
        listed = [JUAN, LAURA]
        return jsonResponse(LAURA, 201)
      },
    })
    renderApp('/pacientes')
    await openNewForm()

    fillLaura()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Ruiz, Laura')).toBeInTheDocument()
    const [call] = postCalls(fetchMock)
    expect(JSON.parse(call?.[1].body as string)).toEqual({
      first_name: 'Laura',
      last_name: 'Ruiz',
      document_number: '40.222.333',
      email: 'laura@example.com',
    })
    expect(screen.queryByRole('form', { name: 'Alta de paciente' })).not.toBeInTheDocument()
  })

  it('DOCUMENT_TAKEN se muestra junto al documento y conserva lo escrito', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
      'POST /patients': () =>
        jsonResponse({ error: { code: 'DOCUMENT_TAKEN', message: 'Ya existe' } }, 409),
    })
    renderApp('/pacientes')
    const form = await openNewForm()

    fillLaura()
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar' }))

    const message = await within(form).findByText('Ya existe un paciente con ese documento')
    expect(message).toHaveAttribute('id', 'patient-document-error')
    expect(screen.getByLabelText('Documento')).toHaveAccessibleDescription(
      'Ya existe un paciente con ese documento',
    )
    expect(screen.getByLabelText('Documento')).toHaveValue('40.222.333')
    expect(screen.getByLabelText('Nombre')).toHaveValue('Laura')
    expect(screen.getByLabelText('Email')).toHaveValue('laura@example.com')
  })

  it('un obligatorio vacío muestra el error junto al campo y no llama a la API', async () => {
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
    })
    renderApp('/pacientes')
    await openNewForm()
    fill('Nombre', 'Laura')
    fill('Apellido', 'Ruiz')
    fill('Documento', '40222333')

    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(screen.getByLabelText('Email')).toHaveAccessibleDescription('Este dato es obligatorio')
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true')
    expect(postCalls(fetchMock)).toEqual([])
  })

  it('todos los obligatorios vacíos marcan cuatro errores', async () => {
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
    })
    renderApp('/pacientes')
    await openNewForm()

    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(screen.getAllByText('Este dato es obligatorio')).toHaveLength(4)
    expect(postCalls(fetchMock)).toEqual([])
  })

  it('al editar, vaciar el teléfono envía PATCH solo con phone = null', async () => {
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
      'PATCH /patients/pac-1': () => jsonResponse({ ...JUAN, phone: null }),
    })
    renderApp('/pacientes')
    const row = (await screen.findByText('Pérez, Juan')).closest('tr') as HTMLElement
    fireEvent.click(within(row).getByRole('button', { name: 'Editar' }))
    const form = screen.getByRole('form', { name: 'Editar paciente' })
    expect(screen.getByLabelText('Teléfono')).toHaveValue('011-5550-0001')

    fill('Teléfono', '')
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(postCalls(fetchMock)).toHaveLength(1)
    })
    const [call] = postCalls(fetchMock)
    expect(call?.[1].method).toBe('PATCH')
    expect(JSON.parse(call?.[1].body as string)).toEqual({ phone: null })
    await waitFor(() => {
      expect(screen.queryByRole('form', { name: 'Editar paciente' })).not.toBeInTheDocument()
    })
  })

  it('editar sin cambiar nada cierra el formulario sin llamar a la API', async () => {
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
    })
    renderApp('/pacientes')
    const row = (await screen.findByText('Pérez, Juan')).closest('tr') as HTMLElement
    fireEvent.click(within(row).getByRole('button', { name: 'Editar' }))

    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(screen.queryByRole('form', { name: 'Editar paciente' })).not.toBeInTheDocument()
    expect(postCalls(fetchMock)).toEqual([])
  })

  it('un 422 muestra "Revisá los datos ingresados"', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
      'POST /patients': () =>
        jsonResponse({ detail: [{ loc: ['body'], msg: 'x', type: 'y' }] }, 422),
    })
    renderApp('/pacientes')
    await openNewForm()
    fillLaura()

    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Revisá los datos ingresados')
  })

  it('INVALID_PATIENT_DATA muestra el aviso de la fecha de nacimiento', async () => {
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
      'POST /patients': () =>
        jsonResponse({ error: { code: 'INVALID_PATIENT_DATA', message: 'x' } }, 400),
    })
    renderApp('/pacientes')
    await openNewForm()
    fillLaura()
    fill('Fecha de nacimiento', '2999-01-01')

    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(
      await screen.findByText('La fecha de nacimiento no puede ser futura'),
    ).toBeInTheDocument()
  })

  it('cancelar cierra el formulario sin llamar a la API', async () => {
    const fetchMock = mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
    })
    renderApp('/pacientes')
    await openNewForm()
    fillLaura()

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByRole('form', { name: 'Alta de paciente' })).not.toBeInTheDocument()
    expect(postCalls(fetchMock)).toEqual([])
  })
})
