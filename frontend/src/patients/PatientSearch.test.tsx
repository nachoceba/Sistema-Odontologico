import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import { PatientSearch } from './PatientSearch'

const JUAN = {
  id: 'pac-1',
  first_name: 'Juan',
  last_name: 'Pérez',
  document_number: '30111222',
  email: 'juan@example.com',
  phone: null,
  birth_date: null,
  active: true,
}
const LUCIA = { ...JUAN, id: 'pac-3', first_name: 'Lucía', last_name: 'Pereyra' }

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  saveToken('tok')
})

afterEach(() => {
  clearToken()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('PatientSearch reutilizable', () => {
  it('busca solo pacientes activos y entrega id y nombre al elegir', async () => {
    const fetchMock = mockApi({
      'GET /patients?q=per': () => jsonResponse({ items: [JUAN, LUCIA], truncated: false }),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
    })
    const onSelect = vi.fn()
    render(<PatientSearch onSelect={onSelect} />)

    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar paciente' }), {
      target: { value: 'per' },
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Pérez, Juan' }))

    expect(onSelect).toHaveBeenCalledExactlyOnceWith({ id: 'pac-1', name: 'Pérez, Juan' })
    const urls = (fetchMock.mock.calls as [string][]).map((call) => call[0])
    expect(urls.some((url) => url.includes('include_inactive'))).toBe(false)
    expect(screen.getByRole('button', { name: 'Pereyra, Lucía' })).toBeInTheDocument()
  })

  it('sin coincidencias muestra "No se encontraron pacientes"', async () => {
    mockApi({
      'GET /patients?q=zzz': () => jsonResponse({ items: [], truncated: false }),
      'GET /patients': () => jsonResponse({ items: [], truncated: false }),
    })
    render(<PatientSearch onSelect={vi.fn()} />)

    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar paciente' }), {
      target: { value: 'zzz' },
    })

    await waitFor(() => {
      expect(screen.getByText('No se encontraron pacientes')).toBeInTheDocument()
    })
  })

  it('no pide nada ni lista mientras el campo está vacío', () => {
    const fetchMock = mockApi({})
    render(<PatientSearch onSelect={vi.fn()} />)

    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
