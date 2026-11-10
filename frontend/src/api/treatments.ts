import { request } from './users'

/** Tratamiento del catálogo (C-17): nombre y estado, sin duración. */
export interface Treatment {
  id: string
  name: string
  active: boolean
}

export interface TreatmentChanges {
  name?: string
  active?: boolean
}

export async function listTreatments(): Promise<Treatment[]> {
  const response = await request('/treatments', 'GET')
  return (await response.json()) as Treatment[]
}

export async function createTreatment(name: string): Promise<Treatment> {
  const response = await request('/treatments', 'POST', { name })
  return (await response.json()) as Treatment
}

export async function updateTreatment(id: string, changes: TreatmentChanges): Promise<Treatment> {
  const response = await request(`/treatments/${encodeURIComponent(id)}`, 'PATCH', changes)
  return (await response.json()) as Treatment
}

/** Tratamientos asignados a un profesional, activos e inactivos, por nombre. */
export async function listProfessionalTreatments(professionalId: string): Promise<Treatment[]> {
  const response = await request(
    `/professionals/${encodeURIComponent(professionalId)}/treatments`,
    'GET',
  )
  return (await response.json()) as Treatment[]
}

/** Reemplaza la asignación completa del profesional. */
export async function replaceProfessionalTreatments(
  professionalId: string,
  treatmentIds: string[],
): Promise<Treatment[]> {
  const response = await request(
    `/professionals/${encodeURIComponent(professionalId)}/treatments`,
    'PUT',
    { treatment_ids: treatmentIds },
  )
  return (await response.json()) as Treatment[]
}
