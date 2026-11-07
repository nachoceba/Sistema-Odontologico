import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DateNavigator } from './DateNavigator'
import { DayColumn } from './DayColumn'
import { daySlots } from './fixtures'
import { buildDayColumn } from './grid'

function renderNavigator(view: 'dia' | 'semana' = 'dia') {
  const handlers = {
    onPrevious: vi.fn(),
    onNext: vi.fn(),
    onToday: vi.fn(),
    onDate: vi.fn(),
    onView: vi.fn(),
    onRefresh: vi.fn(),
  }
  render(<DateNavigator date="2026-11-09" view={view} {...handlers} />)
  return handlers
}

describe('barra de la agenda agrupada', () => {
  it('agrupa la navegación por fecha y la elección de vista con nombre propio', () => {
    renderNavigator()

    const dates = screen.getByRole('group', { name: 'Navegar' })
    expect(within(dates).getByRole('button', { name: 'Anterior' })).toBeInTheDocument()
    expect(within(dates).getByRole('button', { name: 'Hoy' })).toBeInTheDocument()
    expect(within(dates).getByRole('button', { name: 'Siguiente' })).toBeInTheDocument()
    expect(within(dates).getByLabelText('Fecha')).toHaveValue('2026-11-09')

    const views = screen.getByRole('group', { name: 'Vista' })
    expect(within(views).getByRole('button', { name: 'Día' })).toHaveAttribute('aria-pressed', 'true')
    expect(within(views).getByRole('button', { name: 'Semana' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })

  it('los grupos usan la clase de agrupación y los botones conservan su comportamiento', () => {
    const handlers = renderNavigator('semana')

    expect(screen.getByRole('group', { name: 'Navegar' })).toHaveClass('toolbar-group')
    expect(screen.getByRole('group', { name: 'Vista' })).toHaveClass('toolbar-group')
    expect(screen.getByRole('button', { name: 'Semana' })).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(screen.getByRole('button', { name: 'Día' }))
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Hoy' }))
    expect(handlers.onView).toHaveBeenCalledWith('dia')
    expect(handlers.onRefresh).toHaveBeenCalledTimes(1)
    expect(handlers.onToday).toHaveBeenCalledTimes(1)
  })
})

describe('objetivos mínimos en la grilla', () => {
  const css = readFileSync(join(process.cwd(), 'src', 'styles.css'), 'utf8')
  const rule = /button\.book-button,\s*button\.appointment-button\s*\{([^}]*)\}/.exec(css)?.[1] ?? ''

  it('"Agendar" y los turnos llevan la clase de objetivo mínimo y la hoja pide 24 px o más', () => {
    const column = buildDayColumn({
      date: '2026-11-09',
      slots: daySlots([[9, 10]]),
      appointments: [],
      timeOff: [],
      conflicts: [],
    })
    render(
      <DayColumn
        column={column}
        onBookSlot={vi.fn()}
        canBook={() => true}
      />,
    )

    const book = screen.getAllByRole('button', { name: 'Agendar' })[0]
    expect(book).toHaveClass('book-button')
    expect(Number.parseFloat(/min-width:\s*([\d.]+)rem/.exec(rule)?.[1] ?? '0')).toBeGreaterThanOrEqual(1.5)
    expect(Number.parseFloat(/min-height:\s*([\d.]+)rem/.exec(rule)?.[1] ?? '0')).toBeGreaterThanOrEqual(1.5)
  })
})
