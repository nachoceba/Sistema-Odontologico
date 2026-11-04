import { fireEvent, screen } from '@testing-library/react'
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
const RECEPTIONIST = { ...ADMIN, id: 'u-rec', full_name: 'Rec Demo', role: 'receptionist' }
const DENTIST_NO_FILE = { ...DENTIST, id: 'u-2', professional_id: null }

const DRA = { id: 'p-1', display_name: 'Dra. Ana Álvarez', license_number: 'MAT-0001', active: true }
const DR_B = { id: 'p-2', display_name: 'Dr. Bruno Benítez', license_number: null, active: false }
const MONDAY = { weekday: 0, start_time: '09:00', end_time: '13:00' }
const LEAVE = { id: 't-1', starts_on: '2026-10-12', ends_on: '2026-10-16', reason: 'Congreso' }

function detailHandlers(id: string) {
  return {
    [`GET /professionals/${id}/working-hours`]: () => jsonResponse({ blocks: [MONDAY] }),
    [`GET /professionals/${id}/time-off`]: () => jsonResponse([LEAVE]),
  }
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

describe('acceso a la pantalla de profesionales', () => {
  it('el administrador ve los controles de edición al elegir a la Dra. A', async () => {
    saveToken('tok-admin')
    mockApi({
      'GET /auth/me': () => jsonResponse(ADMIN),
      'GET /professionals': () => jsonResponse([DRA, DR_B]),
      ...detailHandlers('p-1'),
    })

    renderApp('/profesionales')
    fireEvent.click(await screen.findByRole('button', { name: 'Ver a Dra. Ana Álvarez' }))

    expect(await screen.findByRole('button', { name: 'Editar ficha' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Guardar horario' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agregar licencia' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Borrar' })).toBeInTheDocument()
  })

  it('la recepción ve horario y licencias sin ningún botón de edición', async () => {
    saveToken('tok-rec')
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /professionals': () => jsonResponse([DRA, DR_B]),
      ...detailHandlers('p-1'),
    })

    renderApp('/profesionales')
    fireEvent.click(await screen.findByRole('button', { name: 'Ver a Dra. Ana Álvarez' }))

    expect(await screen.findByText('Congreso')).toBeInTheDocument()
    expect(screen.getByLabelText('Lunes, tramo 1, inicio')).toBeDisabled()
    for (const name of ['Editar ficha', 'Guardar horario', 'Agregar licencia', 'Borrar']) {
      expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
    }
  })

  it('la odontóloga ve solo su ficha, ya abierta y sin selector de otros', async () => {
    saveToken('tok-dra')
    mockApi({
      'GET /auth/me': () => jsonResponse(DENTIST),
      'GET /professionals': () => jsonResponse([DRA]),
      ...detailHandlers('p-1'),
    })

    renderApp('/profesionales')

    expect(await screen.findByText('Congreso')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Ver a / })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Editar ficha' })).not.toBeInTheDocument()
  })

  it('un odontólogo sin ficha ve el aviso y no hay errores', async () => {
    saveToken('tok-dr')
    mockApi({
      'GET /auth/me': () => jsonResponse(DENTIST_NO_FILE),
      'GET /professionals': () => jsonResponse([]),
    })

    renderApp('/profesionales')

    expect(
      await screen.findByText('No tenés una ficha de profesional asociada'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('sin sesión, /profesionales lleva a /login', async () => {
    mockApi({})

    renderApp('/profesionales')

    expect(await screen.findByRole('heading', { name: 'Sistema Odontológico' })).toBeInTheDocument()
  })

  it('los tres roles ven el enlace "Profesionales" en la agenda', async () => {
    saveToken('tok-rec')
    mockApi({ 'GET /auth/me': () => jsonResponse(RECEPTIONIST) })

    renderApp('/agenda')

    const link = await screen.findByRole('link', { name: 'Profesionales' })
    expect(link).toHaveAttribute('href', '/profesionales')
  })
})
