import { vi } from 'vitest'
import type { Appointment, Slot } from '../api/appointments'
import type { Conflict, Professional, TimeOff } from '../api/professionals'
import { BASE, jsonResponse } from '../test-utils'
import { daySlots } from './fixtures'

/** Datos de la API simulada para las pantallas de agenda; se pueden cambiar entre pedidos. */
export interface AgendaWorld {
  me: Record<string, unknown>
  professionals: Professional[]
  appointments: Appointment[]
  timeOff: TimeOff[]
  conflicts: Conflict[]
  /** Si devuelve una respuesta, reemplaza a la normal del pedido. */
  override?: (method: string, path: string) => Response | Promise<Response> | undefined
}

export const DRA: Professional = {
  id: 'p-1',
  display_name: 'Dra. Ana Álvarez',
  license_number: 'MAT-0001',
  active: true,
}
export const DR_B: Professional = {
  id: 'p-2',
  display_name: 'Dr. Bruno Benítez',
  license_number: null,
  active: true,
}

/** Lunes a viernes de 09:00 a 13:00 y de 14:00 a 18:00; sábado y domingo sin atención (noviembre 2026). */
function slotsFor(world: AgendaWorld, professionalId: string, date: string): Slot[] {
  const day = Number(date.slice(8, 10))
  const weekday = (new Date(`${date}T00:00:00Z`).getUTCDay() + 6) % 7
  if (weekday > 4) return daySlots([], { day })
  const busy = world.appointments
    .filter((a) => a.professional_id === professionalId && a.status === 'scheduled')
    .map((a) => new Date(Date.parse(a.starts_at) - 3 * 3_600_000))
    .filter((d) => d.getUTCDate() === day)
    .map(
      (d) =>
        `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`,
    )
  return daySlots(
    [
      [9, 13],
      [14, 18],
    ],
    { day, busy },
  )
}

export interface InstalledApi {
  /** Cada pedido como `GET /ruta?consulta`, sin el prefijo de la API. */
  calls: string[]
}

export function installAgendaApi(world: AgendaWorld): InstalledApi {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
      const path = raw.replace(BASE, '')
      const method = (init?.method ?? 'GET').toUpperCase()
      calls.push(`${method} ${path}`)
      const overridden = world.override?.(method, path)
      if (overridden !== undefined) return Promise.resolve(overridden)

      const url = new URL(path, 'http://x')
      const slotMatch = /^\/professionals\/([^/]+)\/slots$/.exec(url.pathname)
      const timeOffMatch = /^\/professionals\/([^/]+)\/time-off$/.exec(url.pathname)
      const conflictMatch = /^\/professionals\/([^/]+)\/conflicts$/.exec(url.pathname)
      if (url.pathname === '/auth/me') return Promise.resolve(jsonResponse(world.me))
      if (url.pathname === '/professionals') return Promise.resolve(jsonResponse(world.professionals))
      if (slotMatch?.[1] !== undefined)
        return Promise.resolve(
          jsonResponse(slotsFor(world, slotMatch[1], url.searchParams.get('date') ?? '')),
        )
      if (timeOffMatch !== null) return Promise.resolve(jsonResponse(world.timeOff))
      if (conflictMatch !== null) return Promise.resolve(jsonResponse(world.conflicts))
      if (url.pathname === '/appointments') {
        const id = url.searchParams.get('professional_id')
        const from = Date.parse(url.searchParams.get('from') ?? '')
        const to = Date.parse(url.searchParams.get('to') ?? '')
        return Promise.resolve(
          jsonResponse(
            world.appointments.filter(
              (a) =>
                a.professional_id === id && Date.parse(a.ends_at) > from && Date.parse(a.starts_at) < to,
            ),
          ),
        )
      }
      return Promise.reject(new TypeError(`sin handler: ${method} ${path}`))
    }),
  )
  return { calls }
}
