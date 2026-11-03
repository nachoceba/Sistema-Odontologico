import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiUrl } from './config'

describe('apiUrl', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('arma la URL con la base configurada', () => {
    vi.stubEnv('VITE_API_URL', 'http://localhost:8000/api/v1')

    expect(apiUrl('/health')).toBe('http://localhost:8000/api/v1/health')
  })

  it('no duplica la barra cuando la base termina en barra', () => {
    vi.stubEnv('VITE_API_URL', 'http://localhost:8000/api/v1/')

    expect(apiUrl('/health')).toBe('http://localhost:8000/api/v1/health')
  })

  it('acepta rutas sin barra inicial', () => {
    vi.stubEnv('VITE_API_URL', 'http://localhost:8000/api/v1//')

    expect(apiUrl('health')).toBe('http://localhost:8000/api/v1/health')
  })

  it('devuelve null si la variable falta', () => {
    vi.stubEnv('VITE_API_URL', undefined)

    expect(apiUrl('/health')).toBeNull()
  })

  it('devuelve null si la variable esta vacia o solo tiene espacios', () => {
    vi.stubEnv('VITE_API_URL', '   ')

    expect(apiUrl('/health')).toBeNull()
  })
})
