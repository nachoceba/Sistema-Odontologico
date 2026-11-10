import { useEffect, useId, useRef, useState } from 'react'
import {
  listProfessionalTreatments,
  listTreatments,
  replaceProfessionalTreatments,
  type Treatment,
} from '../api/treatments'
import { NO_ACTIVE_ASSIGNED_MESSAGE, messageForTreatmentError } from '../treatments/messages'
import { LoadingNotice } from '../ui/Notices'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; assigned: Treatment[]; catalog: Treatment[] }

async function fetchState(professionalId: string, editable: boolean): Promise<State> {
  try {
    const [assigned, catalog] = await Promise.all([
      listProfessionalTreatments(professionalId),
      editable ? listTreatments() : Promise.resolve([]),
    ])
    return { status: 'ready', assigned, catalog }
  } catch (error) {
    return { status: 'error', message: messageForTreatmentError(error) }
  }
}

/** "Tratamientos que ofrece": el administrador marca casillas; los demás roles solo leen (C-17, DD-141). */
export function TreatmentsPanel({
  professionalId,
  editable,
}: {
  professionalId: string
  editable: boolean
}) {
  const headingId = useId()
  const [state, setState] = useState<State>({ status: 'loading' })
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const inFlight = useRef(false)

  useEffect(() => {
    let active = true
    void fetchState(professionalId, editable).then((next) => {
      if (!active) return
      setState(next)
      if (next.status === 'ready') setChecked(new Set(next.assigned.map((t) => t.id)))
    })
    return () => {
      active = false
    }
  }, [professionalId, editable])

  async function save() {
    if (inFlight.current) return
    inFlight.current = true
    setError(null)
    setSaved(false)
    try {
      // Se manda en el orden del catálogo para que el pedido no dependa del orden de los clics.
      const ids =
        state.status === 'ready' ? state.catalog.filter((t) => checked.has(t.id)).map((t) => t.id) : []
      const assigned = await replaceProfessionalTreatments(professionalId, ids)
      setState((current) => (current.status === 'ready' ? { ...current, assigned } : current))
      setSaved(true)
    } catch (failure) {
      setError(messageForTreatmentError(failure))
    } finally {
      inFlight.current = false
    }
  }

  function toggle(id: string) {
    setSaved(false)
    setChecked((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const assigned = state.status === 'ready' ? state.assigned : []
  const noneActive = state.status === 'ready' && !assigned.some((t) => t.active)

  return (
    <section aria-labelledby={headingId}>
      <h2 id={headingId}>Tratamientos que ofrece</h2>
      {state.status === 'loading' ? <LoadingNotice /> : null}
      {state.status === 'error' ? <p role="alert">{state.message}</p> : null}
      {noneActive ? <p className="hint">{NO_ACTIVE_ASSIGNED_MESSAGE}</p> : null}
      {state.status === 'ready' && editable ? (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void save()
          }}
        >
          <ul className="check-list">
            {state.catalog.map((t) => (
              <li key={t.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={checked.has(t.id)}
                    onChange={() => {
                      toggle(t.id)
                    }}
                  />
                  {t.name}
                </label>
                {t.active ? null : <span className="status-tag">Inactivo</span>}
              </li>
            ))}
          </ul>
          {error === null ? null : <p role="alert">{error}</p>}
          {saved ? <p role="status">Tratamientos guardados</p> : null}
          <div className="form-actions">
            <button type="submit">Guardar tratamientos</button>
          </div>
        </form>
      ) : null}
      {state.status === 'ready' && !editable && assigned.length > 0 ? (
        <ul className="check-list">
          {assigned.map((t) => (
            <li key={t.id}>
              {t.name}
              {t.active ? null : <span className="status-tag">Inactivo</span>}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
