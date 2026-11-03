import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, readToken, saveToken } from './session'

describe('session (token en sessionStorage)', () => {
  beforeEach(() => {
    clearToken()
    window.sessionStorage.clear()
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('guarda, lee y borra el token', () => {
    expect(readToken()).toBeNull()
    saveToken('abc')
    expect(readToken()).toBe('abc')
    expect(window.sessionStorage.getItem('auth_token')).toBe('abc')
    clearToken()
    expect(readToken()).toBeNull()
    expect(window.sessionStorage.getItem('auth_token')).toBeNull()
  })

  it('nunca escribe en localStorage', () => {
    saveToken('abc')
    expect(window.localStorage.length).toBe(0)
  })

  it('el segundo token reemplaza al primero', () => {
    saveToken('uno')
    saveToken('dos')
    expect(readToken()).toBe('dos')
  })

  it('si sessionStorage falla al escribir, la sesión vive en memoria', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('bloqueado', 'SecurityError')
    })
    saveToken('en-memoria')
    expect(readToken()).toBe('en-memoria')
    clearToken()
    expect(readToken()).toBeNull()
  })

  it('si sessionStorage falla al leer, devuelve el token de memoria o null', () => {
    saveToken('abc')
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('bloqueado', 'SecurityError')
    })
    expect(readToken()).toBe('abc')
    clearToken()
    expect(readToken()).toBeNull()
  })
})
