import { CLINIC_TIMEZONE } from '../professionals/format'

const DAY_ABBREVIATIONS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'] as const
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/

const PARTS_FORMAT = new Intl.DateTimeFormat('en-CA', {
  timeZone: CLINIC_TIMEZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

function partsOf(instant: Date): Record<string, string> {
  const parts: Record<string, string> = {}
  for (const part of PARTS_FORMAT.formatToParts(instant)) parts[part.type] = part.value
  return parts
}

function toUtcMs(isoDate: string): number {
  const match = ISO_DATE.exec(isoDate)
  return Date.UTC(Number(match?.[1]), Number(match?.[2]) - 1, Number(match?.[3]))
}

function fromUtcMs(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10)
}

/** Fecha de hoy (`AAAA-MM-DD`) en el consultorio, sin importar la zona del navegador. */
export function todayInClinic(now: Date): string {
  const parts = partsOf(now)
  return `${parts.year ?? ''}-${parts.month ?? ''}-${parts.day ?? ''}`
}

/** Suma días a una fecha `AAAA-MM-DD` con aritmética en UTC (nunca la zona del navegador). */
export function addDays(isoDate: string, days: number): string {
  return fromUtcMs(toUtcMs(isoDate) + days * 86_400_000)
}

/** Los siete días, de lunes a domingo, de la semana que contiene la fecha. */
export function weekDays(isoDate: string): string[] {
  const weekday = (new Date(toUtcMs(isoDate)).getUTCDay() + 6) % 7 // 0 = lunes
  const monday = addDays(isoDate, -weekday)
  return Array.from({ length: 7 }, (_, index) => addDays(monday, index))
}

/** Devuelve la fecha si es un `AAAA-MM-DD` real del calendario; si no, null. */
export function parseIsoDate(value: string): string | null {
  const match = ISO_DATE.exec(value)
  if (match === null) return null
  return fromUtcMs(toUtcMs(value)) === value ? value : null
}

/** Instante UTC -> `HH:MM` de 24 horas en el consultorio (RN-GL-01). */
export function formatLocalTime(utcInstant: string): string {
  const parts = partsOf(new Date(utcInstant))
  return `${parts.hour ?? ''}:${parts.minute ?? ''}`
}

/** `2026-11-09` -> `Lun 09/11`. */
export function formatDayLabel(isoDate: string): string {
  const weekday = (new Date(toUtcMs(isoDate)).getUTCDay() + 6) % 7
  return `${DAY_ABBREVIATIONS[weekday] ?? ''} ${isoDate.slice(8, 10)}/${isoDate.slice(5, 7)}`
}

/** Fecha local del consultorio (`AAAA-MM-DD`) de un instante UTC. */
export function localDateOf(utcInstant: string): string {
  return todayInClinic(new Date(utcInstant))
}
