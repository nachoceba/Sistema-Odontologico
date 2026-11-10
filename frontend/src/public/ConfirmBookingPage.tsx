import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { confirmOnlineBooking, type OnlineConfirmation } from '../api/publicBooking'
import { longDayAndTime } from './format'
import { confirmFailure } from './messages'
import { PublicLayout } from './PublicLayout'

function tokenFromHash(hash: string): string | null {
  const token = new URLSearchParams(hash.replace(/^#/, '')).get('token')
  return token === null || token === '' ? null : token
}

type View =
  | { kind: 'ready'; error: string | null }
  | { kind: 'done'; booking: OnlineConfirmation }
  | { kind: 'invalid' }

function Title({ children }: { children: string }) {
  const title = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    title.current?.focus()
  }, [])
  return (
    <h1 ref={title} tabIndex={-1}>
      {children}
    </h1>
  )
}

/**
 * Confirma la reserva con el token del enlace del email (`#token=...`). Abrir la página no hace
 * ningún pedido: el `POST` sale solo con el botón, así un previsualizador de correo no confirma.
 */
export default function ConfirmBookingPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [token] = useState(() => tokenFromHash(location.hash))
  const [view, setView] = useState<View>(
    token === null ? { kind: 'invalid' } : { kind: 'ready', error: null },
  )
  const [sending, setSending] = useState(false)
  // La ref bloquea el segundo clic incluso antes de que React re-renderice el botón.
  const inFlight = useRef(false)

  async function confirm() {
    if (inFlight.current || token === null) return
    inFlight.current = true
    setSending(true)
    try {
      const booking = await confirmOnlineBooking(token)
      clearFragment()
      setView({ kind: 'done', booking })
    } catch (failure) {
      clearFragment()
      const result = confirmFailure(failure)
      setView(
        result.kind === 'invalid' ? { kind: 'invalid' } : { kind: 'ready', error: result.message },
      )
    } finally {
      inFlight.current = false
      setSending(false)
    }
  }

  /** El token no se queda en la dirección ni en el historial después del intento. */
  function clearFragment() {
    void navigate({ pathname: location.pathname, hash: '' }, { replace: true })
  }

  if (view.kind === 'invalid') {
    return (
      <PublicLayout>
        <section className="public-card">
          <Title>Enlace no válido</Title>
          <p>
            El enlace no es válido, ya se usó o venció. Si todavía quiere el turno, vuelva a
            reservarlo.
          </p>
          <Link to="/turnos">Reservar un turno</Link>
        </section>
      </PublicLayout>
    )
  }

  if (view.kind === 'done') {
    return (
      <PublicLayout>
        <section className="public-card">
          <Title>Turno confirmado</Title>
          <p>Su turno quedó confirmado. Le enviamos la confirmación por email.</p>
          <dl className="detail-list">
            <dt>Profesional</dt>
            <dd>{view.booking.professional_display_name}</dd>
            {view.booking.treatment_name === null ? null : (
              <>
                <dt>Tratamiento</dt>
                <dd>{view.booking.treatment_name}</dd>
              </>
            )}
            <dt>Día y hora</dt>
            <dd>{longDayAndTime(view.booking.starts_at)}</dd>
          </dl>
        </section>
      </PublicLayout>
    )
  }

  return (
    <PublicLayout>
      <section className="public-card">
        <h1>Confirmar su turno</h1>
        <p>Toque el botón para dejar confirmado el turno que reservó.</p>
        {view.error === null ? null : <p role="alert">{view.error}</p>}
        <button
          type="button"
          disabled={sending}
          onClick={() => {
            void confirm()
          }}
        >
          Confirmar mi turno
        </button>
      </section>
    </PublicLayout>
  )
}
