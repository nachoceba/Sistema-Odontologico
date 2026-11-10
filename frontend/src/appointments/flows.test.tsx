import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { at, turno } from '../agenda/fixtures'
import { installAgendaApi, LIMPIEZA } from '../agenda/testApi'
import { jsonResponse } from '../test-utils'
import { endSession, inRow, open, startSession, world } from './pageHarness'

// Lunes 09/11 a las 12:00 en el consultorio.
beforeEach(() => {
  startSession('2026-11-09T15:00:00Z')
})
afterEach(endSession)

async function pickPatientAndBook() {
  fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar paciente' }), {
    target: { value: 'perez' },
  })
  fireEvent.click(await screen.findByRole('button', { name: 'Perez, Juan' }))
  const select = await screen.findByLabelText('Tratamiento')
  await screen.findByRole('option', { name: 'Limpieza dental' })
  fireEvent.change(select, { target: { value: LIMPIEZA.id } })
  fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }))
}

describe('flujo: agendar', () => {
  it('la franja pasa a Ocupado con el turno y se avisa que se enviará la confirmación sin mostrar el email', async () => {
    const api = installAgendaApi(world())
    open('/agenda')
    await screen.findAllByText('Libre')

    fireEvent.click(inRow('14:00–14:30').getByRole('button', { name: 'Agendar' }))
    expect(await screen.findByRole('heading', { name: 'Lun 09/11 14:00–14:30' })).toBeInTheDocument()
    await pickPatientAndBook()

    expect(await screen.findByText('Turno agendado: Perez, Juan, Lun 09/11 14:00, Limpieza dental. Se enviará la confirmación por email al paciente.')).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('lucia@example.com')
    expect(document.body.textContent).not.toMatch(/@example\.com/)
    expect(await screen.findByText('14:00–14:30 Perez, Juan')).toBeInTheDocument()
    expect(inRow('14:00–14:30').getByText('Ocupado')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Lun 09/11 14:00–14:30' })).not.toBeInTheDocument()
    expect(api.posts).toEqual([
      {
        path: '/appointments',
        body: {
          patient_id: 'pac-1',
          professional_id: 'p-1',
          treatment_id: LIMPIEZA.id,
          starts_at: at(14),
        },
      },
    ])
  })

  it('no ofrece Agendar en franjas que ya empezaron', async () => {
    installAgendaApi(world())
    open('/agenda')
    await screen.findAllByText('Libre')

    expect(inRow('11:30–12:00').queryByRole('button', { name: 'Agendar' })).toBeNull()
    expect(inRow('12:00–12:30').queryByRole('button', { name: 'Agendar' })).toBeNull()
    expect(inRow('12:30–13:00').getByRole('button', { name: 'Agendar' })).toBeInTheDocument()
  })

  it('choque de slot: SLOT_TAKEN en el panel y la franja pasa a Ocupado al recargar', async () => {
    const data = world()
    installAgendaApi({
      ...data,
      override: (method, path) => {
        if (method !== 'POST' || path !== '/appointments') return undefined
        data.appointments.push(turno(14, 0, 14, 30, { patient_last_name: 'Otra', patient_id: 'x' }))
        return jsonResponse({ error: { code: 'SLOT_TAKEN', message: 'x' } }, 409)
      },
    })
    open('/agenda')
    await screen.findAllByText('Libre')

    fireEvent.click(inRow('14:00–14:30').getByRole('button', { name: 'Agendar' }))
    await screen.findByRole('heading', { name: 'Lun 09/11 14:00–14:30' })
    await pickPatientAndBook()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ese horario se acaba de ocupar. Elegí otro horario',
    )
    expect(await screen.findByText('14:00–14:30 Otra, Juan')).toBeInTheDocument()
    expect(inRow('14:00–14:30').getByText('Ocupado')).toBeInTheDocument()
    expect(screen.getByText('Paciente: Perez, Juan')).toBeInTheDocument()
  })
})

describe('flujo: cancelar', () => {
  it('cancelar libera la franja: vuelve Libre con Agendar y el turno queda tachado', async () => {
    const juan = turno(10, 0, 10, 30, {}, 10)
    const api = installAgendaApi(world({ appointments: [juan] }))
    open('/agenda?fecha=2026-11-10')

    fireEvent.click(await screen.findByRole('button', { name: /10:00–10:30 Perez, Juan/ }))
    expect(await screen.findByRole('heading', { name: 'Mar 10/11 10:00–10:30' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    fireEvent.change(screen.getByLabelText('Motivo'), {
      target: { value: 'El paciente avisó por teléfono' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }))

    expect(await screen.findByText('Turno cancelado')).toBeInTheDocument()
    await waitFor(() => {
      expect(inRow('10:00–10:30').getByText('Libre')).toBeInTheDocument()
    })
    expect(inRow('10:00–10:30').getByRole('button', { name: 'Agendar' })).toBeInTheDocument()
    expect(inRow('10:00–10:30').getByText('Cancelado')).toBeInTheDocument()
    expect(api.posts).toEqual([
      { path: `/appointments/${juan.id}/cancel`, body: { reason: 'El paciente avisó por teléfono' } },
    ])
  })

  it('ALREADY_STARTED: mensaje y la agenda se vuelve a pedir con el diálogo abierto', async () => {
    const juan = turno(15, 0, 15, 30)
    const api = installAgendaApi(
      world({
        appointments: [juan],
        override: (method, path) =>
          method === 'POST' && path.endsWith('/cancel')
            ? jsonResponse({ error: { code: 'ALREADY_STARTED', message: 'x' } }, 409)
            : undefined,
      }),
    )
    open('/agenda')
    fireEvent.click(await screen.findByRole('button', { name: /15:00–15:30 Perez, Juan/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar' }))
    fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'Motivo' } })
    const before = api.calls.filter((c) => c.startsWith('GET /appointments?')).length

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('El turno ya empezó')
    await waitFor(() => {
      expect(api.calls.filter((c) => c.startsWith('GET /appointments?')).length).toBeGreaterThan(
        before,
      )
    })
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })
})

describe('flujo: reprogramar', () => {
  it('mueve el turno al martes 11:00 y la franja vieja vuelve a Libre', async () => {
    const juan = turno(15, 0, 15, 30)
    const api = installAgendaApi(world({ appointments: [juan] }))
    open('/agenda')

    fireEvent.click(await screen.findByRole('button', { name: /15:00–15:30 Perez, Juan/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Reprogramar' }))
    await screen.findByRole('button', { name: '12:30–13:00' })
    fireEvent.change(within(screen.getByRole('dialog')).getByLabelText('Fecha'), {
      target: { value: '2026-11-10' },
    })
    fireEvent.click(await screen.findByRole('button', { name: '11:00–11:30' }))
    expect(screen.getByText('Mover de Lun 09/11 15:00 a Mar 10/11 11:00')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar turno' }))

    expect(await screen.findByText('Turno reprogramado: Mar 10/11 11:00. Se enviará la confirmación por email al paciente.')).toBeInTheDocument()
    await waitFor(() => {
      expect(inRow('15:00–15:30').getByText('Libre')).toBeInTheDocument()
    })
    expect(api.posts).toEqual([
      { path: `/appointments/${juan.id}/reschedule`, body: { starts_at: at(11, 0, 10) } },
    ])
  })

  it('un profesional inactivo no ofrece Reprogramar pero sí Cancelar', async () => {
    const inactive = { id: 'p-0', display_name: 'Dr. Zeta Baja', license_number: null, active: false }
    installAgendaApi(
      world({
        professionals: [inactive],
        appointments: [turno(15, 0, 15, 30, { professional_id: 'p-0' })],
      }),
    )
    open('/agenda?profesional=p-0')

    fireEvent.click(await screen.findByRole('button', { name: /15:00–15:30 Perez, Juan/ }))

    expect(await screen.findByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reprogramar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Agendar' })).not.toBeInTheDocument()
  })
})

describe('flujo: semana', () => {
  it('en la vista Semana también se agenda y se abre el detalle', async () => {
    installAgendaApi(world({ appointments: [turno(10, 0, 10, 30, {}, 11)] }))
    open('/agenda?vista=semana&fecha=2026-11-09')
    await screen.findAllByText('Libre')

    fireEvent.click(await screen.findByRole('button', { name: /10:00–10:30 Perez, Juan/ }))
    expect(await screen.findByRole('heading', { name: 'Mié 11/11 10:00–10:30' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Agendar' }).length).toBeGreaterThan(0)
  })
})
