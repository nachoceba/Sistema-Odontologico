import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { vi } from 'vitest'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import PublicBookingPage from './PublicBookingPage'

export { BASE, jsonResponse, mockApi }

/** Lunes 9 de noviembre de 2026, 10:00 en el consultorio. */
export const NOW = new Date('2026-11-09T13:00:00Z')

export const DRA_A = { id: 'p-1', display_name: 'Dra. A' }
export const SLOT_1030 = { starts_at: '2026-11-09T13:30:00Z', ends_at: '2026-11-09T14:00:00Z' }
export const SLOT_1100 = { starts_at: '2026-11-09T14:00:00Z', ends_at: '2026-11-09T14:30:00Z' }
export const SLOTS_URL = 'GET /public/professionals/p-1/slots?date=2026-11-09'
export const REGISTERED = {
  starts_at: SLOT_1030.starts_at,
  ends_at: SLOT_1030.ends_at,
  professional_display_name: 'Dra. A',
  confirm_before: '2026-11-09T16:00:00Z',
}

export function useFixedClock(): void {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
}

export function Probe() {
  const location = useLocation()
  return <span data-testid="location">{`${location.pathname}${location.hash}`}</span>
}

export function renderBooking() {
  return render(
    <MemoryRouter initialEntries={['/turnos']}>
      <PublicBookingPage />
      <Probe />
    </MemoryRouter>,
  )
}

export interface Person {
  document: string
  first: string
  last: string
  email: string
  phone?: string
}

export const LUCIA: Person = {
  document: '40999888',
  first: 'Lucía',
  last: 'Díaz',
  email: 'lucia@example.com',
  phone: '11 5555-1234',
}

/** Elige a la Dra. A, la franja de las 10:30 de hoy y deja el formulario a la vista. */
export async function pickSlot(): Promise<void> {
  fireEvent.click(await screen.findByRole('button', { name: 'Dra. A' }))
  fireEvent.click(await screen.findByRole('button', { name: '10:30' }))
  await screen.findByLabelText('DNI')
}

export function fillForm(person: Person): void {
  fireEvent.change(screen.getByLabelText('DNI'), { target: { value: person.document } })
  fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: person.first } })
  fireEvent.change(screen.getByLabelText('Apellido'), { target: { value: person.last } })
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: person.email } })
  if (person.phone !== undefined) {
    fireEvent.change(screen.getByLabelText('Teléfono (opcional)'), {
      target: { value: person.phone },
    })
  }
}
