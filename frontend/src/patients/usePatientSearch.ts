import { useCallback, useEffect, useState } from 'react'
import { searchPatients, type Patient, type PatientSearchResult } from '../api/patients'
import { messageForError } from './messages'

export const SEARCH_DELAY_MS = 300

export type ListState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; result: PatientSearchResult }

/** Búsqueda con espera de 300 ms desde la última tecla; la casilla de inactivos pide al instante. */
export function usePatientSearch(includeInactive: boolean) {
  const [query, setQuery] = useState('')
  const [settled, setSettled] = useState('')
  const [tick, setTick] = useState(0)
  const [list, setList] = useState<ListState>({ status: 'loading' })

  useEffect(() => {
    const timer = setTimeout(() => {
      setSettled(query)
    }, SEARCH_DELAY_MS)
    return () => {
      clearTimeout(timer)
    }
  }, [query])

  useEffect(() => {
    let active = true
    searchPatients({ q: settled, includeInactive })
      .then((result) => {
        if (active) setList({ status: 'ready', result })
      })
      .catch((error: unknown) => {
        if (active) setList({ status: 'error', message: messageForError(error) })
      })
    return () => {
      active = false
    }
  }, [settled, includeInactive, tick])

  const reload = useCallback(() => {
    setTick((current) => current + 1)
  }, [])

  /** Reemplaza una ficha de la tabla sin volver a pedir la lista. */
  const replace = useCallback((saved: Patient) => {
    setList((current) =>
      current.status === 'ready'
        ? {
            status: 'ready',
            result: {
              ...current.result,
              items: current.result.items.map((p) => (p.id === saved.id ? saved : p)),
            },
          }
        : current,
    )
  }, [])

  return { query, setQuery, list, reload, replace }
}
