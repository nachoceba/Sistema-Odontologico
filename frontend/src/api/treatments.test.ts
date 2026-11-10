import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import {
  createTreatment,
  listProfessionalTreatments,
  listTreatments,
  replaceProfessionalTreatments,
  updateTreatment,
  type Treatment,
} from './treatments'
import { ApiError } from './users'

const CONSULTA: Treatment = { id: 't-1', name: 'Consulta', active: true }

function bodyOf(fetchMock: ReturnType<typeof vi.fn>): unknown {
  return JSON.parse((fetchMock.mock.calls[0]?.[1] as RequestInit).body as string)
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  saveToken('tok')
})

afterEach(() => {
  clearToken()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('cliente de tratamientos', () => {
  it('lista el catálogo con el token', async () => {
    const fetchMock = mockApi({ 'GET /treatments': () => jsonResponse([CONSULTA]) })

    expect(await listTreatments()).toEqual([CONSULTA])
    const headers = new Headers((fetchMock.mock.calls[0]?.[1] as RequestInit).headers)
    expect(headers.get('Authorization')).toBe('Bearer tok')
  })

  it('crea con solo el nombre', async () => {
    const fetchMock = mockApi({ 'POST /treatments': () => jsonResponse(CONSULTA, 201) })

    expect(await createTreatment('Consulta')).toEqual(CONSULTA)
    expect(bodyOf(fetchMock)).toEqual({ name: 'Consulta' })
  })

  it('actualiza con PATCH y manda solo los campos dados', async () => {
    const fetchMock = mockApi({
      'PATCH /treatments/t%201': () => jsonResponse({ ...CONSULTA, active: false }),
    })

    const result = await updateTreatment('t 1', { active: false })

    expect(result.active).toBe(false)
    expect(bodyOf(fetchMock)).toEqual({ active: false })
  })

  it('lee y reemplaza la asignación de un profesional', async () => {
    const fetchMock = mockApi({
      'GET /professionals/p-1/treatments': () => jsonResponse([CONSULTA]),
      'PUT /professionals/p-1/treatments': () => jsonResponse([CONSULTA]),
    })

    expect(await listProfessionalTreatments('p-1')).toEqual([CONSULTA])
    expect(await replaceProfessionalTreatments('p-1', ['t-1'])).toEqual([CONSULTA])
    const put = fetchMock.mock.calls[1]?.[1] as RequestInit
    expect(put.method).toBe('PUT')
    expect(JSON.parse(put.body as string)).toEqual({ treatment_ids: ['t-1'] })
  })

  it('un nombre repetido llega como ApiError con su código', async () => {
    mockApi({
      'POST /treatments': () =>
        jsonResponse({ error: { code: 'TREATMENT_NAME_TAKEN', message: 'x' } }, 409),
    })

    await expect(createTreatment('Consulta')).rejects.toMatchObject({
      status: 409,
      code: 'TREATMENT_NAME_TAKEN',
    })
    await expect(createTreatment('Consulta')).rejects.toBeInstanceOf(ApiError)
  })
})
