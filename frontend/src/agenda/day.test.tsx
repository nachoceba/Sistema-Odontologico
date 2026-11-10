import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
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

describe('DayColumn con acciones opcionales (C-10)', () => {
  const slots = daySlots(
    [
      [9, 13],
      [14, 18],
    ],
    { busy: ['10:00'] },
  )
  const juan = turno(10, 0, 10, 30, { patient_first_name: 'Juan', patient_last_name: 'Perez' })

  it('con onBookSlot y canBook, la franja libre permitida muestra Agendar y avisa la franja', () => {
    const onBookSlot = vi.fn()
    render(
      <DayColumn
        column={column({ slots, appointments: [juan] })}
        onBookSlot={onBookSlot}
        canBook={(slot) => slot.startsAt === at(9)}
      />,
    )

    const buttons = screen.getAllByRole('button', { name: 'Agendar' })
    expect(buttons).toHaveLength(1)
    fireEvent.click(buttons[0] as HTMLElement)

    expect(onBookSlot).toHaveBeenCalledTimes(1)
    expect(onBookSlot).toHaveBeenCalledWith({ startsAt: at(9), endsAt: at(9, 30) })
  })

  it('canBook en verdadero para todas ofrece Agendar solo en las libres, no en las ocupadas', () => {
    render(
      <DayColumn
        column={column({ slots, appointments: [juan] })}
        onBookSlot={vi.fn()}
        canBook={() => true}
      />,
    )

    expect(screen.getAllByRole('button', { name: 'Agendar' })).toHaveLength(15)
    const busy = screen.getByText('Ocupado').closest('li') as HTMLElement
    expect(within(busy).queryByRole('button', { name: 'Agendar' })).not.toBeInTheDocument()
  })

  it('con onSelectAppointment, el turno es un botón que avisa su id', () => {
    const onSelectAppointment = vi.fn()
    render(
      <DayColumn
        column={column({ slots, appointments: [juan] })}
        onSelectAppointment={onSelectAppointment}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Perez, Juan/ }))

    expect(onSelectAppointment).toHaveBeenCalledWith(juan.id)
    expect(screen.getByText('10:00–10:30 Perez, Juan')).toBeInTheDocument()
  })

  it('los turnos sueltos y cancelados también se pueden elegir', () => {
    const cancelado = turno(11, 0, 11, 30, { status: 'cancelled', patient_last_name: 'Gomez' })
    const suelto = turno(18, 0, 18, 30, { patient_last_name: 'Ruiz' })
    const onSelectAppointment = vi.fn()
    render(
      <DayColumn
        column={column({ slots, appointments: [juan, cancelado, suelto] })}
        onSelectAppointment={onSelectAppointment}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Gomez/ }))
    fireEvent.click(screen.getByRole('button', { name: /Ruiz/ }))

    expect(onSelectAppointment).toHaveBeenNthCalledWith(1, cancelado.id)
    expect(onSelectAppointment).toHaveBeenNthCalledWith(2, suelto.id)
  })

  it('sin esas props no hay ningún botón (comportamiento de C-09)', () => {
    render(<DayColumn column={column({ slots, appointments: [juan] })} />)

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})

describe('DayColumn: tratamiento (C-17, DD-146)', () => {
  const busy = daySlots(
    [
      [9, 13],
      [14, 18],
    ],
    { busy: ['10:00'] },
  )

  it('muestra el tratamiento después del paciente, separado por un punto medio', () => {
    const juan = turno(10, 0, 10, 30, { treatment_id: 't-1', treatment_name: 'Limpieza dental' })
    render(<DayColumn column={column({ slots: busy, appointments: [juan] })} />)

    expect(screen.getByText('10:00–10:30 Perez, Juan')).toBeInTheDocument()
    expect(screen.getByText('· Limpieza dental')).toBeInTheDocument()
    expect(document.body.textContent).toContain('10:00–10:30 Perez, Juan · Limpieza dental')
  })

  it('el nombre completo queda disponible aunque se corte con puntos suspensivos', () => {
    const juan = turno(10, 0, 10, 30, { treatment_id: 't-1', treatment_name: 'Arreglo de caries' })
    render(<DayColumn column={column({ slots: busy, appointments: [juan] })} />)

    const treatment = screen.getByText('· Arreglo de caries')
    expect(treatment).toHaveClass('appointment-treatment')
    expect(treatment).toHaveAttribute('title', 'Arreglo de caries')
  })

  it('un turno sin tratamiento se ve como antes, sin texto ni etiqueta vacía', () => {
    const juan = turno(10, 0, 10, 30)
    const { container } = render(<DayColumn column={column({ slots: busy, appointments: [juan] })} />)

    expect(container.querySelector('.appointment-treatment')).toBeNull()
    expect(document.body.textContent).not.toContain('·')
  })

  it('un turno cancelado conserva el tratamiento dentro de la línea atenuada', () => {
    const cancelado = turno(10, 0, 10, 30, {
      status: 'cancelled',
      treatment_id: 't-2',
      treatment_name: 'Extracción',
    })
    const { container } = render(
      <DayColumn column={column({ slots: busy, appointments: [cancelado] })} />,
    )

    expect(container.querySelector('.appointment--cancelled')).toHaveTextContent(
      'Perez, Juan · Extracción',
    )
  })

  it('en un turno suelto (fila propia) también aparece, y no hay datos de contacto', () => {
    const suelto = turno(18, 0, 18, 30, { treatment_id: 't-3', treatment_name: 'Consulta' })
    render(<DayColumn column={column({ appointments: [suelto] })} />)

    expect(screen.getByText('· Consulta')).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/@|\d{7}/)
  })
})
