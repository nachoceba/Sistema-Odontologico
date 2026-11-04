import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import {
  ApiError,
  createUser,
  deactivateUser,
  listUsers,
  reactivateUser,
  setPassword,
  updateUser,
  type ManagedUser,
} from './users'

const REC: ManagedUser = {
  id: 'u-rec',
  email: 'recepcion@example.com',
  full_name: 'Rec Demo',
  role: 'receptionist',
  active: true,
  professional_id: null,
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  saveToken('tok-admin')
})

afterEach(() => {
  clearToken()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

function lastCall(fetchMock: ReturnType<typeof vi.fn>): { url: string; init: RequestInit } {
  const call = fetchMock.mock.calls.at(-1) as [string, RequestInit]
  return { url: call[0], init: call[1] }
}

describe('cliente de la API de usuarios', () => {
  it('listUsers pide GET /users con el token y devuelve las cuentas tipadas', async () => {
    const fetchMock = mockApi({ 'GET /users': () => jsonResponse([REC]) })

    const users = await listUsers()

    expect(users).toEqual([REC])
    const { init } = lastCall(fetchMock)
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer tok-admin')
  })

  it('createUser envía POST /users con el cuerpo JSON y devuelve la cuenta creada', async () => {
    const fetchMock = mockApi({ 'POST /users': () => jsonResponse(REC, 201) })
    const input = {
      email: 'recepcion@example.com',
      full_name: 'Rec Demo',
      role: 'receptionist' as const,
      password: 'clave-inicial-12',
    }

    const created = await createUser(input)

    expect(created).toEqual(REC)
    const { init } = lastCall(fetchMock)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual(input)
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
  })

  it('updateUser envía PATCH /users/{id} solo con los campos pedidos', async () => {
    const fetchMock = mockApi({ 'PATCH /users/u-rec': () => jsonResponse({ ...REC, full_name: 'Otro' }) })

    const updated = await updateUser('u-rec', { full_name: 'Otro' })

    expect(updated.full_name).toBe('Otro')
    const { init } = lastCall(fetchMock)
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body as string)).toEqual({ full_name: 'Otro' })
  })

  it('deactivateUser y reactivateUser usan POST al endpoint de cada acción', async () => {
    const fetchMock = mockApi({
      'POST /users/u-rec/deactivate': () => jsonResponse({ ...REC, active: false }),
      'POST /users/u-rec/reactivate': () => jsonResponse(REC),
    })

    expect((await deactivateUser('u-rec')).active).toBe(false)
    expect(lastCall(fetchMock).init.method).toBe('POST')
    expect((await reactivateUser('u-rec')).active).toBe(true)
    expect(lastCall(fetchMock).url).toBe(`${BASE}/users/u-rec/reactivate`)
  })

  it('setPassword envía PUT /users/{id}/password y acepta el 204 sin cuerpo', async () => {
    const fetchMock = mockApi({
      'PUT /users/u-rec/password': () => new Response(null, { status: 204 }),
    })

    await expect(setPassword('u-rec', 'clave-nueva-123')).resolves.toBeUndefined()

    const { init } = lastCall(fetchMock)
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body as string)).toEqual({ password: 'clave-nueva-123' })
  })

  it('un 409 lanza ApiError con status y code', async () => {
    mockApi({
      'POST /users': () =>
        jsonResponse({ error: { code: 'EMAIL_TAKEN', message: 'Ya existe' } }, 409),
    })

    const error = await createUser({
      email: 'a@b.com',
      full_name: 'A',
      role: 'receptionist',
      password: 'clave-inicial-12',
    }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 409, code: 'EMAIL_TAKEN' })
  })

  it('un 422 de validación lanza ApiError con code null', async () => {
    mockApi({
      'PATCH /users/u-rec': () =>
        jsonResponse({ detail: [{ loc: ['body', 'email'], msg: 'x', type: 'value_error' }] }, 422),
    })

    const error = await updateUser('u-rec', { email: 'mal' }).catch((e: unknown) => e)

    expect(error).toMatchObject({ status: 422, code: null })
  })

  it('un 404 sin cuerpo JSON igual lanza ApiError con el status', async () => {
    mockApi({ 'GET /users': () => new Response('no', { status: 404 }) })

    await expect(listUsers()).rejects.toMatchObject({ status: 404, code: null })
  })

  it('un error de red se propaga sin convertirse en ApiError', async () => {
    mockApi({ 'GET /users': () => Promise.reject(new TypeError('Failed to fetch')) })

    const error = await listUsers().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(TypeError)
    expect(error).not.toBeInstanceOf(ApiError)
  })
})
