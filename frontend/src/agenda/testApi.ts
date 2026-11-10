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
  /** Pacientes activos que devuelve la búsqueda (`GET /patients?q=`). */
  patients?: { id: string; first_name: string; last_name: string }[]
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
  /** Cuerpos JSON de los pedidos `POST`, en orden, con su ruta. */
  posts: { path: string; body: Record<string, unknown> }[]
}

const SLOT_MS = 30 * 60_000

function error(status: number, code: string): Response {
  return jsonResponse({ error: { code, message: 'x' } }, status)
}

/** Escrituras simuladas sobre el mundo: agendar, cancelar, reprogramar y marcar asistencia. */
function write(
  world: AgendaWorld,
  pathname: string,
  body: Record<string, unknown>,
): Response | undefined {
  if (pathname === '/appointments') {
    const startsAt = String(body.starts_at)
    const taken = world.appointments.some(
      (a) =>
        a.professional_id === body.professional_id &&
        a.status === 'scheduled' &&
        a.starts_at === startsAt,
    )
    if (taken) return error(409, 'SLOT_TAKEN')
    const patient = world.patients?.find((p) => p.id === body.patient_id)
    const created: Appointment = {
      id: `new-${String(world.appointments.length + 1)}`,
      patient_id: String(body.patient_id),
      patient_first_name: patient?.first_name ?? 'Juan',
      patient_last_name: patient?.last_name ?? 'Perez',
      professional_id: String(body.professional_id),
      starts_at: startsAt,
      ends_at: new Date(Date.parse(startsAt) + SLOT_MS).toISOString().replace('.000Z', 'Z'),
      status: 'scheduled',
      cancel_reason: null,
      created_by: 'u-rec',
      origin: 'staff',
      pending_until: null,
    }
    world.appointments.push(created)
    return jsonResponse(created, 201)
  }
  const match = /^\/appointments\/([^/]+)\/(cancel|reschedule|attendance)$/.exec(pathname)
  const target = world.appointments.find((a) => a.id === match?.[1])
  if (match === null || target === undefined) return undefined
  if (match[2] === 'cancel') {
    target.status = 'cancelled'
    target.cancel_reason = String(body.reason)
  } else if (match[2] === 'reschedule') {
    target.starts_at = String(body.starts_at)
    target.ends_at = new Date(Date.parse(target.starts_at) + SLOT_MS)
      .toISOString()
      .replace('.000Z', 'Z')
  } else {
    target.status = body.status === 'completed' ? 'completed' : 'no_show'
  }
  // Un turno cancelado o movido deja de estar en conflicto.
  world.conflicts = world.conflicts.filter((c) => c.appointment_id !== target.id)
  return jsonResponse(target)
}

export function installAgendaApi(world: AgendaWorld): InstalledApi {
  const calls: string[] = []
  const posts: InstalledApi['posts'] = []
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
      if (method === 'POST') {
        const body = JSON.parse(typeof init?.body === 'string' ? init.body : '{}') as Record<
          string,
          unknown
        >
        posts.push({ path: url.pathname, body })
        const written = write(world, url.pathname, body)
        if (written !== undefined) return Promise.resolve(written)
      }
      const oneMatch = /^\/appointments\/([^/]+)$/.exec(url.pathname)
      if (method === 'GET' && oneMatch !== null) {
        const found = world.appointments.find((a) => a.id === oneMatch[1])
        return Promise.resolve(found === undefined ? error(404, 'APPOINTMENT_NOT_FOUND') : jsonResponse(found))
      }
      if (method === 'GET' && url.pathname === '/patients') {
        const q = (url.searchParams.get('q') ?? '').toLowerCase()
        const items = (world.patients ?? []).filter((p) => p.last_name.toLowerCase().includes(q))
        return Promise.resolve(jsonResponse({ items, truncated: false }))
      }
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
  return { calls, posts }
}
