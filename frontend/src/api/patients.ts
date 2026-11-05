import { request } from './users'

/** Ficha de un paciente tal como la devuelve la API (documento ya normalizado). */
export interface Patient {
  id: string
  first_name: string
  last_name: string
  document_number: string
  email: string
  phone: string | null
  /** `AAAA-MM-DD` o null. */
  birth_date: string | null
  active: boolean
}

export interface PatientSearchResult {
  items: Patient[]
  truncated: boolean
}

export interface NewPatientInput {
  first_name: string
  last_name: string
  document_number: string
  email: string
  phone?: string
  birth_date?: string
}

/** Campo ausente = no cambia; `phone` y `birth_date` en `null` lo borran. */
export interface PatientChanges {
  first_name?: string
  last_name?: string
  document_number?: string
  email?: string
  phone?: string | null
  birth_date?: string | null
}

/** Turno `scheduled` futuro de un paciente recién desactivado; instantes en UTC. */
export interface UpcomingAppointment {
  id: string
  professional_id: string
  starts_at: string
  ends_at: string
  status: string
}

export interface Deactivation {
  patient: Patient
  upcoming_appointments: UpcomingAppointment[]
}

export interface SearchParams {
  q?: string
  includeInactive?: boolean
}

export async function searchPatients({
  q,
  includeInactive = false,
}: SearchParams = {}): Promise<PatientSearchResult> {
  const query = new URLSearchParams()
  const text = q?.trim() ?? ''
  if (text !== '') query.set('q', text)
  if (includeInactive) query.set('include_inactive', 'true')
  const suffix = query.size === 0 ? '' : `?${query.toString()}`
  const response = await request(`/patients${suffix}`, 'GET')
  return (await response.json()) as PatientSearchResult
}

export async function getPatient(id: string): Promise<Patient> {
  const response = await request(`/patients/${id}`, 'GET')
  return (await response.json()) as Patient
}

export async function createPatient(input: NewPatientInput): Promise<Patient> {
  const response = await request('/patients', 'POST', input)
  return (await response.json()) as Patient
}

export async function updatePatient(id: string, changes: PatientChanges): Promise<Patient> {
  const response = await request(`/patients/${id}`, 'PATCH', changes)
  return (await response.json()) as Patient
}

export async function deactivatePatient(id: string): Promise<Deactivation> {
  const response = await request(`/patients/${id}/deactivate`, 'POST')
  return (await response.json()) as Deactivation
}

export async function reactivatePatient(id: string): Promise<Patient> {
  const response = await request(`/patients/${id}/reactivate`, 'POST')
  return (await response.json()) as Patient
}

export async function deletePatient(id: string): Promise<void> {
  await request(`/patients/${id}`, 'DELETE')
}
