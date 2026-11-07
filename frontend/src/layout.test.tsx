import { fireEvent, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from './auth/session'
import { BASE, DENTIST, jsonResponse, mockApi, renderApp } from './test-utils'

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

function linkNames(): string[] {
  const nav = screen.getByRole('navigation', { name: 'Principal' })
  return Array.from(nav.querySelectorAll('a, button')).map((element) => element.textContent ?? '')
}

describe('marco común de las pantallas con sesión', () => {
  it('administración en /pacientes ve la barra completa y Pacientes marcado como actual', async () => {
    saveToken('tok-admin')
    mockApi({ 'GET /auth/me': () => jsonResponse(ADMIN) })

    renderApp('/pacientes')

    expect(await screen.findByRole('heading', { name: 'Pacientes' })).toBeInTheDocument()
    expect(linkNames()).toEqual(['Agenda', 'Pacientes', 'Profesionales', 'Usuarios', 'Salir'])
    expect(screen.getByRole('link', { name: 'Pacientes' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Agenda' })).not.toHaveAttribute('aria-current')
  })

  it.each([
    ['recepción', RECEPTIONIST, 'Hola, Rec Demo'],
    ['un odontólogo', DENTIST, 'Hola, Dra. Ana Pérez'],
  ])('%s en /profesionales no ve "Usuarios" y ve Profesionales como actual', async (_name, user, greeting) => {
    saveToken('tok')
    mockApi({ 'GET /auth/me': () => jsonResponse(user) })

    renderApp('/profesionales')

    expect(await screen.findByText(greeting)).toBeInTheDocument()
    expect(linkNames()).toEqual(['Agenda', 'Pacientes', 'Profesionales', 'Salir'])
    expect(screen.getByRole('link', { name: 'Profesionales' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  it('/login no muestra la barra de navegación', async () => {
    mockApi({ 'GET /health': () => jsonResponse({ status: 'ok' }) })

    renderApp('/login')

    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Principal' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Saltar al contenido' })).not.toBeInTheDocument()
  })

  it('"Saltar al contenido" es el primer elemento enfocable y deja el foco en el contenido principal', async () => {
    saveToken('tok-admin')
    mockApi({ 'GET /auth/me': () => jsonResponse(ADMIN) })

    renderApp('/usuarios')

    const skip = await screen.findByRole('link', { name: 'Saltar al contenido' })
    const first = document.body.querySelector('a[href], button, input, select, textarea')
    expect(first).toBe(skip)

    fireEvent.click(skip)

    const main = screen.getByRole('main')
    expect(main).toHaveAttribute('id', 'contenido')
    expect(document.activeElement).toBe(main)
  })

  it('recepción en /usuarios ve la barra y el aviso con "Volver a la agenda", sin pedir /users', async () => {
    saveToken('tok-rec')
    const fetchMock = mockApi({ 'GET /auth/me': () => jsonResponse(RECEPTIONIST) })

    renderApp('/usuarios')

    expect(await screen.findByText('No tenés permiso para esta acción')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Principal' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Volver a la agenda' })).toHaveAttribute(
      'href',
      '/agenda',
    )
    const urls = fetchMock.mock.calls.map((call) => String(call[0]))
    expect(urls.some((url) => url.endsWith('/users'))).toBe(false)
  })

  it('cada pantalla tiene un solo contenido principal', async () => {
    saveToken('tok-admin')
    mockApi({ 'GET /auth/me': () => jsonResponse(ADMIN) })

    renderApp('/agenda')

    await screen.findByRole('heading', { name: 'Agenda' })
    expect(screen.getAllByRole('main')).toHaveLength(1)
    expect(screen.getAllByRole('navigation', { name: 'Principal' })).toHaveLength(1)
  })
})
