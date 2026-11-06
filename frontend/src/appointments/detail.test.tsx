import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Appointment } from '../api/appointments'
import { at, turno } from '../agenda/fixtures'
import { AppointmentDetail } from './AppointmentDetail'
import type { AppointmentActions } from './actions'

const ALL: AppointmentActions = { cancel: true, reschedule: true, markAttendance: false }
const NONE: AppointmentActions = { cancel: false, reschedule: false, markAttendance: false }

function renderDetail(
  appointment: Appointment,
  actions: AppointmentActions,
  extra: { conflict?: 'TIME_OFF' | 'OUTSIDE_WORKING_HOURS' | null } = {},
) {
  const handlers = {
    onCancel: vi.fn(),
    onReschedule: vi.fn(),
    onAttendance: vi.fn(),
    onClose: vi.fn(),
  }
  render(
    <AppointmentDetail
      appointment={appointment}
      professionalName="Dra. Ana Álvarez"
      conflict={extra.conflict ?? null}
      actions={actions}
      {...handlers}
    />,
  )
  return handlers
}

describe('AppointmentDetail', () => {
  it('muestra fecha y hora local, paciente, profesional, estado y las acciones', () => {
    const handlers = renderDetail(turno(10, 0, 10, 30, {}, 10), ALL)

    expect(screen.getByRole('heading', { name: 'Mar 10/11 10:00–10:30' })).toBeInTheDocument()
    expect(screen.getByText('Perez, Juan')).toBeInTheDocument()
    expect(screen.getByText('Dra. Ana Álvarez')).toBeInTheDocument()
    expect(screen.getByText('Agendado')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar' }))
    expect(handlers.onCancel).toHaveBeenCalledTimes(1)
    expect(handlers.onReschedule).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: 'Atendido' })).not.toBeInTheDocument()
  })

  it('un turno cancelado muestra su motivo y no ofrece acciones', () => {
    renderDetail(
      turno(10, 0, 10, 30, { status: 'cancelled', cancel_reason: 'El paciente avisó por teléfono' }),
      NONE,
    )

    expect(screen.getByText('Cancelado')).toBeInTheDocument()
    expect(screen.getByText('Motivo: El paciente avisó por teléfono')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Cancelar|Reprogramar|Atendido|Ausente/ })).toBeNull()
  })

  it('un turno iniciado ofrece Atendido y Ausente con su estado', () => {
    const handlers = renderDetail(turno(10, 0, 10, 30), {
      cancel: false,
      reschedule: false,
      markAttendance: true,
    })

    fireEvent.click(screen.getByRole('button', { name: 'Atendido' }))
    fireEvent.click(screen.getByRole('button', { name: 'Ausente' }))

    expect(handlers.onAttendance).toHaveBeenNthCalledWith(1, 'completed')
    expect(handlers.onAttendance).toHaveBeenNthCalledWith(2, 'no_show')
  })

  it('un turno en conflicto muestra su aviso', () => {
    renderDetail(turno(10, 0, 10, 30, {}, 12), ALL, { conflict: 'TIME_OFF' })
    expect(screen.getByText('En conflicto: en licencia')).toBeInTheDocument()
  })

  it('el aviso de fuera de horario se distingue del de licencia', () => {
    renderDetail(turno(17, 30, 18, 0), ALL, { conflict: 'OUTSIDE_WORKING_HOURS' })
    expect(screen.getByText('En conflicto: fuera del horario')).toBeInTheDocument()
  })

  it('no muestra email, teléfono ni documento y abrirlo no escribe', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    renderDetail(
      { ...turno(10, 0, 10, 30), starts_at: at(10), ends_at: at(10, 30) },
      ALL,
    )

    expect(document.body.textContent).not.toMatch(/@|tel|documento|DNI/i)
    expect(fetchMock).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it('Cerrar avisa y Escape también', () => {
    const handlers = renderDetail(turno(10, 0, 10, 30), ALL)

    fireEvent.click(screen.getByRole('button', { name: 'Cerrar' }))
    fireEvent.keyDown(screen.getByRole('complementary'), { key: 'Escape' })

    expect(handlers.onClose).toHaveBeenCalledTimes(2)
  })
})
