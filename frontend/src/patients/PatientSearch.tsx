import { useEffect, useState } from 'react'
import { searchPatients, type Patient } from '../api/patients'
import { SEARCH_DELAY_MS } from './usePatientSearch'
import { EMPTY_MESSAGE, TRUNCATED_MESSAGE, listName, messageForError } from './messages'

export type SelectedPatient = { id: string; name: string }

type State =
  | { status: 'idle' }
  | { status: 'error'; message: string }
  | { status: 'ready'; items: Patient[]; truncated: boolean }

/** Buscador de pacientes activos para elegir uno (lo reutilizará la pantalla de turnos). */
export function PatientSearch({ onSelect }: { onSelect: (patient: SelectedPatient) => void }) {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<State>({ status: 'idle' })

  useEffect(() => {
    const term = query.trim()
    if (term === '') return undefined
    let active = true
    const timer = setTimeout(() => {
      searchPatients({ q: term })
        .then((result) => {
          if (active) setResult({ status: 'ready', ...result })
        })
        .catch((error: unknown) => {
          if (active) setResult({ status: 'error', message: messageForError(error) })
        })
    }, SEARCH_DELAY_MS)
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [query])

  // Con el campo vacío se ignora lo último que llegó (derivado, sin efecto).
  const state: State = query.trim() === '' ? { status: 'idle' } : result
  return (
    <div className="patient-search">
      <input
        type="search"
        aria-label="Buscar paciente"
        placeholder="Apellido o documento"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
        }}
      />
      {state.status === 'error' ? <p role="alert">{state.message}</p> : null}
      {state.status === 'ready' && state.items.length === 0 ? (
        <p role="status">{EMPTY_MESSAGE}</p>
      ) : null}
      {state.status === 'ready' && state.truncated ? (
        <p role="status">{TRUNCATED_MESSAGE}</p>
      ) : null}
      {state.status === 'ready' && state.items.length > 0 ? (
        <ul>
          {state.items.map((patient) => (
            <li key={patient.id}>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  onSelect({ id: patient.id, name: listName(patient) })
                }}
              >
                {listName(patient)}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
