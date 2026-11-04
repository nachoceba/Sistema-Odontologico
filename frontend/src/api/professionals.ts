import { request } from './users'

/** Ficha de un profesional; nunca trae datos de la cuenta. */
export interface Professional {
  id: string
  display_name: string
  license_number: string | null
  active: boolean
}

/** Tramo semanal: weekday 0 = lunes a 6 = domingo; horas `HH:MM` locales. */
export interface WorkingBlock {
  weekday: number
  start_time: string
  end_time: string
}

export type ConflictReason = 'OUTSIDE_WORKING_HOURS' | 'TIME_OFF'

/** Turno `scheduled` que quedó fuera del horario o en licencia; instantes en UTC. */
export interface Conflict {
  appointment_id: string
  patient_id: string
  professional_id: string
  starts_at: string
  ends_at: string
  reason: ConflictReason
}

export interface TimeOff {
  id: string
  starts_on: string
  ends_on: string
  reason: string | null
}

export interface TimeOffInput {
  starts_on: string
  ends_on: string
  reason?: string
}

export interface ProfessionalChanges {
  display_name?: string
  /** `null` borra la matrícula; omitirla no la cambia. */
  license_number?: string | null
}

export interface WorkingHoursSaved {
  blocks: WorkingBlock[]
  conflicts: Conflict[]
}

export interface TimeOffSaved {
  time_off: TimeOff
  conflicts: Conflict[]
}

export async function listProfessionals(): Promise<Professional[]> {
  const response = await request('/professionals', 'GET')
  return (await response.json()) as Professional[]
}

export async function getProfessional(id: string): Promise<Professional> {
  const response = await request(`/professionals/${id}`, 'GET')
  return (await response.json()) as Professional
}

export async function updateProfessional(
  id: string,
  changes: ProfessionalChanges,
): Promise<Professional> {
  const response = await request(`/professionals/${id}`, 'PATCH', changes)
  return (await response.json()) as Professional
}

export async function getWorkingHours(id: string): Promise<WorkingBlock[]> {
  const response = await request(`/professionals/${id}/working-hours`, 'GET')
  return ((await response.json()) as { blocks: WorkingBlock[] }).blocks
}

export async function replaceWorkingHours(
  id: string,
  blocks: WorkingBlock[],
): Promise<WorkingHoursSaved> {
  const response = await request(`/professionals/${id}/working-hours`, 'PUT', { blocks })
  return (await response.json()) as WorkingHoursSaved
}

export async function listTimeOff(id: string): Promise<TimeOff[]> {
  const response = await request(`/professionals/${id}/time-off`, 'GET')
  return (await response.json()) as TimeOff[]
}

export async function addTimeOff(id: string, input: TimeOffInput): Promise<TimeOffSaved> {
  const response = await request(`/professionals/${id}/time-off`, 'POST', input)
  return (await response.json()) as TimeOffSaved
}

export async function deleteTimeOff(id: string, timeOffId: string): Promise<void> {
  await request(`/professionals/${id}/time-off/${timeOffId}`, 'DELETE')
}

export async function listConflicts(id: string): Promise<Conflict[]> {
  const response = await request(`/professionals/${id}/conflicts`, 'GET')
  return (await response.json()) as Conflict[]
}
