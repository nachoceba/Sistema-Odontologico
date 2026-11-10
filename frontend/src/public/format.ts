import { formatLocalTime, localDateOf } from '../agenda/dates'

const WEEKDAYS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'] as const

/** Instante UTC -> `lunes 09/11/2026, 10:30` en la zona del consultorio (RN-GL-01). */
export function longDayAndTime(utcInstant: string): string {
  const date = localDateOf(utcInstant) // AAAA-MM-DD
  const [year, month, day] = date.split('-')
  const weekday = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day))).getUTCDay()
  return `${WEEKDAYS[weekday] ?? ''} ${day ?? ''}/${month ?? ''}/${year ?? ''}, ${formatLocalTime(utcInstant)}`
}
