import { request } from './users'

export type AppointmentStatus = 'scheduled' | 'completed' | 'no_show' | 'cancelled'
export type SlotStatus = 'FREE' | 'BUSY' | 'OUTSIDE_HOURS'

/** Turno tal como lo devuelve el listado: instantes UTC y nombre vigente del paciente (DD-79). */
export interface Appointment {
  id: string
  patient_id: string
  patient_first_name: string
  patient_last_name: string
  professional_id: string
  starts_at: string
  ends_at: string
  status: AppointmentStatus
  cancel_reason: string | null
  created_by: string
}

/** Franja de un día local del profesional; instantes UTC. */
export interface Slot {
  starts_at: string
  ends_at: string
  status: SlotStatus
}

/** Turnos de un profesional en `[from, to)`, de todos los estados, ordenados por inicio. */
export async function listAppointments(
  professionalId: string,
  fromIso: string,
  toIso: string,
): Promise<Appointment[]> {
  const query =
    `professional_id=${encodeURIComponent(professionalId)}` +
    `&from=${encodeURIComponent(fromIso)}&to=${encodeURIComponent(toIso)}`
  const response = await request(`/appointments?${query}`, 'GET')
  return (await response.json()) as Appointment[]
}

/** Franjas del día local `AAAA-MM-DD` del profesional (de 00:00 a 24:00 del consultorio). */
export async function getDaySlots(professionalId: string, date: string): Promise<Slot[]> {
  const response = await request(
    `/professionals/${encodeURIComponent(professionalId)}/slots?date=${encodeURIComponent(date)}`,
    'GET',
  )
  return (await response.json()) as Slot[]
}
