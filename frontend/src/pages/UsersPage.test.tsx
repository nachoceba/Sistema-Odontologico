import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ManagedUser } from '../api/users'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi, renderApp } from '../test-utils'

const ADMIN_ME = {
  id: 'u-admin',
  email: 'admin@example.com',
  full_name: 'Admin Demo',
  role: 'admin',
  professional_id: null,
}

const ACCOUNTS: ManagedUser[] = [
  { id: 'u-admin', email: 'admin@example.com', full_name: 'Admin Demo', role: 'admin', active: true, professional_id: null },
  { id: 'u-dra', email: 'dra@example.com', full_name: 'Dra Demo', role: 'dentist', active: true, professional_id: 'p-dra' },
  { id: 'u-rec', email: 'recepcion@example.com', full_name: 'Rec Demo', role: 'receptionist', active: true, professional_id: null },
  { id: 'u-baja', email: 'baja@example.com', full_name: 'Baja Demo', role: 'receptionist', active: false, professional_id: null },
]

const REC = ACCOUNTS[2] as ManagedUser

function apiError(code: string, status: number): Response {
  return jsonResponse({ error: { code, message: 'x' } }, status)
}

function setup(extra: Record<string, () => Promise<Response> | Response> = {}) {
  saveToken('tok-admin')
  return mockApi({
    'GET /auth/me': () => jsonResponse(ADMIN_ME),
    'GET /users': () => jsonResponse(ACCOUNTS),
    ...extra,
  })
}

function bodyOf(fetchMock: ReturnType<typeof vi.fn>, suffix: string, method: string): unknown {
  const call = fetchMock.mock.calls.find(
    (c) => String(c[0]).endsWith(suffix) && ((c[1] as RequestInit | undefined)?.method ?? 'GET') === method,
  )
  return call === undefined ? undefined : JSON.parse((call[1] as RequestInit).body as string)
}

function callsTo(fetchMock: ReturnType<typeof vi.fn>, suffix: string, method: string): number {
  return fetchMock.mock.calls.filter(
    (c) => String(c[0]).endsWith(suffix) && ((c[1] as RequestInit | undefined)?.method ?? 'GET') === method,
  ).length
}

function rowOf(name: string): HTMLElement {
  return screen.getByRole('row', { name: new RegExp(name) })
}

function createForm(): HTMLElement {
  return screen.getByRole('form', { name: 'Alta de usuario' })
}

function fill(form: HTMLElement, label: string, value: string) {
  fireEvent.change(within(form).getByLabelText(label), { target: { value } })
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  window.sessionStorage.clear()
  window.localStorage.clear()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('listado de usuarios', () => {
  it('muestra "Cargando…" mientras el listado no llega', async () => {
    setup({ 'GET /users': () => new Promise<Response>(() => undefined) })
    renderApp('/usuarios')
    await screen.findByRole('heading', { name: 'Usuarios' })
    expect(screen.getByText('Cargando…')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('muestra las cuatro cuentas en el orden recibido y la inactiva como "Inactivo"', async () => {
    setup()
    renderApp('/usuarios')

    await screen.findByText('Rec Demo')

    const rows = screen.getAllByRole('row').slice(1)
    expect(rows).toHaveLength(4)
    expect(within(rowOf('Admin Demo')).getByText('Administrador')).toBeInTheDocument()
    expect(within(rowOf('Dra Demo')).getByText('Odontólogo/a')).toBeInTheDocument()
    expect(within(rowOf('Rec Demo')).getByText('Recepción')).toBeInTheDocument()
    expect(within(rowOf('Rec Demo')).getByText('Activo')).toBeInTheDocument()
    expect(within(rowOf('Baja Demo')).getByText('Inactivo')).toBeInTheDocument()
    expect(within(rowOf('Baja Demo')).getByRole('button', { name: 'Reactivar' })).toBeInTheDocument()
  })

  it('un error de red muestra "No se pudo conectar con el servidor"', async () => {
    setup({ 'GET /users': () => Promise.reject(new TypeError('Failed to fetch')) })
    renderApp('/usuarios')

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('un 500 muestra "No se pudo conectar con el servidor"', async () => {
    setup({ 'GET /users': () => apiError('INTERNAL_ERROR', 500) })
    renderApp('/usuarios')

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })
})

describe('alta de usuarios', () => {
  it('crea una odontóloga con los campos de la ficha y la muestra en la tabla', async () => {
    const created: ManagedUser = {
      id: 'u-nueva',
      email: 'nueva@example.com',
      full_name: 'Nueva Odonto',
      role: 'dentist',
      active: true,
      professional_id: 'p-nueva',
    }
    const fetchMock = setup({ 'POST /users': () => jsonResponse(created, 201) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')
    const form = createForm()

    fill(form, 'Email', 'nueva@example.com')
    fill(form, 'Nombre completo', 'Nueva Odonto')
    fill(form, 'Rol', 'dentist')
    fill(form, 'Nombre a mostrar', 'Dra. Nueva')
    fill(form, 'Matrícula', 'MN-0001')
    fill(form, 'Contraseña inicial', 'clave-inicial-12')
    fireEvent.click(within(form).getByRole('button', { name: 'Crear' }))

    expect(await screen.findByText('Nueva Odonto')).toBeInTheDocument()
    expect(bodyOf(fetchMock, '/users', 'POST')).toEqual({
      email: 'nueva@example.com',
      full_name: 'Nueva Odonto',
      role: 'dentist',
      password: 'clave-inicial-12',
      display_name: 'Dra. Nueva',
      license_number: 'MN-0001',
    })
    expect(within(createForm()).getByLabelText('Email')).toHaveValue('')
    expect(within(createForm()).getByLabelText('Contraseña inicial')).toHaveValue('')
  })

  it('no envía los campos de ficha vacíos', async () => {
    const fetchMock = setup({ 'POST /users': () => jsonResponse({ ...REC, id: 'u-x', full_name: 'Equis' }, 201) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')
    const form = createForm()

    fill(form, 'Email', 'x@example.com')
    fill(form, 'Nombre completo', 'Equis')
    fill(form, 'Rol', 'dentist')
    fill(form, 'Contraseña inicial', 'clave-inicial-12')
    fireEvent.click(within(form).getByRole('button', { name: 'Crear' }))

    await waitFor(() => {
      expect(callsTo(fetchMock, '/users', 'POST')).toBe(1)
    })
    expect(bodyOf(fetchMock, '/users', 'POST')).toEqual({
      email: 'x@example.com',
      full_name: 'Equis',
      role: 'dentist',
      password: 'clave-inicial-12',
    })
  })

  it('oculta "Nombre a mostrar" y "Matrícula" para el rol Recepción', async () => {
    setup()
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')
    const form = createForm()

    expect(within(form).queryByLabelText('Nombre a mostrar')).not.toBeInTheDocument()
    expect(within(form).queryByLabelText('Matrícula')).not.toBeInTheDocument()

    fill(form, 'Rol', 'dentist')
    expect(within(form).getByLabelText('Nombre a mostrar')).toBeInTheDocument()
    expect(within(form).getByLabelText('Matrícula')).toBeInTheDocument()

    fill(form, 'Rol', 'receptionist')
    expect(within(form).queryByLabelText('Matrícula')).not.toBeInTheDocument()
  })

  it('un 409 EMAIL_TAKEN muestra el mensaje, conserva email y nombre y vacía la contraseña', async () => {
    setup({ 'POST /users': () => apiError('EMAIL_TAKEN', 409) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')
    const form = createForm()

    fill(form, 'Email', 'recepcion@example.com')
    fill(form, 'Nombre completo', 'Otra Persona')
    fill(form, 'Contraseña inicial', 'clave-inicial-12')
    fireEvent.click(within(form).getByRole('button', { name: 'Crear' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Ya existe un usuario con ese email')
    expect(within(form).getByLabelText('Email')).toHaveValue('recepcion@example.com')
    expect(within(form).getByLabelText('Nombre completo')).toHaveValue('Otra Persona')
    expect(within(form).getByLabelText('Contraseña inicial')).toHaveValue('')
  })

  it('un 422 muestra "Revisá los datos: hay campos inválidos"', async () => {
    setup({ 'POST /users': () => jsonResponse({ detail: [] }, 422) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')
    const form = createForm()

    fill(form, 'Email', 'x@example.com')
    fill(form, 'Nombre completo', 'Equis')
    fill(form, 'Contraseña inicial', 'clave-inicial-12')
    fireEvent.click(within(form).getByRole('button', { name: 'Crear' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Revisá los datos: hay campos inválidos',
    )
  })

  it('un doble clic en "Crear" envía una sola solicitud y deshabilita el botón', async () => {
    let release: (response: Response) => void = () => undefined
    const pending = new Promise<Response>((resolve) => {
      release = resolve
    })
    const fetchMock = setup({ 'POST /users': () => pending })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')
    const form = createForm()
    fill(form, 'Email', 'x@example.com')
    fill(form, 'Nombre completo', 'Equis')
    fill(form, 'Contraseña inicial', 'clave-inicial-12')
    const button = within(form).getByRole('button', { name: 'Crear' })

    fireEvent.click(button)
    fireEvent.click(button)
    fireEvent.submit(form)

    expect(button).toBeDisabled()
    expect(callsTo(fetchMock, '/users', 'POST')).toBe(1)
    release(apiError('EMAIL_TAKEN', 409))
    await waitFor(() => {
      expect(button).toBeEnabled()
    })
  })

  it('la contraseña no queda en sessionStorage ni en localStorage', async () => {
    setup({ 'POST /users': () => jsonResponse({ ...REC, id: 'u-x', full_name: 'Equis' }, 201) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')
    const form = createForm()
    fill(form, 'Email', 'x@example.com')
    fill(form, 'Nombre completo', 'Equis')
    fill(form, 'Contraseña inicial', 'clave-secreta-ficticia')
    fireEvent.click(within(form).getByRole('button', { name: 'Crear' }))

    await screen.findByText('Equis')

    expect(JSON.stringify({ ...window.sessionStorage })).not.toContain('clave-secreta-ficticia')
    expect(JSON.stringify({ ...window.localStorage })).not.toContain('clave-secreta-ficticia')
  })
})

describe('desactivar y reactivar', () => {
  it('desactiva con confirmación y la fila pasa a "Inactivo" con "Reactivar"', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = setup({
      'POST /users/u-rec/deactivate': () => jsonResponse({ ...REC, active: false }),
    })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Desactivar' }))

    await waitFor(() => {
      expect(within(rowOf('Rec Demo')).getByText('Inactivo')).toBeInTheDocument()
    })
    expect(within(rowOf('Rec Demo')).getByRole('button', { name: 'Reactivar' })).toBeInTheDocument()
    expect(confirm).toHaveBeenCalledTimes(1)
    expect(callsTo(fetchMock, '/users/u-rec/deactivate', 'POST')).toBe(1)
  })

  it('al cancelar la confirmación no envía nada y la fila no cambia', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const fetchMock = setup()
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Desactivar' }))

    expect(callsTo(fetchMock, '/users/u-rec/deactivate', 'POST')).toBe(0)
    expect(within(rowOf('Rec Demo')).getByText('Activo')).toBeInTheDocument()
  })

  it('al desactivar un odontólogo la confirmación avisa que sus turnos futuros no se cancelan', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    setup()
    renderApp('/usuarios')
    await screen.findByText('Dra Demo')

    fireEvent.click(within(rowOf('Dra Demo')).getByRole('button', { name: 'Desactivar' }))

    expect(String(confirm.mock.calls[0]?.[0])).toContain('Sus turnos futuros no se cancelan')
  })

  it('la confirmación de una cuenta que no es de odontólogo no menciona turnos', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    setup()
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Desactivar' }))

    expect(String(confirm.mock.calls[0]?.[0])).not.toContain('turnos')
  })

  it('la propia fila no ofrece "Desactivar"', async () => {
    setup()
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    expect(
      within(rowOf('Admin Demo')).queryByRole('button', { name: 'Desactivar' }),
    ).not.toBeInTheDocument()
    expect(within(rowOf('Admin Demo')).getByRole('button', { name: 'Editar' })).toBeInTheDocument()
  })

  it('reactiva una cuenta inactiva', async () => {
    const baja = ACCOUNTS[3] as ManagedUser
    const fetchMock = setup({
      'POST /users/u-baja/reactivate': () => jsonResponse({ ...baja, active: true }),
    })
    renderApp('/usuarios')
    await screen.findByText('Baja Demo')

    fireEvent.click(within(rowOf('Baja Demo')).getByRole('button', { name: 'Reactivar' }))

    await waitFor(() => {
      expect(within(rowOf('Baja Demo')).getByText('Activo')).toBeInTheDocument()
    })
    expect(callsTo(fetchMock, '/users/u-baja/reactivate', 'POST')).toBe(1)
  })

  it('un rechazo SELF_MODIFICATION_NOT_ALLOWED muestra su mensaje y la fila no cambia', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    setup({ 'POST /users/u-rec/deactivate': () => apiError('SELF_MODIFICATION_NOT_ALLOWED', 409) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Desactivar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No podés desactivar ni cambiar el rol de tu propia cuenta',
    )
    expect(within(rowOf('Rec Demo')).getByText('Activo')).toBeInTheDocument()
  })

  it('USER_NOT_FOUND muestra "El usuario ya no existe" y vuelve a cargar la tabla', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = setup({ 'POST /users/u-rec/deactivate': () => apiError('USER_NOT_FOUND', 404) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Desactivar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('El usuario ya no existe')
    await waitFor(() => {
      expect(callsTo(fetchMock, '/users', 'GET')).toBe(2)
    })
  })
})

describe('edición', () => {
  function editForm(): HTMLElement {
    return screen.getByRole('form', { name: 'Editar usuario' })
  }

  it('guarda nombre y email y actualiza la fila (envía solo lo que cambió)', async () => {
    const fetchMock = setup({
      'PATCH /users/u-rec': () =>
        jsonResponse({ ...REC, full_name: 'Rec Corregida', email: 'nueva@example.com' }),
    })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Editar' }))
    fill(editForm(), 'Nombre completo', 'Rec Corregida')
    fill(editForm(), 'Email', 'nueva@example.com')
    fireEvent.click(within(editForm()).getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Rec Corregida')).toBeInTheDocument()
    expect(bodyOf(fetchMock, '/users/u-rec', 'PATCH')).toEqual({
      full_name: 'Rec Corregida',
      email: 'nueva@example.com',
    })
    expect(screen.queryByRole('form', { name: 'Editar usuario' })).not.toBeInTheDocument()
  })

  it('para un odontólogo el selector de rol solo ofrece "Odontólogo/a"', async () => {
    setup()
    renderApp('/usuarios')
    await screen.findByText('Dra Demo')

    fireEvent.click(within(rowOf('Dra Demo')).getByRole('button', { name: 'Editar' }))

    const options = within(within(editForm()).getByLabelText('Rol')).getAllByRole('option')
    expect(options.map((o) => o.textContent)).toEqual(['Odontólogo/a'])
  })

  it('para una recepcionista el selector ofrece los tres roles', async () => {
    setup()
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Editar' }))

    const options = within(within(editForm()).getByLabelText('Rol')).getAllByRole('option')
    expect(options.map((o) => o.textContent)).toEqual(['Administrador', 'Recepción', 'Odontólogo/a'])
  })

  it('en la propia cuenta el rol no se puede cambiar', async () => {
    setup()
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Admin Demo')).getByRole('button', { name: 'Editar' }))

    expect(within(editForm()).getByLabelText('Rol')).toBeDisabled()
  })

  it('un 409 EMAIL_TAKEN al guardar muestra el mensaje y la fila conserva sus datos', async () => {
    setup({ 'PATCH /users/u-rec': () => apiError('EMAIL_TAKEN', 409) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Editar' }))
    fill(editForm(), 'Email', 'dra@example.com')
    fireEvent.click(within(editForm()).getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Ya existe un usuario con ese email')
    expect(within(rowOf('Rec Demo')).getByText('recepcion@example.com')).toBeInTheDocument()
  })

  it('ROLE_CHANGE_NOT_ALLOWED muestra "No se puede cambiar el rol de un odontólogo"', async () => {
    setup({ 'PATCH /users/u-rec': () => apiError('ROLE_CHANGE_NOT_ALLOWED', 409) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Editar' }))
    fill(editForm(), 'Rol', 'dentist')
    fireEvent.click(within(editForm()).getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se puede cambiar el rol de un odontólogo',
    )
  })

  it('USER_NOT_FOUND al guardar avisa y recarga la tabla', async () => {
    const fetchMock = setup({ 'PATCH /users/u-rec': () => apiError('USER_NOT_FOUND', 404) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Editar' }))
    fill(editForm(), 'Nombre completo', 'Otro')
    fireEvent.click(within(editForm()).getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('El usuario ya no existe')
    await waitFor(() => {
      expect(callsTo(fetchMock, '/users', 'GET')).toBe(2)
    })
  })

  it('cancelar cierra el formulario sin enviar nada', async () => {
    const fetchMock = setup()
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Editar' }))
    fireEvent.click(within(editForm()).getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByRole('form', { name: 'Editar usuario' })).not.toBeInTheDocument()
    expect(callsTo(fetchMock, '/users/u-rec', 'PATCH')).toBe(0)
  })
})

describe('asignar contraseña', () => {
  it('envía la contraseña nueva, muestra "Contraseña actualizada" y vacía el campo', async () => {
    const fetchMock = setup({
      'PUT /users/u-rec/password': () => new Response(null, { status: 204 }),
    })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Asignar contraseña' }))
    const form = screen.getByRole('form', { name: 'Asignar contraseña' })
    fireEvent.change(within(form).getByLabelText('Contraseña nueva'), {
      target: { value: 'clave-nueva-10' },
    })
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar contraseña' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Contraseña actualizada')
    expect(within(form).getByLabelText('Contraseña nueva')).toHaveValue('')
    expect(bodyOf(fetchMock, '/users/u-rec/password', 'PUT')).toEqual({ password: 'clave-nueva-10' })
    expect(JSON.stringify({ ...window.sessionStorage })).not.toContain('clave-nueva-10')
    expect(JSON.stringify({ ...window.localStorage })).not.toContain('clave-nueva-10')
  })

  it('un 422 muestra el mensaje de datos inválidos y vacía el campo', async () => {
    setup({ 'PUT /users/u-rec/password': () => jsonResponse({ detail: [] }, 422) })
    renderApp('/usuarios')
    await screen.findByText('Rec Demo')

    fireEvent.click(within(rowOf('Rec Demo')).getByRole('button', { name: 'Asignar contraseña' }))
    const form = screen.getByRole('form', { name: 'Asignar contraseña' })
    fireEvent.change(within(form).getByLabelText('Contraseña nueva'), { target: { value: 'corta' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar contraseña' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Revisá los datos: hay campos inválidos',
    )
    expect(within(form).getByLabelText('Contraseña nueva')).toHaveValue('')
  })
})
