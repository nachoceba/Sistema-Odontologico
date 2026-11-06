import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { turno } from '../agenda/fixtures'
import { installAgendaApi } from '../agenda/testApi'
import { DRA } from '../agenda/testApi'
import { jsonResponse } from '../test-utils'
import { DENTIST_A, endSession, open, startSession, world } from './pageHarness'

afterEach(endSession)

async function openDetail() {
  fireEvent.click(await screen.findByRole('button', { name: /10:00–10:30 Perez, Juan/ }))
  await screen.findByRole('heading', { name: 'Lun 09/11 10:00–10:30' })
}

function confirmIn(label: string) {
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: label }))
}

describe('marcar atención', () => {
  it('la Dra. A marca Atendido a las 10:10 tras confirmar y el turno queda sin acciones', async () => {
    startSession('2026-11-09T13:10:00Z') // 10:10 en el consultorio
    const juan = turno(10, 0, 10, 30)
    const api = installAgendaApi(world({ me: DENTIST_A, professionals: [DRA], appointments: [juan] }))
    open('/agenda')
    await openDetail()

    fireEvent.click(screen.getByRole('button', { name: 'Atendido' }))
    expect(
      screen.getByRole('heading', { name: '¿Marcar a Perez, Juan como atendido?' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Después no se puede cambiar')).toBeInTheDocument()
    confirmIn('Atendido')

    expect(await screen.findByText('Asistencia registrada')).toBeInTheDocument()
    expect(api.posts).toEqual([
      { path: `/appointments/${juan.id}/attendance`, body: { status: 'completed' } },
    ])
    expect(await screen.findByText('Atendido')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /10:00–10:30 Perez, Juan/ }))
    await screen.findByRole('heading', { name: 'Lun 09/11 10:00–10:30' })
    expect(screen.queryByRole('button', { name: /^(Atendido|Ausente|Cancelar|Reprogramar)$/ })).toBeNull()
  })

  it('recepción marca Ausente a las 10:40 y se envía no_show', async () => {
    startSession('2026-11-09T13:40:00Z')
    const juan = turno(10, 0, 10, 30)
    const api = installAgendaApi(world({ appointments: [juan] }))
    open('/agenda')
    await openDetail()

    fireEvent.click(screen.getByRole('button', { name: 'Ausente' }))
    expect(
      screen.getByRole('heading', { name: '¿Marcar a Perez, Juan como ausente?' }),
    ).toBeInTheDocument()
    confirmIn('Ausente')

    expect(await screen.findByText('Asistencia registrada')).toBeInTheDocument()
    expect(api.posts[0]?.body).toEqual({ status: 'no_show' })
  })

  it.each([
    ['ATTENDANCE_ALREADY_RECORDED', 'Este turno ya tiene la asistencia registrada'],
    [
      'NOT_STARTED_YET',
      'El turno todavía no empezó: la asistencia se marca desde su hora de inicio',
    ],
  ])('%s: se ve el mensaje y la agenda vuelve a pedirse', async (code, text) => {
    startSession('2026-11-09T13:10:00Z')
    const api = installAgendaApi(
      world({
        me: DENTIST_A,
        professionals: [DRA],
        appointments: [turno(10, 0, 10, 30)],
        override: (method, path) =>
          method === 'POST' && path.endsWith('/attendance')
            ? jsonResponse({ error: { code, message: 'x' } }, 409)
            : undefined,
      }),
    )
    open('/agenda')
    await openDetail()
    fireEvent.click(screen.getByRole('button', { name: 'Atendido' }))
    const before = api.calls.filter((c) => c.startsWith('GET /appointments?')).length

    confirmIn('Atendido')

    expect(await screen.findByRole('alert')).toHaveTextContent(text)
    await waitFor(() => {
      expect(api.calls.filter((c) => c.startsWith('GET /appointments?')).length).toBeGreaterThan(
        before,
      )
    })
  })

  it('cancelar la confirmación no llama a la API y el turno sigue Agendado', async () => {
    startSession('2026-11-09T13:10:00Z')
    const api = installAgendaApi(world({ appointments: [turno(10, 0, 10, 30)] }))
    open('/agenda')
    await openDetail()
    fireEvent.click(screen.getByRole('button', { name: 'Atendido' }))

    confirmIn('Cancelar')

    expect(api.posts).toEqual([])
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByText('Agendado')).toBeInTheDocument()
  })

  it('la odontóloga no ve Agendar, Cancelar ni Reprogramar en ninguna parte', async () => {
    startSession('2026-11-09T13:10:00Z')
    installAgendaApi(
      world({ me: DENTIST_A, professionals: [DRA], appointments: [turno(10, 0, 10, 30)] }),
    )
    open('/agenda')
    await openDetail()

    expect(screen.queryByRole('button', { name: 'Agendar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reprogramar' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Atendido' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ausente' })).toBeInTheDocument()
  })

  it('un doble clic en la confirmación envía un solo pedido', async () => {
    startSession('2026-11-09T13:10:00Z')
    const api = installAgendaApi(world({ appointments: [turno(10, 0, 10, 30)] }))
    open('/agenda')
    await openDetail()
    fireEvent.click(screen.getByRole('button', { name: 'Atendido' }))

    const button = within(screen.getByRole('dialog')).getByRole('button', { name: 'Atendido' })
    fireEvent.click(button)
    fireEvent.click(button)

    await screen.findByText('Asistencia registrada')
    expect(api.posts).toHaveLength(1)
  })
})
