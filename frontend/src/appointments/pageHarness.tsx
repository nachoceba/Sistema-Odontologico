import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { vi } from 'vitest'
import App from '../App'
import { clearToken, saveToken } from '../auth/session'
import { DR_B, DRA, type AgendaWorld } from '../agenda/testApi'
import { BASE } from '../test-utils'

export const RECEPTIONIST = {
  id: 'u-rec',
  email: 'rec@example.com',
  full_name: 'Rec Demo',
  role: 'receptionist',
  professional_id: null,
}
export const DENTIST_A = {
  id: 'u-1',
  email: 'dra.a@example.com',
  full_name: 'Dra. Ana Álvarez',
  role: 'dentist',
  professional_id: 'p-1',
}

function Probe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname + location.search}</output>
}

export function open(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
      <Probe />
    </MemoryRouter>,
  )
}

export function world(overrides: Partial<AgendaWorld> = {}): AgendaWorld {
  return {
    me: RECEPTIONIST,
    professionals: [DRA, DR_B],
    appointments: [],
    timeOff: [],
    conflicts: [],
    patients: [{ id: 'pac-1', first_name: 'Juan', last_name: 'Perez' }],
    ...overrides,
  }
}

/** Sesión abierta, API configurada y reloj fijo (solo `Date`) a un instante UTC. */
export function startSession(nowIso: string): void {
  vi.stubEnv('VITE_API_URL', BASE)
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(nowIso))
  clearToken()
  window.sessionStorage.clear()
  saveToken('tok')
}

export function endSession(): void {
  vi.useRealTimers()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
}

/** La fila de la grilla que contiene ese texto (por ejemplo `14:00–14:30`). */
export function rowOf(text: string): HTMLElement {
  const row = screen.getByText(text).closest('li.slot')
  if (!(row instanceof HTMLElement)) throw new Error(`sin fila para ${text}`)
  return row
}

export function inRow(text: string) {
  return within(rowOf(text))
}

export const lastLocation = (): string | null => screen.getByTestId('location').textContent
