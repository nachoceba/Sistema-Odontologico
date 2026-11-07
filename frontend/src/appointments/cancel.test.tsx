import { useState } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, saveToken } from '../auth/session'
import { turno } from '../agenda/fixtures'
import { BASE, jsonResponse, mockApi } from '../test-utils'
import { CancelDialog } from './CancelDialog'

const TARGET = turno(10, 0, 10, 30, {}, 10)
const RECORD = { ...TARGET, status: 'cancelled' }

beforeEach(() => {
  vi.stubEnv('VITE_API_URL', BASE)
  saveToken('tok')
})

afterEach(() => {
  clearToken()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

function setup() {
  const handlers = { onDone: vi.fn(), onRejected: vi.fn(), onClose: vi.fn() }
  render(<CancelDialog appointment={TARGET} {...handlers} />)
  return handlers
}

function writeReason(text: string) {
  fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: text } })
}

describe('CancelDialog', () => {
  it('cancelar con motivo envía un solo POST y avisa que terminó', async () => {
    const fetchMock = mockApi({
      [`POST /appointments/${TARGET.id}/cancel`]: () => jsonResponse(RECORD),
    })
    const handlers = setup()

    expect(
      screen.getByRole('heading', { name: 'Cancelar el turno de Perez, Juan del Mar 10/11 10:00' }),
    ).toBeInTheDocument()
    writeReason('El paciente avisó por teléfono')
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }))

    await waitFor(() => {
      expect(handlers.onDone).toHaveBeenCalledTimes(1)
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(JSON.parse((fetchMock.mock.calls[0]?.[1] as RequestInit).body as string)).toEqual({
      reason: 'El paciente avisó por teléfono',
    })
  })

  it.each(['   ', ''])('motivo %j muestra el aviso y no llama a la API', (reason) => {
    const fetchMock = mockApi({})
    setup()

    writeReason(reason)
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }))

    expect(screen.getByText('Escribí el motivo de la cancelación')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('el campo se limita a 500 caracteres', () => {
    setup()
    expect(screen.getByLabelText('Motivo')).toHaveAttribute('maxlength', '500')
  })

  it.each([
    ['ALREADY_STARTED', 'El turno ya empezó: no se puede cancelar ni reprogramar'],
    ['CANCELLED_IS_FINAL', 'El turno ya estaba cancelado'],
  ])('%s muestra su mensaje, pide recargar y deja el diálogo abierto', async (code, text) => {
    mockApi({
      [`POST /appointments/${TARGET.id}/cancel`]: () =>
        jsonResponse({ error: { code, message: 'x' } }, 409),
    })
    const handlers = setup()

    writeReason('Motivo')
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(text)
    expect(handlers.onRejected).toHaveBeenCalledTimes(1)
    expect(handlers.onDone).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Motivo')).toHaveValue('Motivo')
  })

  it('un 403 muestra el aviso de permiso sin pedir recarga', async () => {
    mockApi({
      [`POST /appointments/${TARGET.id}/cancel`]: () =>
        jsonResponse({ error: { code: 'FORBIDDEN', message: 'x' } }, 403),
    })
    const handlers = setup()

    writeReason('Motivo')
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No tenés permiso para esta acción')
    expect(handlers.onRejected).not.toHaveBeenCalled()
  })

  it('Volver cierra sin llamar a la API y Escape también', () => {
    const fetchMock = mockApi({})
    const handlers = setup()

    fireEvent.click(screen.getByRole('button', { name: 'Volver' }))
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })

    expect(handlers.onClose).toHaveBeenCalledTimes(2)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('un doble clic envía un solo pedido', async () => {
    const fetchMock = mockApi({
      [`POST /appointments/${TARGET.id}/cancel`]: () => jsonResponse(RECORD),
    })
    const handlers = setup()

    writeReason('Motivo')
    const button = screen.getByRole('button', { name: 'Cancelar turno' })
    fireEvent.click(button)
    fireEvent.click(button)

    await waitFor(() => {
      expect(handlers.onDone).toHaveBeenCalledTimes(1)
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('el motivo se envía recortado', async () => {
    const fetchMock = mockApi({
      [`POST /appointments/${TARGET.id}/cancel`]: () => jsonResponse(RECORD),
    })
    setup()

    writeReason('  Licencia  ')
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
    expect(JSON.parse((fetchMock.mock.calls[0]?.[1] as RequestInit).body as string)).toEqual({
      reason: 'Licencia',
    })
  })
})

function Harness() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true)
        }}
      >
        Abrir
      </button>
      {open ? (
        <CancelDialog
          appointment={TARGET}
          onDone={() => undefined}
          onRejected={() => undefined}
          onClose={() => {
            setOpen(false)
          }}
        />
      ) : null}
    </>
  )
}

describe('CancelDialog: foco dentro del diálogo (P-11)', () => {
  it('Tab desde el último botón vuelve al primer elemento del diálogo', () => {
    setup()
    const dialog = screen.getByRole('dialog')
    const last = screen.getByRole('button', { name: 'Volver' })
    last.focus()

    fireEvent.keyDown(last, { key: 'Tab' })

    expect(document.activeElement).toBe(screen.getByLabelText('Motivo'))
    expect(dialog).toContainElement(document.activeElement as HTMLElement)
  })

  it('Shift+Tab desde el primer elemento va al último botón', () => {
    setup()
    const first = screen.getByLabelText('Motivo')
    first.focus()

    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true })

    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Volver' }))
  })

  it('Tab entre elementos del medio no se desvía: lo resuelve el navegador', () => {
    setup()
    const middle = screen.getByRole('button', { name: 'Cancelar turno' })
    middle.focus()

    const notPrevented = fireEvent.keyDown(middle, { key: 'Tab' })

    expect(notPrevented).toBe(true)
    expect(document.activeElement).toBe(middle)
  })

  it('al cerrar con Escape el foco vuelve al botón que abrió el diálogo', () => {
    render(<Harness />)
    const opener = screen.getByRole('button', { name: 'Abrir' })
    opener.focus()
    fireEvent.click(opener)
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(document.activeElement).toBe(opener)
  })

  it('al cerrar con "Volver" el foco también vuelve al botón que abrió el diálogo', () => {
    render(<Harness />)
    const opener = screen.getByRole('button', { name: 'Abrir' })
    opener.focus()
    fireEvent.click(opener)

    fireEvent.click(screen.getByRole('button', { name: 'Volver' }))

    expect(document.activeElement).toBe(opener)
  })
})
