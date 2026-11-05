import { describe, expect, it } from 'vitest'
import {
  addDays,
  formatDayLabel,
  formatLocalTime,
  parseIsoDate,
  todayInClinic,
  weekDays,
} from './dates'

describe('todayInClinic', () => {
  it.each([
    ['2026-11-10T01:00:00Z', '2026-11-09'], // 22:00 del lunes en el consultorio
    ['2026-11-10T03:00:00Z', '2026-11-10'], // medianoche local
    ['2026-11-10T02:59:59Z', '2026-11-09'],
    ['2026-01-01T02:00:00Z', '2025-12-31'],
  ])('%s -> %s', (instant, expected) => {
    expect(todayInClinic(new Date(instant))).toBe(expected)
  })
})

describe('addDays', () => {
  it.each([
    ['2026-11-30', 1, '2026-12-01'],
    ['2026-12-31', 1, '2027-01-01'],
    ['2026-03-01', -1, '2026-02-28'],
    ['2028-02-28', 1, '2028-02-29'],
    ['2026-11-09', 7, '2026-11-16'],
    ['2026-11-09', 0, '2026-11-09'],
  ])('%s %i -> %s', (date, n, expected) => {
    expect(addDays(date, n)).toBe(expected)
  })
})

describe('weekDays', () => {
  it('un jueves da lunes a domingo de su semana', () => {
    expect(weekDays('2026-11-12')).toEqual([
      '2026-11-09',
      '2026-11-10',
      '2026-11-11',
      '2026-11-12',
      '2026-11-13',
      '2026-11-14',
      '2026-11-15',
    ])
  })

  it('un domingo pertenece a la semana que termina en él', () => {
    const days = weekDays('2026-11-15')
    expect(days[0]).toBe('2026-11-09')
    expect(days[6]).toBe('2026-11-15')
  })

  it('un lunes abre su propia semana, cruzando el fin de año', () => {
    expect(weekDays('2026-12-28')[6]).toBe('2027-01-03')
    expect(weekDays('2026-12-28')[0]).toBe('2026-12-28')
  })
})

describe('parseIsoDate', () => {
  it.each(['2026-02-30', '2026-13-01', '2026-11-9', 'hoy', '', '2026-11-09T10:00'])(
    '%s es inválida',
    (value) => {
      expect(parseIsoDate(value)).toBeNull()
    },
  )

  it.each(['2026-11-09', '2028-02-29', '2026-12-31'])('%s es válida', (value) => {
    expect(parseIsoDate(value)).toBe(value)
  })

  it('29 de febrero de un año no bisiesto es inválida', () => {
    expect(parseIsoDate('2027-02-29')).toBeNull()
  })
})

describe('formatLocalTime', () => {
  it.each([
    ['2026-11-09T12:00:00Z', '09:00'],
    ['2026-11-10T03:00:00Z', '00:00'],
    ['2026-11-09T22:45:00Z', '19:45'],
  ])('%s -> %s', (instant, expected) => {
    expect(formatLocalTime(instant)).toBe(expected)
  })
})

describe('formatDayLabel', () => {
  it.each([
    ['2026-11-09', 'Lun 09/11'],
    ['2026-11-15', 'Dom 15/11'],
    ['2026-12-31', 'Jue 31/12'],
  ])('%s -> %s', (date, expected) => {
    expect(formatDayLabel(date)).toBe(expected)
  })
})
