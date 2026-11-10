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

describe('AppointmentDetail: turnos online (DD-133)', () => {
  const PENDIENTE = {
    origin: 'online',
    created_by: null,
    pending_until: '2026-11-09T16:00:00Z',
  } as const
  const ONLY_CANCEL: AppointmentActions = { cancel: true, reschedule: false, markAttendance: false }

  it('un pendiente muestra la hora límite local y solo la acción Cancelar', () => {
    renderDetail(turno(10, 30, 11, 0, PENDIENTE), ONLY_CANCEL)

    expect(screen.getByText('Pendiente de confirmación hasta las 13:00')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Reprogramar|Atendido|Ausente/ })).toBeNull()
  })

  it('para el odontólogo el pendiente se ve sin acciones', () => {
    renderDetail(turno(10, 30, 11, 0, PENDIENTE), NONE)

    expect(screen.getByText('Pendiente de confirmación hasta las 13:00')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Cancelar|Reprogramar|Atendido|Ausente/ })).toBeNull()
  })

  it('un online confirmado muestra "Online" y no el plazo', () => {
    renderDetail(
      turno(10, 30, 11, 0, { origin: 'online', created_by: null, pending_until: null }),
      ALL,
    )

    expect(screen.getByText('Online')).toBeInTheDocument()
    expect(screen.queryByText(/Pendiente de confirmación/)).not.toBeInTheDocument()
  })

  it('un turno de recepción no muestra etiquetas de origen', () => {
    renderDetail(turno(10, 30, 11, 0), ALL)

    expect(screen.queryByText('Online')).not.toBeInTheDocument()
    expect(screen.queryByText(/Pendiente de confirmación/)).not.toBeInTheDocument()
  })
})

describe('AppointmentDetail: tratamiento (C-17)', () => {
  it('muestra la fila Tratamiento con el nombre y ninguna acción para cambiarlo', () => {
    renderDetail(turno(10, 0, 10, 30, { treatment_id: 't-1', treatment_name: 'Extracción' }), ALL)

    expect(screen.getByText('Tratamiento')).toBeInTheDocument()
    expect(screen.getByText('Extracción')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /tratamiento/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('un turno anterior a C-17 dice Sin tratamiento', () => {
    renderDetail(turno(10, 0, 10, 30), ALL)

    expect(screen.getByText('Sin tratamiento')).toBeInTheDocument()
  })

  it('el odontólogo también lo ve, sin acciones', () => {
    renderDetail(turno(10, 0, 10, 30, { treatment_id: 't-2', treatment_name: 'Consulta' }), NONE)

    expect(screen.getByText('Consulta')).toBeInTheDocument()
  })
})
