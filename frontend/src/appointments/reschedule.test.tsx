import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { at, daySlots, turno } from '../agenda/fixtures'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import { RescheduleDialog } from './RescheduleDialog'

const TARGET = turno(10, 0, 10, 30) // Lun 09/11 10:00
const RECORD = { ...TARGET, starts_at: at(11, 0, 10), ends_at: at(11, 30, 10) }
const WORKDAY = [
  [9, 13],
  [14, 18],
] as const

const MONDAY = daySlots(WORKDAY, { day: 9, busy: ['10:00'] })
const TUESDAY = daySlots(WORKDAY, { day: 10 })
const SUNDAY = daySlots([], { day: 15 })

function api(extra: Record<string, () => Response> = {}) {
  return mockApi({
    'GET /professionals/p-1/slots?date=2026-11-09': () => jsonResponse(MONDAY),
    'GET /professionals/p-1/slots?date=2026-11-10': () => jsonResponse(TUESDAY),
    'GET /professionals/p-1/slots?date=2026-11-15': () => jsonResponse(SUNDAY),
    ...extra,
  })
}

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-09T11:00:00Z')) // 08:00 en el consultorio
  saveToken('tok')
})

afterEach(() => {
  clearToken()
  vi.useRealTimers()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

function setup() {
  const handlers = { onDone: vi.fn(), onRejected: vi.fn(), onClose: vi.fn() }
  render(<RescheduleDialog appointment={TARGET} role="receptionist" {...handlers} />)
  return handlers
}

const slotButton = (range: string) => screen.findByRole('button', { name: range })

describe('RescheduleDialog: elegir el horario', () => {
  it('al abrir muestra la fecha del turno y sus franjas libres, sin la del propio turno', async () => {
    const fetchMock = api()
    setup()

    expect(await slotButton('09:00–09:30')).toBeInTheDocument()
    expect(screen.getByLabelText('Fecha')).toHaveValue('2026-11-09')
    expect(screen.getByRole('button', { name: '09:30–10:00' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '10:00–10:30' })).not.toBeInTheDocument()
    expect((fetchMock.mock.calls as [string][]).map((c) => c[0])).toEqual([
      `${BASE}/professionals/p-1/slots?date=2026-11-09`,
    ])
  })

  it('no ofrece franjas que ya empezaron', async () => {
    vi.setSystemTime(new Date('2026-11-09T14:00:00Z')) // 11:00 local
    api()
    setup()

    expect(await slotButton('11:30–12:00')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '11:00–11:30' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '09:00–09:30' })).not.toBeInTheDocument()
  })

  it('cambiar a otro día vuelve a pedir las franjas de ese día', async () => {
    const fetchMock = api()
    setup()
    await slotButton('09:00–09:30')

    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-10' } })

    expect(await slotButton('10:00–10:30')).toBeInTheDocument()
    const urls = (fetchMock.mock.calls as [string][]).map((c) => c[0])
    expect(urls).toContain(`${BASE}/professionals/p-1/slots?date=2026-11-10`)
  })

  it('un día sin atención o de licencia dice que no hay horarios libres', async () => {
    api()
    setup()
    await slotButton('09:00–09:30')

    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-15' } })

    expect(await screen.findByText('No hay horarios libres este día')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^\d\d:\d\d–/ })).not.toBeInTheDocument()
  })

  it('elegir las 11:00 del martes muestra el resumen y habilita Reprogramar turno', async () => {
    api()
    setup()
    await slotButton('09:00–09:30')
    expect(screen.getByRole('button', { name: 'Reprogramar turno' })).toBeDisabled()

    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-10' } })
    fireEvent.click(await slotButton('11:00–11:30'))

    expect(screen.getByText('Mover de Lun 09/11 10:00 a Mar 10/11 11:00')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reprogramar turno' })).toBeEnabled()
  })

  it('cambiar de día descarta la franja elegida', async () => {
    api()
    setup()
    fireEvent.click(await slotButton('09:00–09:30'))

    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-10' } })

    await slotButton('10:00–10:30')
    expect(screen.queryByText(/^Mover de/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reprogramar turno' })).toBeDisabled()
  })

  it('Volver no envía ningún pedido de escritura', async () => {
    const fetchMock = api()
    const handlers = setup()
    fireEvent.click(await slotButton('09:00–09:30'))

    fireEvent.click(screen.getByRole('button', { name: 'Volver' }))

    expect(handlers.onClose).toHaveBeenCalledTimes(1)
    const writes = fetchMock.mock.calls.filter(
      (c) => ((c[1] as RequestInit | undefined)?.method ?? 'GET') !== 'GET',
    )
    expect(writes).toEqual([])
  })

  it('una falla al pedir las franjas muestra el mensaje', async () => {
    mockApi({
      'GET /professionals/p-1/slots?date=2026-11-09': () =>
        jsonResponse({ error: { code: 'FORBIDDEN', message: 'x' } }, 403),
    })
    setup()

    expect(await screen.findByRole('alert')).toHaveTextContent('No tenés permiso para esta acción')
  })
})

describe('RescheduleDialog: enviar', () => {
  async function chooseTuesday11() {
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-10' } })
    fireEvent.click(await slotButton('11:00–11:30'))
  }

  it('envía un solo POST con el inicio elegido y avisa el nuevo horario', async () => {
    const fetchMock = api({
      [`POST /appointments/${TARGET.id}/reschedule`]: () => jsonResponse(RECORD),
    })
    const handlers = setup()
    await slotButton('09:00–09:30')
    await chooseTuesday11()

    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar turno' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar turno' }))

    await waitFor(() => {
      expect(handlers.onDone).toHaveBeenCalledWith(at(11, 0, 10))
    })
    const posts = fetchMock.mock.calls.filter(
      (c) => (c[1] as RequestInit | undefined)?.method === 'POST',
    )
    expect(posts).toHaveLength(1)
    expect(JSON.parse((posts[0]?.[1] as RequestInit).body as string)).toEqual({
      starts_at: at(11, 0, 10),
    })
  })

  it.each([
    ['SLOT_TAKEN', 'Ese horario se acaba de ocupar. Elegí otro horario'],
    [
      'PATIENT_INACTIVE',
      'El paciente está inactivo: reactivalo desde Pacientes para darle o moverle turnos',
    ],
    ['PROFESSIONAL_TIME_OFF', 'El profesional está de licencia ese día'],
  ])('%s: mensaje, diálogo abierto con lo elegido y recarga', async (code, text) => {
    api({
      [`POST /appointments/${TARGET.id}/reschedule`]: () =>
        jsonResponse({ error: { code, message: 'x' } }, 409),
    })
    const handlers = setup()
    await slotButton('09:00–09:30')
    await chooseTuesday11()

    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(text)
    expect(screen.getByText('Mover de Lun 09/11 10:00 a Mar 10/11 11:00')).toBeInTheDocument()
    expect(handlers.onRejected).toHaveBeenCalledTimes(1)
    expect(handlers.onDone).not.toHaveBeenCalled()
  })
})

describe('RescheduleDialog: tratamiento fijo (C-17)', () => {
  it('muestra el tratamiento del turno como dato y no ofrece cambiarlo', async () => {
    api()
    const target = { ...TARGET, treatment_id: 't-1', treatment_name: 'Extracción' }
    render(
      <RescheduleDialog
        appointment={target}
        role="receptionist"
        onDone={vi.fn()}
        onRejected={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(await screen.findByText('Tratamiento: Extracción')).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('un turno sin tratamiento dice Sin tratamiento y reprogramar no envía treatment_id', async () => {
    const fetchMock = api({
      [`POST /appointments/${TARGET.id}/reschedule`]: () => jsonResponse(RECORD),
    })
    const handlers = setup()
    expect(await screen.findByText('Tratamiento: Sin tratamiento')).toBeInTheDocument()

    fireEvent.click(await slotButton('09:00–09:30'))
    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar turno' }))

    await waitFor(() => {
      expect(handlers.onDone).toHaveBeenCalledTimes(1)
    })
    const post = fetchMock.mock.calls.find(
      (c) => (c[1] as RequestInit | undefined)?.method === 'POST',
    )
    expect(JSON.parse((post?.[1] as RequestInit).body as string)).not.toHaveProperty('treatment_id')
  })
})
