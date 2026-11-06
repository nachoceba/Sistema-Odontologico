import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { at, daySlots, turno } from './fixtures'
import { buildDayColumn } from './grid'
import { WeekView } from './WeekView'

function columnFor(day: number, withTurno: boolean) {
  const date = `2026-11-${String(day).padStart(2, '0')}`
  const appointment = turno(10, 0, 10, 30, { patient_last_name: `Dia${String(day)}` }, day)
  return buildDayColumn({
    date,
    slots: daySlots([[9, 11]], { day, busy: withTurno ? ['10:00'] : [] }),
    appointments: withTurno ? [appointment] : [],
    timeOff: [],
    conflicts: [],
  })
}

describe('WeekView con acciones opcionales', () => {
  it('pasa agendar y elegir turno a cada día', () => {
    const onBookSlot = vi.fn()
    const onSelectAppointment = vi.fn()
    render(
      <WeekView
        columns={[columnFor(9, false), columnFor(10, true)]}
        today="2026-11-09"
        onSelectDay={vi.fn()}
        onBookSlot={onBookSlot}
        canBook={() => true}
        onSelectAppointment={onSelectAppointment}
      />,
    )

    fireEvent.click(screen.getAllByRole('button', { name: 'Agendar' })[0] as HTMLElement)
    fireEvent.click(screen.getByRole('button', { name: /Dia10/ }))

    expect(onBookSlot).toHaveBeenCalledWith({ startsAt: at(9, 0, 9), endsAt: at(9, 30, 9) })
    expect(onSelectAppointment).toHaveBeenCalledTimes(1)
  })

  it('sin acciones solo quedan los botones de día', () => {
    render(
      <WeekView
        columns={[columnFor(9, false), columnFor(10, true)]}
        today="2026-11-09"
        onSelectDay={vi.fn()}
      />,
    )

    expect(screen.getAllByRole('button')).toHaveLength(2)
  })
})
