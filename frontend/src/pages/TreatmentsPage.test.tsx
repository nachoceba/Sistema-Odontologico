import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Treatment } from '../api/treatments'
import { clearToken, saveToken } from '../auth/session'
import { BASE, DENTIST, jsonResponse, mockApi, renderApp } from '../test-utils'

const ADMIN = {
  id: 'u-admin',
  email: 'admin@example.com',
  full_name: 'Admin Demo',
  role: 'admin',
  professional_id: null,
}
const RECEPTIONIST = { ...ADMIN, id: 'u-rec', full_name: 'Rec Demo', role: 'receptionist' }

const BLANQUEAMIENTO: Treatment = { id: 't-4', name: 'Blanqueamiento', active: true }
const CONSULTA: Treatment = { id: 't-1', name: 'Consulta', active: true }
const LIMPIEZA: Treatment = { id: 't-2', name: 'Limpieza dental', active: false }

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

function api(extra: Record<string, () => Response> = {}, me: object = ADMIN) {
  return mockApi({
    'GET /auth/me': () => jsonResponse(me),
    'GET /treatments': () => jsonResponse([BLANQUEAMIENTO, CONSULTA, LIMPIEZA]),
    ...extra,
  })
}

interface Write {
  url: string
  method: string
  body: unknown
}

function writes(fetchMock: ReturnType<typeof vi.fn>): Write[] {
  return (fetchMock.mock.calls as [string, RequestInit | undefined][])
    .filter(([, init]) => (init?.method ?? 'GET') !== 'GET')
    .map(([url, init]) => ({
      url,
      method: init?.method ?? 'GET',
      body: JSON.parse((init?.body as string | undefined) ?? 'null') as unknown,
    }))
}

describe('acceso a /tratamientos', () => {
  it('el administrador ve el enlace Tratamientos y el catálogo', async () => {
    api()

    renderApp('/tratamientos')

    expect(await screen.findByRole('heading', { name: 'Tratamientos' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Tratamientos' })).toHaveAttribute(
      'href',
      '/tratamientos',
    )
  })

  it.each([
    ['recepción', RECEPTIONIST],
    ['odontólogo', DENTIST],
  ])('%s no ve el enlace ni el catálogo y no pide la lista', async (_name, me) => {
    const fetchMock = api({}, me)

    renderApp('/tratamientos')

    expect(await screen.findByText(/^Hola, /)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tratamientos' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Tratamientos' })).not.toBeInTheDocument()
    expect(fetchMock.mock.calls.some((c) => String(c[0]).endsWith('/treatments'))).toBe(false)
  })
})

describe('catálogo de tratamientos', () => {
  it('lista por nombre con su estado', async () => {
    api()
    renderApp('/tratamientos')

    const rows = await screen.findAllByRole('row')

    const body = rows.slice(1).map((row) => within(row).getAllByRole('cell')[0]?.textContent)
    expect(body).toEqual(['Blanqueamiento', 'Consulta', 'Limpieza dental'])
    expect(within(rows[3] as HTMLElement).getByText('Inactivo')).toBeInTheDocument()
    expect(within(rows[1] as HTMLElement).getByText('Activo')).toBeInTheDocument()
  })

  it('catálogo vacío: aviso y formulario para agregar', async () => {
    api({ 'GET /treatments': () => jsonResponse([]) })
    renderApp('/tratamientos')

    expect(await screen.findByText('Todavía no hay tratamientos.')).toBeInTheDocument()
    expect(screen.getByLabelText('Nombre')).toBeInTheDocument()
  })

  it('si falla el pedido muestra el error y Reintentar vuelve a pedir', async () => {
    let fail = true
    api({ 'GET /treatments': () => (fail ? jsonResponse({}, 500) : jsonResponse([CONSULTA])) })
    renderApp('/tratamientos')

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar')
    fail = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('Consulta')).toBeInTheDocument()
  })

  it('agrega un tratamiento y aparece activo en su lugar alfabético', async () => {
    const created: Treatment = { id: 't-9', name: 'Conducto', active: true }
    const fetchMock = api({ 'POST /treatments': () => jsonResponse(created, 201) })
    renderApp('/tratamientos')
    await screen.findByText('Consulta')

    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Conducto' } })
    fireEvent.click(screen.getByRole('button', { name: 'Agregar tratamiento' }))

    await waitFor(() => {
      const names = screen
        .getAllByRole('row')
        .slice(1)
        .map((row) => within(row).getAllByRole('cell')[0]?.textContent)
      expect(names).toEqual(['Blanqueamiento', 'Conducto', 'Consulta', 'Limpieza dental'])
    })
    expect(screen.getByLabelText('Nombre')).toHaveValue('')
    const [{ url, body }] = writes(fetchMock) as [Write]
    expect(url).toBe(`${BASE}/treatments`)
    expect(body).toEqual({ name: 'Conducto' })
  })

  it('un doble clic en agregar envía un solo pedido', async () => {
    const fetchMock = api({
      'POST /treatments': () => jsonResponse({ id: 't-9', name: 'Conducto', active: true }, 201),
    })
    renderApp('/tratamientos')
    await screen.findByText('Consulta')

    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Conducto' } })
    const button = screen.getByRole('button', { name: 'Agregar tratamiento' })
    fireEvent.click(button)
    fireEvent.click(button)

    await screen.findByText('Conducto')
    expect(writes(fetchMock)).toHaveLength(1)
  })

  it('un nombre repetido muestra el aviso y la lista no cambia', async () => {
    api({
      'POST /treatments': () =>
        jsonResponse({ error: { code: 'TREATMENT_NAME_TAKEN', message: 'x' } }, 409),
    })
    renderApp('/tratamientos')
    await screen.findByText('Consulta')

    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'consulta' } })
    fireEvent.click(screen.getByRole('button', { name: 'Agregar tratamiento' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ya existe un tratamiento con ese nombre.',
    )
    expect(screen.getAllByRole('row')).toHaveLength(4)
    expect(screen.getByLabelText('Nombre')).toHaveValue('consulta')
  })

  it('renombra y guarda con PATCH solo con el nombre', async () => {
    const fetchMock = api({
      'PATCH /treatments/t-1': () => jsonResponse({ ...CONSULTA, name: 'Consulta general' }),
    })
    renderApp('/tratamientos')
    const row = (await screen.findByText('Consulta')).closest('tr') as HTMLElement

    fireEvent.click(within(row).getByRole('button', { name: 'Renombrar' }))
    fireEvent.change(screen.getByLabelText('Nuevo nombre'), {
      target: { value: 'Consulta general' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByText('Consulta general')).toBeInTheDocument()
    const [{ method, body }] = writes(fetchMock) as [Write]
    expect(method).toBe('PATCH')
    expect(body).toEqual({ name: 'Consulta general' })
  })

  it('renombrar a un nombre repetido muestra el aviso y conserva el nombre anterior', async () => {
    api({
      'PATCH /treatments/t-1': () =>
        jsonResponse({ error: { code: 'TREATMENT_NAME_TAKEN', message: 'x' } }, 409),
    })
    renderApp('/tratamientos')
    const row = (await screen.findByText('Consulta')).closest('tr') as HTMLElement

    fireEvent.click(within(row).getByRole('button', { name: 'Renombrar' }))
    fireEvent.change(screen.getByLabelText('Nuevo nombre'), {
      target: { value: 'Blanqueamiento' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ya existe un tratamiento con ese nombre.',
    )
  })

  it('desactivar pide confirmación y queda Inactivo; luego se puede activar', async () => {
    const fetchMock = api({
      'PATCH /treatments/t-4': (): Response => jsonResponse({ ...BLANQUEAMIENTO, active: false }),
    })
    renderApp('/tratamientos')
    const row = (await screen.findByText('Blanqueamiento')).closest('tr') as HTMLElement

    fireEvent.click(within(row).getByRole('button', { name: 'Desactivar' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent(
      'Los turnos que ya lo tienen no cambian. No se va a poder elegir en turnos nuevos.',
    )
    expect(writes(fetchMock)).toHaveLength(0)
    fireEvent.click(within(dialog).getByRole('button', { name: 'Desactivar' }))

    await waitFor(() => {
      expect(within(row).getByText('Inactivo')).toBeInTheDocument()
    })
    expect(within(row).getByRole('button', { name: 'Activar' })).toBeInTheDocument()
    const [{ body }] = writes(fetchMock) as [Write]
    expect(body).toEqual({ active: false })
  })

  it('cancelar la confirmación no envía nada', async () => {
    const fetchMock = api()
    renderApp('/tratamientos')
    const row = (await screen.findByText('Blanqueamiento')).closest('tr') as HTMLElement

    fireEvent.click(within(row).getByRole('button', { name: 'Desactivar' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(writes(fetchMock)).toHaveLength(0)
  })

  it('activar un tratamiento inactivo no pide confirmación', async () => {
    const fetchMock = api({
      'PATCH /treatments/t-2': () => jsonResponse({ ...LIMPIEZA, active: true }),
    })
    renderApp('/tratamientos')
    const row = (await screen.findByText('Limpieza dental')).closest('tr') as HTMLElement

    fireEvent.click(within(row).getByRole('button', { name: 'Activar' }))

    await waitFor(() => {
      expect(within(row).getByText('Activo')).toBeInTheDocument()
    })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    const [{ body }] = writes(fetchMock) as [Write]
    expect(body).toEqual({ active: true })
  })
})
