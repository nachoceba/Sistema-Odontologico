import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DRA, DR_B, installAgendaApi } from '../agenda/testApi'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi, renderApp } from '../test-utils'
import { ToothMark } from './ToothMark'

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

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  clearToken()
  window.sessionStorage.clear()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('ToothMark', () => {
  it('es decorativo: oculto para lectores de pantalla, sin foco, sin rol ni nombre', () => {
    const { container } = render(<ToothMark />)

    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg).toHaveAttribute('aria-hidden', 'true')
    expect(svg).toHaveAttribute('focusable', 'false')
    expect(svg).not.toHaveAttribute('role')
    expect(svg).not.toHaveAttribute('aria-label')
    expect(svg?.querySelector('title')).toBeNull()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('el pulso es opcional: sin él no lleva la clase de animación', () => {
    const { container, rerender } = render(<ToothMark />)
    expect(container.querySelector('svg')).not.toHaveClass('tooth-mark--pulse')

    rerender(<ToothMark pulse />)
    expect(container.querySelector('svg')).toHaveClass('tooth-mark--pulse')
  })
})

describe('el diente en las pantallas', () => {
  it('el login lo muestra sin cambiar el nombre del título ni del botón', async () => {
    mockApi({ 'GET /health': () => jsonResponse({ status: 'ok' }) })

    const { container } = renderApp('/login')

    const button = await screen.findByRole('button', { name: 'Ingresar' })
    const heading = screen.getByRole('heading', { name: 'Sistema Odontológico' })
    expect(container.querySelector('.login-brand .tooth-mark')).not.toBeNull()
    expect(heading.querySelector('svg')).toBeNull()
    expect(button.querySelector('svg')).toBeNull()
    expect(container.querySelectorAll('input svg, label svg')).toHaveLength(0)
  })

  it('la barra lo muestra junto al nombre del sistema y los enlaces conservan su nombre', async () => {
    saveToken('tok')
    mockApi({ 'GET /auth/me': () => jsonResponse(RECEPTIONIST) })

    renderApp('/profesionales')

    const nav = await screen.findByRole('navigation', { name: 'Principal' })
    expect(nav.querySelector('.app-brand .tooth-mark')).not.toBeNull()
    expect(nav.querySelector('.app-brand')).toHaveTextContent('Sistema Odontológico')
    expect(screen.getByRole('link', { name: 'Agenda' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Salir' })).toBeInTheDocument()
  })

  it('el aviso inicial "Cargando…" conserva role="status" y su texto y el diente pulsa', async () => {
    saveToken('tok')
    mockApi({ 'GET /auth/me': () => new Promise<Response>(() => undefined) })

    renderApp('/agenda')

    const status = await screen.findByRole('status')
    expect(status).toHaveTextContent(/^Cargando…$/)
    expect(status.querySelector('svg.tooth-mark--pulse')).not.toBeNull()
  })

  it('el aviso de carga de profesionales también lo muestra, con el mismo texto', async () => {
    saveToken('tok')
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /professionals': () => new Promise<Response>(() => undefined),
    })

    renderApp('/profesionales')

    const status = await screen.findByRole('status')
    expect(status).toHaveTextContent(/^Cargando…$/)
    expect(status.querySelector('svg.tooth-mark--pulse')).not.toBeNull()
  })

  it('el aviso de pacientes vacío lo muestra quieto y con el mismo texto', async () => {
    saveToken('tok')
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
    })

    renderApp('/pacientes')

    const empty = await screen.findByText('No se encontraron pacientes')
    const status = empty.closest('[role="status"]')
    expect(status).not.toBeNull()
    expect(status?.querySelector('svg.tooth-mark')).not.toBeNull()
    expect(status?.querySelector('svg.tooth-mark--pulse')).toBeNull()
  })

  it('no hay ningún diente dentro de la tabla de pacientes', async () => {
    saveToken('tok')
    mockApi({
      'GET /auth/me': () => jsonResponse(RECEPTIONIST),
      'GET /patients': () => jsonResponse({ items: [JUAN], truncated: false }),
    })

    const { container } = renderApp('/pacientes')

    await screen.findByText('Pérez, Juan')
    expect(container.querySelector('table')).not.toBeNull()
    expect(container.querySelectorAll('table .tooth-mark')).toHaveLength(0)
  })

  it('no hay ningún diente dentro de la grilla de la semana', async () => {
    saveToken('tok')
    installAgendaApi({
      me: RECEPTIONIST,
      professionals: [DRA, DR_B],
      appointments: [],
      timeOff: [],
      conflicts: [],
    })

    const { container } = renderApp('/agenda?vista=semana&fecha=2026-11-09')

    await waitFor(() => {
      expect(container.querySelector('.week-grid .day-column')).not.toBeNull()
    })
    await act(async () => {
      await Promise.resolve()
    })
    expect(container.querySelectorAll('.week-grid .tooth-mark')).toHaveLength(0)
  })
})

describe('animación del diente en styles.css', () => {
  const css = readFileSync(join(process.cwd(), 'src', 'styles.css'), 'utf8')

  it('existe un pulso suave que varía la opacidad entre 0,6 y 1', () => {
    expect(css).toMatch(/\.tooth-mark--pulse\s*\{[^}]*animation:\s*tooth-pulse/)
    const keyframes = /@keyframes tooth-pulse\s*\{([\s\S]*?)\n\}/.exec(css)?.[1] ?? ''
    expect(keyframes).toContain('opacity: 1')
    expect(keyframes).toContain('opacity: 0.6')
  })

  it('con prefers-reduced-motion: reduce el diente queda sin animación', () => {
    const reduced = /@media \(prefers-reduced-motion: reduce\)\s*\{([\s\S]*?)\n\}/.exec(css)?.[1] ?? ''
    expect(reduced).toMatch(/\.tooth-mark--pulse\s*\{[^}]*animation:\s*none/)
  })
})
