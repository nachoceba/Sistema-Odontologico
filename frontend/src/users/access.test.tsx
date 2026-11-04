import { screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, readToken, saveToken } from '../auth/session'
import { BASE, DENTIST, jsonResponse, mockApi, renderApp } from '../test-utils'

const ADMIN = {
  id: 'u-admin',
  email: 'admin@example.com',
  full_name: 'Admin Demo',
  role: 'admin',
  professional_id: null,
}
const RECEPTIONIST = { ...ADMIN, id: 'u-rec', full_name: 'Rec Demo', role: 'receptionist' }

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  window.sessionStorage.clear()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('acceso a la pantalla de usuarios', () => {
  it('el administrador ve el enlace "Usuarios" en /agenda', async () => {
    saveToken('tok-admin')
    mockApi({ 'GET /auth/me': () => jsonResponse(ADMIN) })

    renderApp('/agenda')

    const link = await screen.findByRole('link', { name: 'Usuarios' })
    expect(link).toHaveAttribute('href', '/usuarios')
  })

  it('la recepción no ve el enlace "Usuarios"', async () => {
    saveToken('tok-rec')
    mockApi({ 'GET /auth/me': () => jsonResponse(RECEPTIONIST) })

    renderApp('/agenda')

    expect(await screen.findByText('Hola, Rec Demo')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument()
  })

  it('un odontólogo tampoco ve el enlace', async () => {
    saveToken('tok-dra')
    mockApi({ 'GET /auth/me': () => jsonResponse(DENTIST) })

    renderApp('/agenda')

    expect(await screen.findByText('Hola, Dra. Ana Pérez')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument()
  })

  it('un odontólogo que escribe /usuarios ve el aviso, conserva la sesión y no pide el listado', async () => {
    saveToken('tok-dra')
    const fetchMock = mockApi({ 'GET /auth/me': () => jsonResponse(DENTIST) })

    renderApp('/usuarios')

    expect(await screen.findByText('No tenés permiso para esta acción')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Volver a la agenda' })).toHaveAttribute(
      'href',
      '/agenda',
    )
    expect(readToken()).toBe('tok-dra')
    const urls = fetchMock.mock.calls.map((call) => String(call[0]))
    expect(urls.some((url) => url.endsWith('/users'))).toBe(false)
  })

  it('la recepción que escribe /usuarios recibe el mismo aviso', async () => {
    saveToken('tok-rec')
    mockApi({ 'GET /auth/me': () => jsonResponse(RECEPTIONIST) })

    renderApp('/usuarios')

    expect(await screen.findByText('No tenés permiso para esta acción')).toBeInTheDocument()
  })

  it('sin sesión, /usuarios lleva a /login', async () => {
    mockApi({ 'GET /health': () => jsonResponse({ status: 'ok' }) })

    renderApp('/usuarios')

    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeInTheDocument()
  })

  it('el administrador entra a /usuarios y se pide el listado', async () => {
    saveToken('tok-admin')
    mockApi({
      'GET /auth/me': () => jsonResponse(ADMIN),
      'GET /users': () => jsonResponse([]),
    })

    renderApp('/usuarios')

    expect(await screen.findByRole('heading', { name: 'Usuarios' })).toBeInTheDocument()
  })
})
