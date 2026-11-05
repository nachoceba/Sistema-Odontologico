import { screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, DENTIST, jsonResponse, mockApi, renderApp } from '../test-utils'

const ADMIN = {
  id: 'u-admin',
  email: 'admin@example.com',
  full_name: 'Admin Demo',
  role: 'admin',
  professional_id: null,
}
const RECEPTIONIST = {
  ...ADMIN,
  id: 'u-rec',
  full_name: 'Rec Demo',
  role: 'receptionist',
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
const ANA = {
  ...JUAN,
  id: 'pac-2',
  first_name: 'Ana',
  last_name: 'Gómez',
  active: false,
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  window.sessionStorage.clear()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

function mockFor(user: object) {
  saveToken('tok')
  return mockApi({
    'GET /auth/me': () => jsonResponse(user),
    'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
    'GET /patients?include_inactive=true': () =>
      jsonResponse({ items: [ANA, JUAN], truncated: false }),
  })
}

describe('acceso a la pantalla de pacientes', () => {
  it('la recepción ve Nuevo paciente, Editar y Desactivar, y no ve Borrar', async () => {
    mockFor(RECEPTIONIST)

    renderApp('/pacientes')

    expect(await screen.findByRole('button', { name: 'Nuevo paciente' })).toBeInTheDocument()
    const row = (await screen.findByText('Pérez, Juan')).closest('tr')
    expect(row).not.toBeNull()
    const inRow = within(row as HTMLElement)
    expect(inRow.getByRole('button', { name: 'Editar' })).toBeInTheDocument()
    expect(inRow.getByRole('button', { name: 'Desactivar' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Borrar' })).not.toBeInTheDocument()
  })

  it('el administrador también ve Borrar', async () => {
    mockFor(ADMIN)

    renderApp('/pacientes')

    expect(await screen.findByRole('button', { name: 'Borrar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nuevo paciente' })).toBeInTheDocument()
  })

  it('la Dra. A ve el listado y la búsqueda, sin ningún control de escritura', async () => {
    mockFor(DENTIST)

    renderApp('/pacientes')

    expect(await screen.findByText('Pérez, Juan')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Buscar paciente' })).toBeInTheDocument()
    for (const name of ['Nuevo paciente', 'Editar', 'Desactivar', 'Reactivar', 'Borrar']) {
      expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
    }
  })

  it('sin sesión, /pacientes lleva a /login', async () => {
    mockApi({})

    renderApp('/pacientes')

    expect(await screen.findByRole('heading', { name: 'Sistema Odontológico' })).toBeInTheDocument()
  })

  it.each([
    ['recepción', RECEPTIONIST],
    ['administración', ADMIN],
    ['odontóloga', DENTIST],
  ])('%s ve el enlace "Pacientes" en la agenda', async (_name, user) => {
    saveToken('tok')
    mockApi({ 'GET /auth/me': () => jsonResponse(user) })

    renderApp('/agenda')

    expect(await screen.findByRole('link', { name: 'Pacientes' })).toHaveAttribute(
      'href',
      '/pacientes',
    )
  })
})
