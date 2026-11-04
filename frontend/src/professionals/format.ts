/** Zona del consultorio (SU-01). El frontend no tiene un endpoint de configuración todavía. */
export const CLINIC_TIMEZONE = 'America/Argentina/Buenos_Aires'

export const DAY_NAMES = [
  'Lunes',
  'Martes',
  'Miércoles',
  'Jueves',
  'Viernes',
  'Sábado',
  'Domingo',
] as const

/** `2026-10-12` -> `12/10/2026`, sin pasar por Date para no correr el día por la zona. */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-')
  return `${day ?? ''}/${month ?? ''}/${year ?? ''}`
}

const MOMENT_FORMAT = new Intl.DateTimeFormat('es-AR', {
  timeZone: CLINIC_TIMEZONE,
  weekday: 'short',
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

/** Instante UTC -> `lun 05/10 16:00` en hora local del consultorio (RN-GL-01). */
export function formatLocalMoment(utcInstant: string): string {
  const parts: Record<string, string> = {}
  for (const part of MOMENT_FORMAT.formatToParts(new Date(utcInstant))) {
    parts[part.type] = part.value
  }
  const weekday = (parts.weekday ?? '').replace('.', '')
  return `${weekday} ${parts.day ?? ''}/${parts.month ?? ''} ${parts.hour ?? ''}:${parts.minute ?? ''}`
}
