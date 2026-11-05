import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DayColumn } from './DayColumn'
import { at, daySlots, turno } from './fixtures'
import { buildDayColumn, type DayColumn as DayColumnModel } from './grid'

const DATE = '2026-11-09'

function column(overrides: Partial<Parameters<typeof buildDayColumn>[0]> = {}): DayColumnModel {
  return buildDayColumn({
    date: DATE,
    slots: daySlots([
      [9, 13],
      [14, 18],
    ]),
    appointments: [],
    timeOff: [],
    conflicts: [],
    ...overrides,
  })
}

describe('DayColumn', () => {
  it('muestra Libre, Ocupado con el turno y la banda de fuera de horario como texto', () => {
    const juan = turno(10, 0, 10, 30, { patient_first_name: 'Juan', patient_last_name: 'Perez' })
    render(
      <DayColumn
        column={column({
          slots: daySlots(
            [
              [9, 13],
              [14, 18],
            ],
            { busy: ['10:00'] },
          ),
          appointments: [juan],
        })}
      />,
    )

    expect(screen.getAllByText('Libre')).toHaveLength(15)
    expect(screen.getByText('Ocupado')).toBeInTheDocument()
    expect(screen.getByText('10:00–10:30 Perez, Juan')).toBeInTheDocument()
    expect(screen.getByText('Agendado')).toBeInTheDocument()
    expect(screen.getByText('Fuera de horario 13:00–14:00')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Lun 09/11' })).toBeInTheDocument()
  })

  it('muestra la hora del consultorio y no la UTC', () => {
    render(<DayColumn column={column()} />)
    const items = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(items[0]).toBe('09:00–09:30 Libre')
    expect(items.at(-1)).toBe('17:30–18:00 Libre')
    expect(screen.queryByText(/21:00/)).not.toBeInTheDocument()
  })

  it('un día sin atención lo dice', () => {
    render(<DayColumn column={column({ date: '2026-11-15', slots: daySlots([], { day: 15 }) })} />)
    expect(screen.getByText('Sin atención este día')).toBeInTheDocument()
    expect(screen.queryByText('Libre')).not.toBeInTheDocument()
  })

  it('licencia con y sin motivo', () => {
    const leave = { id: 't', starts_on: DATE, ends_on: DATE, reason: 'Congreso' }
    const { rerender } = render(
      <DayColumn column={column({ slots: daySlots([]), timeOff: [leave] })} />,
    )
    expect(screen.getByText('Licencia: Congreso')).toBeInTheDocument()
    expect(screen.queryByText('Sin atención este día')).not.toBeInTheDocument()

    rerender(
      <DayColumn column={column({ slots: daySlots([]), timeOff: [{ ...leave, reason: null }] })} />,
    )
    expect(screen.getByText('Licencia')).toBeInTheDocument()
  })

  it('un turno cancelado se ve tachado con su etiqueta junto a la franja libre', () => {
    const cancelled = turno(11, 0, 11, 30, {
      status: 'cancelled',
      patient_first_name: 'Ana',
      patient_last_name: 'Gomez',
    })
    render(<DayColumn column={column({ appointments: [cancelled] })} />)

    const label = screen.getByText('Cancelado')
    expect(label).toBeInTheDocument()
    const item = screen.getByText('11:00–11:30 Gomez, Ana').closest('li')
    expect(item).toHaveClass('appointment--cancelled')
    expect(within(item as HTMLElement).getByText('Cancelado')).toBeInTheDocument()
    expect(screen.getAllByText('Libre')).toHaveLength(16)
  })

  it('etiquetas de atendido y ausente', () => {
    render(
      <DayColumn
        column={column({
          appointments: [
            turno(9, 0, 9, 30, { status: 'completed' }),
            turno(9, 30, 10, 0, { status: 'no_show' }),
          ],
        })}
      />,
    )
    expect(screen.getByText('Atendido')).toBeInTheDocument()
    expect(screen.getByText('Ausente')).toBeInTheDocument()
  })

  it('avisa los conflictos con su texto y sin botones', () => {
    const inLeave = turno(10, 0, 10, 30)
    const outside = turno(19, 0, 19, 30)
    const conflict = (appointment: { id: string }, reason: 'TIME_OFF' | 'OUTSIDE_WORKING_HOURS') => ({
      appointment_id: appointment.id,
      patient_id: 'pac-1',
      professional_id: 'p-1',
      starts_at: at(10),
      ends_at: at(10, 30),
      reason,
    })
    render(
      <DayColumn
        column={column({
          appointments: [inLeave, outside],
          conflicts: [conflict(inLeave, 'TIME_OFF'), conflict(outside, 'OUTSIDE_WORKING_HOURS')],
        })}
      />,
    )

    expect(screen.getByText('En conflicto: en licencia')).toBeInTheDocument()
    expect(screen.getByText('En conflicto: fuera del horario')).toBeInTheDocument()
  })

  it('no muestra datos de contacto ni botones de escritura', () => {
    const juan = turno(10, 0, 10, 30)
    const { container } = render(
      <DayColumn column={column({ appointments: [juan] })} />,
    )

    expect(container.textContent).not.toMatch(/@|tel|documento|DNI/i)
    for (const name of [/agendar/i, /cancelar/i, /reprogramar/i, /marcar/i]) {
      expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
    }
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })

  it('en la semana el título del día es un botón que avisa qué día se eligió', () => {
    const picked: string[] = []
    render(
      <DayColumn
        column={column()}
        onSelectDay={(date) => {
          picked.push(date)
        }}
        highlight
      />,
    )

    screen.getByRole('button', { name: 'Lun 09/11' }).click()
    expect(picked).toEqual([DATE])
    expect(screen.getByRole('region', { name: 'Lun 09/11' })).toHaveClass('day-column--today')
  })
})
