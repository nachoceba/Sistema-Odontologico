import { useCallback, useEffect, useRef, useState, type SyntheticEvent } from 'react'
import {
  createTreatment,
  listTreatments,
  updateTreatment,
  type Treatment,
  type TreatmentChanges,
} from '../api/treatments'
import { ConfirmDialog } from '../patients/ConfirmDialog'
import { LoadingNotice } from '../ui/Notices'
import { EMPTY_CATALOG_MESSAGE, DEACTIVATE_WARNING, messageForTreatmentError } from '../treatments/messages'

type ListState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; treatments: Treatment[] }

function byName(a: Treatment, b: Treatment): number {
  return a.name.localeCompare(b.name, 'es', { sensitivity: 'base' })
}

async function fetchTreatments(): Promise<ListState> {
  try {
    return { status: 'ready', treatments: (await listTreatments()).sort(byName) }
  } catch (error) {
    return { status: 'error', message: messageForTreatmentError(error) }
  }
}

/** Catálogo de tratamientos para el administrador (C-17, DD-143): listar, agregar, renombrar y activar. */
export default function TreatmentsPage() {
  const [list, setList] = useState<ListState>({ status: 'loading' })
  const [alertMessage, setAlertMessage] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [editing, setEditing] = useState<{ id: string; name: string } | null>(null)
  const [confirming, setConfirming] = useState<Treatment | null>(null)
  const [busy, setBusy] = useState(false)
  // La ref bloquea el segundo envío incluso antes de que React vuelva a dibujar el botón.
  const inFlight = useRef(false)

  useEffect(() => {
    let active = true
    void fetchTreatments().then((next) => {
      if (active) setList(next)
    })
    return () => {
      active = false
    }
  }, [])

  const reload = useCallback(() => {
    setList({ status: 'loading' })
    void fetchTreatments().then(setList)
  }, [])

  function replace(saved: Treatment) {
    setList((current) =>
      current.status === 'ready'
        ? {
            status: 'ready',
            treatments: current.treatments.map((t) => (t.id === saved.id ? saved : t)).sort(byName),
          }
        : current,
    )
  }

  /** Una sola escritura a la vez; devuelve si salió bien. */
  async function write(action: () => Promise<void>): Promise<boolean> {
    if (inFlight.current) return false
    inFlight.current = true
    setBusy(true)
    setAlertMessage(null)
    try {
      await action()
      return true
    } catch (error) {
      setAlertMessage(messageForTreatmentError(error))
      return false
    } finally {
      inFlight.current = false
      setBusy(false)
    }
  }

  async function handleCreate(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    await write(async () => {
      const created = await createTreatment(newName)
      setList((current) =>
        current.status === 'ready'
          ? { status: 'ready', treatments: [...current.treatments, created].sort(byName) }
          : current,
      )
      setNewName('')
    })
  }

  async function change(target: Treatment, changes: TreatmentChanges): Promise<boolean> {
    return write(async () => {
      replace(await updateTreatment(target.id, changes))
    })
  }

  async function handleRename(event: SyntheticEvent<HTMLFormElement>, target: Treatment) {
    event.preventDefault()
    if (editing === null) return
    if (await change(target, { name: editing.name })) setEditing(null)
  }

  return (
    <div className="page page--wide">
      <header className="page-header">
        <h1>Tratamientos</h1>
      </header>
      {alertMessage === null ? null : <p role="alert">{alertMessage}</p>}
      {list.status === 'loading' ? <LoadingNotice /> : null}
      {list.status === 'error' ? (
        <p role="alert">
          {list.message}{' '}
          <button type="button" className="link-button" onClick={reload}>
            Reintentar
          </button>
        </p>
      ) : null}
      {list.status === 'ready' && list.treatments.length === 0 ? (
        <p role="status">{EMPTY_CATALOG_MESSAGE}</p>
      ) : null}
      {list.status === 'ready' && list.treatments.length > 0 ? (
        <div className="table-scroll" role="region" aria-label="Tratamientos" tabIndex={0}>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Estado</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {list.treatments.map((t) => (
                <tr key={t.id}>
                  <td>
                    {editing?.id === t.id ? (
                      <form
                        className="inline-form"
                        onSubmit={(event) => {
                          void handleRename(event, t)
                        }}
                      >
                        <input
                          aria-label="Nuevo nombre"
                          value={editing.name}
                          maxLength={80}
                          onChange={(event) => {
                            setEditing({ id: t.id, name: event.target.value })
                          }}
                        />
                        <button type="submit" disabled={busy}>
                          Guardar
                        </button>
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => {
                            setEditing(null)
                            setAlertMessage(null)
                          }}
                        >
                          Cancelar
                        </button>
                      </form>
                    ) : (
                      t.name
                    )}
                  </td>
                  <td>{t.active ? 'Activo' : 'Inactivo'}</td>
                  <td className="row-actions">
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => {
                        setAlertMessage(null)
                        setEditing({ id: t.id, name: t.name })
                      }}
                    >
                      Renombrar
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      disabled={busy}
                      onClick={() => {
                        if (t.active) setConfirming(t)
                        else void change(t, { active: true })
                      }}
                    >
                      {t.active ? 'Desactivar' : 'Activar'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {list.status === 'ready' ? (
        <form className="form-card" onSubmit={(event) => void handleCreate(event)}>
          <h2>Agregar tratamiento</h2>
          <label>
            Nombre
            <input
              value={newName}
              maxLength={80}
              onChange={(event) => {
                setNewName(event.target.value)
              }}
            />
          </label>
          <div className="form-actions">
            <button type="submit" disabled={busy || newName.trim() === ''}>
              Agregar tratamiento
            </button>
          </div>
        </form>
      ) : null}
      {confirming === null ? null : (
        <ConfirmDialog
          title="Desactivar tratamiento"
          message={`${confirming.name}. ${DEACTIVATE_WARNING}`}
          confirmLabel="Desactivar"
          onConfirm={() => {
            const target = confirming
            setConfirming(null)
            void change(target, { active: false })
          }}
          onCancel={() => {
            setConfirming(null)
          }}
        />
      )}
    </div>
  )
}
