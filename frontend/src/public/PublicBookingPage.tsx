import { useEffect, useRef, useState, type SyntheticEvent } from 'react'
import { addDays, formatDayLabel, formatLocalTime, todayInClinic } from '../agenda/dates'
import {
  bookOnline,
  getPublicSlots,
  listPublicProfessionals,
  type PublicProfessional,
  type PublicSlot,
} from '../api/publicBooking'
import { LoadingNotice } from '../ui/Notices'
import { longDayAndTime } from './format'
import {
  NO_PROFESSIONALS_MESSAGE,
  NO_SLOTS_MESSAGE,
  PROFESSIONALS_FAILED_MESSAGE,
  SLOTS_FAILED_MESSAGE,
  lostTheSlot,
  messageForBooking,
} from './messages'
import { PublicLayout } from './PublicLayout'
import { useRemote } from './useRemote'

const HORIZON_DAYS = 14 // hoy y los 13 días siguientes (P-4)

interface FormData {
  document: string
  firstName: string
  lastName: string
  email: string
  phone: string
  website: string
}

const EMPTY_FORM: FormData = {
  document: '',
  firstName: '',
  lastName: '',
  email: '',
  phone: '',
  website: '',
}

interface Registered {
  professional: string
  startsAt: string
  confirmBefore: string
}

function RegisteredNotice({ registered }: { registered: Registered }) {
  const title = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    title.current?.focus()
  }, [])
  return (
    <section className="public-card" aria-labelledby="registered-title">
      <h1 id="registered-title" ref={title} tabIndex={-1}>
        Turno registrado exitosamente
      </h1>
      <p>
        {`Está pendiente de confirmación. Revise su email: tiene que confirmarlo con el enlace que le enviamos antes de las ${formatLocalTime(registered.confirmBefore)}.`}
      </p>
      <dl className="detail-list">
        <dt>Profesional</dt>
        <dd>{registered.professional}</dd>
        <dt>Día y hora</dt>
        <dd>{longDayAndTime(registered.startsAt)}</dd>
      </dl>
      <p className="hint">
        Si no lo confirma a tiempo, el horario se libera. Para cambiarlo o cancelarlo, comuníquese
        con el consultorio.
      </p>
    </section>
  )
}

function Retry({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <>
      <p role="alert">{message}</p>
      <button type="button" className="secondary" onClick={onRetry}>
        Reintentar
      </button>
    </>
  )
}

/** Reserva sin cuenta: profesional, día, franja y datos del paciente (C-15, sin sesión). */
export default function PublicBookingPage() {
  const [professionalsReload, setProfessionalsReload] = useState(0)
  const professionals = useRemote('professionals', listPublicProfessionals, professionalsReload)
  const [professional, setProfessional] = useState<PublicProfessional | null>(null)
  const [pickedDay, setPickedDay] = useState<string | null>(null)
  const [slotsReload, setSlotsReload] = useState(0)
  const [slot, setSlot] = useState<PublicSlot | null>(null)
  const [form, setForm] = useState<FormData>(EMPTY_FORM)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [registered, setRegistered] = useState<Registered | null>(null)
  // La ref bloquea el segundo envío incluso antes de que React re-renderice el botón.
  const inFlight = useRef(false)

  const today = todayInClinic(new Date())
  const days = Array.from({ length: HORIZON_DAYS }, (_, index) => addDays(today, index))
  const day = pickedDay !== null && days.includes(pickedDay) ? pickedDay : today
  const professionalId = professional?.id ?? null
  const slots = useRemote(
    professionalId === null ? null : `${professionalId}|${day}`,
    () => getPublicSlots(professionalId ?? '', day),
    slotsReload,
  )

  if (registered !== null) {
    return (
      <PublicLayout>
        <RegisteredNotice registered={registered} />
      </PublicLayout>
    )
  }

  function chooseProfessional(next: PublicProfessional) {
    setProfessional(next)
    setSlot(null)
    setError(null)
  }

  function chooseDay(next: string) {
    setPickedDay(next)
    setSlot(null)
    setError(null)
  }

  function setField(name: keyof FormData, value: string) {
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current || professional === null || slot === null) return
    inFlight.current = true
    setSubmitting(true)
    setError(null)
    try {
      const booked = await bookOnline({
        professionalId: professional.id,
        startsAt: slot.starts_at,
        documentNumber: form.document,
        firstName: form.firstName,
        lastName: form.lastName,
        email: form.email,
        phone: form.phone,
        website: form.website,
      })
      setRegistered({
        professional: professional.display_name,
        startsAt: slot.starts_at,
        confirmBefore: booked.confirm_before,
      })
    } catch (failure) {
      setError(messageForBooking(failure))
      if (lostTheSlot(failure)) {
        setSlot(null)
        setSlotsReload((count) => count + 1)
      }
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }

  return (
    <PublicLayout>
      <h1>Reservar un turno</h1>
      <p className="hint">
        Elija el profesional, el día y el horario. Después le pedimos sus datos y le enviamos un
        email para confirmar.
      </p>

      <h2>Profesional</h2>
      {professionals.status === 'loading' ? <LoadingNotice /> : null}
      {professionals.status === 'error' ? (
        <Retry
          message={PROFESSIONALS_FAILED_MESSAGE}
          onRetry={() => {
            setProfessionalsReload((count) => count + 1)
          }}
        />
      ) : null}
      {professionals.status === 'ready' && professionals.data.length === 0 ? (
        <p className="notice">{NO_PROFESSIONALS_MESSAGE}</p>
      ) : null}
      {professionals.status === 'ready' && professionals.data.length > 0 ? (
        <ul className="slot-choices">
          {professionals.data.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                aria-pressed={professional?.id === item.id}
                onClick={() => {
                  chooseProfessional(item)
                }}
              >
                {item.display_name}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {professional === null ? null : (
        <>
          <h2>Día y horario</h2>
          <label htmlFor="public-day">Día</label>{' '}
          <select
            id="public-day"
            value={day}
            onChange={(event) => {
              chooseDay(event.target.value)
            }}
          >
            {days.map((date) => (
              <option key={date} value={date}>
                {formatDayLabel(date)}
              </option>
            ))}
          </select>
          {slots.status === 'loading' ? <LoadingNotice /> : null}
          {slots.status === 'error' ? (
            <Retry
              message={SLOTS_FAILED_MESSAGE}
              onRetry={() => {
                setSlotsReload((count) => count + 1)
              }}
            />
          ) : null}
          {slots.status === 'ready' && slots.data.length === 0 ? (
            <p className="notice">{NO_SLOTS_MESSAGE}</p>
          ) : null}
          {slots.status === 'ready' && slots.data.length > 0 ? (
            <ul className="slot-choices">
              {slots.data.map((item) => (
                <li key={item.starts_at}>
                  <button
                    type="button"
                    aria-pressed={slot?.starts_at === item.starts_at}
                    onClick={() => {
                      setSlot(item)
                      setError(null)
                    }}
                  >
                    {formatLocalTime(item.starts_at)}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}

      {error === null ? null : <p role="alert">{error}</p>}

      {slot === null || professional === null ? null : (
        <form
          className="public-form"
          onSubmit={(event) => {
            void submit(event)
          }}
        >
          <h2>Sus datos</h2>
          <p className="hint">{`Turno elegido: ${professional.display_name}, ${longDayAndTime(slot.starts_at)}`}</p>
          <label htmlFor="public-document">DNI</label>
          <input
            id="public-document"
            name="document_number"
            inputMode="numeric"
            autoComplete="off"
            required
            value={form.document}
            onChange={(event) => {
              setField('document', event.target.value)
            }}
          />
          <label htmlFor="public-first-name">Nombre</label>
          <input
            id="public-first-name"
            name="first_name"
            autoComplete="given-name"
            required
            value={form.firstName}
            onChange={(event) => {
              setField('firstName', event.target.value)
            }}
          />
          <label htmlFor="public-last-name">Apellido</label>
          <input
            id="public-last-name"
            name="last_name"
            autoComplete="family-name"
            required
            value={form.lastName}
            onChange={(event) => {
              setField('lastName', event.target.value)
            }}
          />
          <label htmlFor="public-email">Email</label>
          <input
            id="public-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(event) => {
              setField('email', event.target.value)
            }}
          />
          <label htmlFor="public-phone">Teléfono (opcional)</label>
          <input
            id="public-phone"
            name="phone"
            type="tel"
            autoComplete="tel"
            value={form.phone}
            onChange={(event) => {
              setField('phone', event.target.value)
            }}
          />
          <div className="trap-field" aria-hidden="true">
            <label htmlFor="public-website">Deje este campo vacío</label>
            <input
              id="public-website"
              name="website"
              type="text"
              tabIndex={-1}
              autoComplete="off"
              value={form.website}
              onChange={(event) => {
                setField('website', event.target.value)
              }}
            />
          </div>
          <button type="submit" disabled={submitting}>
            Reservar turno
          </button>
        </form>
      )}
    </PublicLayout>
  )
}
