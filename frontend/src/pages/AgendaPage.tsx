import { useEffect, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import { listProfessionals, type Professional } from '../api/professionals'
import { AppNav } from '../agenda/AppNav'
import { DateNavigator, type AgendaView } from '../agenda/DateNavigator'
import { DayColumn } from '../agenda/DayColumn'
import { addDays, parseIsoDate, todayInClinic, weekDays } from '../agenda/dates'
import { INACTIVE_PROFESSIONAL_MESSAGE, NO_PROFESSIONALS_MESSAGE } from '../agenda/messages'
import { ProfessionalPicker } from '../agenda/ProfessionalPicker'
import { useAgendaData } from '../agenda/useAgendaData'
import { WeekView } from '../agenda/WeekView'
import { useAuth } from '../auth/useAuth'
import { NO_FILE_MESSAGE, messageForError } from '../professionals/messages'

type ListState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; professionals: Professional[] }

function readView(value: string | null): AgendaView | null {
  return value === 'dia' || value === 'semana' ? value : null
}

export default function AgendaPage() {
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const [reloadKey, setReloadKey] = useState(0)
  const [list, setList] = useState<{ key: number; state: ListState } | null>(null)

  const isDentist = user?.role === 'dentist'
  const ownId = user?.professional_id ?? null
  const needsList = user !== null && !(isDentist && ownId === null)

  useEffect(() => {
    if (!needsList) return
    let active = true
    listProfessionals().then(
      (professionals) => {
        if (active) setList({ key: reloadKey, state: { status: 'ready', professionals } })
      },
      (error: unknown) => {
        if (active) {
          setList({ key: reloadKey, state: { status: 'error', message: messageForError(error) } })
        }
      },
    )
    return () => {
      active = false
    }
  }, [needsList, reloadKey])

  const rawDate = params.get('fecha')
  const rawView = params.get('vista')
  const validDate = rawDate === null ? null : parseIsoDate(rawDate)
  const today = todayInClinic(new Date())
  const date = validDate ?? today
  const view = readView(rawView) ?? 'dia'
  const invalidParams =
    (rawDate !== null && validDate === null) || (rawView !== null && readView(rawView) === null)

  useEffect(() => {
    if (!invalidParams) return
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        if (rawDate !== null && parseIsoDate(rawDate) === null) {
          next.set('fecha', todayInClinic(new Date()))
        }
        if (rawView !== null && readView(rawView) === null) next.set('vista', 'dia')
        return next
      },
      { replace: true },
    )
  }, [invalidParams, rawDate, rawView, setParams])

  const listState: ListState = !needsList
    ? { status: 'ready', professionals: [] }
    : list?.key === reloadKey
      ? list.state
      : { status: 'loading' }
  const professionals = listState.status === 'ready' ? listState.professionals : []

  let professionalId: string | null = null
  if (isDentist) {
    professionalId = ownId
  } else if (professionals.length > 0) {
    const requested = params.get('profesional')
    professionalId =
      professionals.find((p) => p.id === requested)?.id ??
      professionals.find((p) => p.active)?.id ??
      professionals[0]?.id ??
      null
  }
  const current = professionals.find((p) => p.id === professionalId)

  const step = view === 'semana' ? 7 : 1
  const dates = view === 'semana' ? weekDays(date) : [date]
  const data = useAgendaData(professionalId, dates, reloadKey)

  function go(next: { profesional?: string; fecha?: string; vista?: AgendaView }) {
    setParams({
      ...(professionalId === null ? {} : { profesional: professionalId }),
      fecha: date,
      vista: view,
      ...next,
    })
  }

  function refresh() {
    setReloadKey((key) => key + 1)
  }

  if (user === null) return null

  let body: ReactNode
  if (isDentist && ownId === null) {
    body = <p>{NO_FILE_MESSAGE}</p>
  } else if (listState.status === 'loading') {
    body = <p role="status">Cargando…</p>
  } else if (listState.status === 'error') {
    body = <p role="alert">{listState.message}</p>
  } else if (professionalId === null) {
    body = <p>{NO_PROFESSIONALS_MESSAGE}</p>
  } else {
    body = (
      <>
        {isDentist && current !== undefined ? <h2>{current.display_name}</h2> : null}
        {!isDentist ? (
          <ProfessionalPicker
            professionals={professionals}
            selectedId={professionalId}
            onChange={(id) => {
              go({ profesional: id })
            }}
          />
        ) : null}
        {current !== undefined && !current.active ? (
          <p className="notice">{INACTIVE_PROFESSIONAL_MESSAGE}</p>
        ) : null}
        <DateNavigator
          date={date}
          view={view}
          onPrevious={() => {
            go({ fecha: addDays(date, -step) })
          }}
          onNext={() => {
            go({ fecha: addDays(date, step) })
          }}
          onToday={() => {
            go({ fecha: todayInClinic(new Date()) })
          }}
          onDate={(fecha) => {
            go({ fecha })
          }}
          onView={(vista) => {
            go({ vista })
          }}
          onRefresh={refresh}
        />
        {data.status === 'loading' ? <p role="status">Cargando…</p> : null}
        {data.status === 'error' ? (
          <>
            <p role="alert">{data.message}</p>
            {data.retryable ? (
              <button type="button" onClick={refresh}>
                Reintentar
              </button>
            ) : null}
          </>
        ) : null}
        {data.status === 'ready' && view === 'semana' ? (
          <WeekView
            columns={data.columns}
            today={today}
            onSelectDay={(fecha) => {
              go({ fecha, vista: 'dia' })
            }}
          />
        ) : null}
        {data.status === 'ready' && view === 'dia'
          ? data.columns.map((column) => (
              <DayColumn key={column.date} column={column} highlight={column.date === today} />
            ))
          : null}
      </>
    )
  }

  return (
    <main className="page page--wide">
      <AppNav />
      <h1>Agenda</h1>
      {body}
    </main>
  )
}
