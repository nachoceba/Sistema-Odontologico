import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import type { Appointment, AttendanceStatus } from '../api/appointments'
import { recordAttendance } from '../api/appointments'
import { listProfessionals, type ConflictReason, type Professional } from '../api/professionals'
import { DateNavigator, type AgendaView } from '../agenda/DateNavigator'
import { DayColumn } from '../agenda/DayColumn'
import { addDays, parseIsoDate, todayInClinic, weekDays } from '../agenda/dates'
import { INACTIVE_PROFESSIONAL_MESSAGE, NO_PROFESSIONALS_MESSAGE } from '../agenda/messages'
import { ProfessionalPicker } from '../agenda/ProfessionalPicker'
import { useAgendaData } from '../agenda/useAgendaData'
import { WeekView } from '../agenda/WeekView'
import { useAuth } from '../auth/useAuth'
import { appointmentActions, slotActions } from '../appointments/actions'
import { AppointmentDetail } from '../appointments/AppointmentDetail'
import { BookingPanel } from '../appointments/BookingPanel'
import { CancelDialog } from '../appointments/CancelDialog'
import { ConflictsPanel } from '../appointments/ConflictsPanel'
import {
  ATTENDANCE_NOTICE,
  CANCELLED_NOTICE,
  COMPLETED_LABEL,
  NO_SHOW_LABEL,
  bookedNotice,
  messageForAppointmentError,
  rescheduledNotice,
  shouldReloadAfter,
} from '../appointments/messages'
import { RescheduleDialog } from '../appointments/RescheduleDialog'
import { ConfirmDialog } from '../patients/ConfirmDialog'
import { listName } from '../patients/messages'
import { NO_FILE_MESSAGE, messageForError } from '../professionals/messages'
import { LoadingNotice } from '../ui/Notices'

/** Lo que está abierto sobre la agenda: un solo panel o diálogo a la vez (design D-6). */
type Panel =
  | { kind: 'book'; slot: { startsAt: string; endsAt: string } }
  | { kind: 'detail'; appointment: Appointment; conflict: ConflictReason | null }
  | { kind: 'cancel'; appointment: Appointment }
  | { kind: 'reschedule'; appointment: Appointment }
  | { kind: 'attendance'; appointment: Appointment; status: AttendanceStatus }

type Notice = { kind: 'ok' | 'error'; text: string }

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
  // Recargar la agenda detrás de un panel abierto no debe volver a pedir la lista de profesionales.
  const [agendaKey, setAgendaKey] = useState(0)
  const [panel, setPanel] = useState<Panel | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const attendanceBusy = useRef(false)
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
  const data = useAgendaData(professionalId, dates, reloadKey + agendaKey)

  function go(next: { profesional?: string; fecha?: string; vista?: AgendaView }) {
    setPanel(null)
    setNotice(null)
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

  function reloadAgenda() {
    setAgendaKey((key) => key + 1)
  }

  /** Éxito: cierra el panel, avisa y vuelve a pedir la agenda (P-7, DD-83). */
  function succeed(text: string) {
    setPanel(null)
    setNotice({ kind: 'ok', text })
    reloadAgenda()
  }

  const now = new Date()
  const role = user?.role
  const canManage = role === 'admin' || role === 'receptionist'
  const professionalActive = current?.active ?? false
  const professionalName = current?.display_name ?? ''

  function openDetail(id: string) {
    if (data.status !== 'ready') return
    const appointment = data.appointments.find((a) => a.id === id)
    if (appointment === undefined) return
    const conflict = data.conflicts.find((c) => c.appointment_id === id)?.reason ?? null
    setNotice(null)
    setPanel({ kind: 'detail', appointment, conflict })
  }

  async function confirmAttendance(appointment: Appointment, status: AttendanceStatus) {
    if (attendanceBusy.current) return
    attendanceBusy.current = true
    try {
      await recordAttendance(appointment.id, status)
      succeed(ATTENDANCE_NOTICE)
    } catch (error) {
      setPanel(null)
      setNotice({ kind: 'error', text: messageForAppointmentError(error) })
      if (shouldReloadAfter(error)) reloadAgenda()
    } finally {
      attendanceBusy.current = false
    }
  }

  if (user === null) return null

  const gridActions: {
    onBookSlot?: (slot: { startsAt: string; endsAt: string }) => void
    canBook?: (slot: { startsAt: string }) => boolean
    onSelectAppointment: (id: string) => void
  } = {
    onSelectAppointment: openDetail,
    ...(canManage
      ? {
          onBookSlot: (slot: { startsAt: string; endsAt: string }) => {
            setNotice(null)
            setPanel({ kind: 'book', slot })
          },
          canBook: (slot: { startsAt: string }) =>
            slotActions({ role: user.role, professionalActive, now, slot }).book,
        }
      : {}),
  }

  let body: ReactNode
  if (isDentist && ownId === null) {
    body = <p>{NO_FILE_MESSAGE}</p>
  } else if (listState.status === 'loading') {
    body = <LoadingNotice />
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
        {notice === null ? null : (
          <p
            role={notice.kind === 'ok' ? 'status' : 'alert'}
            className={notice.kind === 'ok' ? 'notice notice--ok' : 'notice'}
          >
            {notice.text}
          </p>
        )}
        {canManage && data.status === 'ready' && data.conflicts.length > 0 ? (
          <ConflictsPanel
            conflicts={data.conflicts}
            professionalActive={professionalActive}
            onReschedule={(appointment) => {
              setPanel({ kind: 'reschedule', appointment })
            }}
            onCancel={(appointment) => {
              setPanel({ kind: 'cancel', appointment })
            }}
            onView={(fecha) => {
              go({ fecha, vista: 'dia' })
            }}
          />
        ) : null}
        {data.status === 'loading' ? <LoadingNotice /> : null}
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
            {...gridActions}
          />
        ) : null}
        {data.status === 'ready' && view === 'dia'
          ? data.columns.map((column) => (
              <DayColumn
                key={column.date}
                column={column}
                highlight={column.date === today}
                {...gridActions}
              />
            ))
          : null}
      </>
    )
  }

  return (
    <div className="page page--wide">
      <h1>Agenda</h1>
      {body}
      {panel?.kind === 'book' && professionalId !== null ? (
        <BookingPanel
          key={panel.slot.startsAt}
          slot={panel.slot}
          professionalId={professionalId}
          professionalName={professionalName}
          onBooked={(patientName, startsAt) => {
            succeed(bookedNotice(patientName, startsAt))
          }}
          onRejected={reloadAgenda}
          onClose={() => {
            setPanel(null)
          }}
        />
      ) : null}
      {panel?.kind === 'detail' ? (
        <AppointmentDetail
          appointment={panel.appointment}
          professionalName={professionalName}
          conflict={panel.conflict}
          actions={appointmentActions({
            role: user.role,
            ownProfessionalId: ownId,
            professionalActive,
            now,
            appointment: {
              status: panel.appointment.status,
              startsAt: panel.appointment.starts_at,
              professionalId: panel.appointment.professional_id,
            },
          })}
          onCancel={() => {
            setPanel({ kind: 'cancel', appointment: panel.appointment })
          }}
          onReschedule={() => {
            setPanel({ kind: 'reschedule', appointment: panel.appointment })
          }}
          onAttendance={(status) => {
            setPanel({ kind: 'attendance', appointment: panel.appointment, status })
          }}
          onClose={() => {
            setPanel(null)
          }}
        />
      ) : null}
      {panel?.kind === 'cancel' ? (
        <CancelDialog
          appointment={panel.appointment}
          onDone={() => {
            succeed(CANCELLED_NOTICE)
          }}
          onRejected={reloadAgenda}
          onClose={() => {
            setPanel(null)
          }}
        />
      ) : null}
      {panel?.kind === 'reschedule' ? (
        <RescheduleDialog
          appointment={panel.appointment}
          role={user.role}
          onDone={(startsAt) => {
            succeed(rescheduledNotice(startsAt))
          }}
          onRejected={reloadAgenda}
          onClose={() => {
            setPanel(null)
          }}
        />
      ) : null}
      {panel?.kind === 'attendance' ? (
        <ConfirmDialog
          title={`¿Marcar a ${listName({
            first_name: panel.appointment.patient_first_name,
            last_name: panel.appointment.patient_last_name,
          })} como ${panel.status === 'completed' ? 'atendido' : 'ausente'}?`}
          message="Después no se puede cambiar"
          confirmLabel={panel.status === 'completed' ? COMPLETED_LABEL : NO_SHOW_LABEL}
          onConfirm={() => {
            void confirmAttendance(panel.appointment, panel.status)
          }}
          onCancel={() => {
            setPanel(null)
          }}
        />
      ) : null}
    </div>
  )
}
