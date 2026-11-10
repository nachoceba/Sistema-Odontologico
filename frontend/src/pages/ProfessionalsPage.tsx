import { useEffect, useState } from 'react'
import {
  getWorkingHours,
  listProfessionals,
  listTimeOff,
  type Conflict,
  type Professional,
  type TimeOff,
  type WorkingBlock,
} from '../api/professionals'
import { useAuth } from '../auth/useAuth'
import { ConflictNotice } from '../professionals/ConflictNotice'
import { NO_FILE_MESSAGE, messageForError } from '../professionals/messages'
import { ProfileCard } from '../professionals/ProfileCard'
import { TimeOffPanel } from '../professionals/TimeOffPanel'
import { TreatmentsPanel } from '../professionals/TreatmentsPanel'
import { WeekEditor } from '../professionals/WeekEditor'
import { LoadingNotice } from '../ui/Notices'

type ListState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; professionals: Professional[] }

type DetailState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; blocks: WorkingBlock[]; timeOff: TimeOff[] }

async function fetchList(): Promise<ListState> {
  try {
    return { status: 'ready', professionals: await listProfessionals() }
  } catch (error) {
    return { status: 'error', message: messageForError(error) }
  }
}

async function fetchDetail(id: string): Promise<DetailState> {
  try {
    const [blocks, timeOff] = await Promise.all([getWorkingHours(id), listTimeOff(id)])
    return { status: 'ready', blocks, timeOff }
  } catch (error) {
    return { status: 'error', message: messageForError(error) }
  }
}

function ProfessionalDetail({
  professional,
  editable,
  onSaved,
}: {
  professional: Professional
  editable: boolean
  onSaved: (saved: Professional) => void
}) {
  const [detail, setDetail] = useState<DetailState>({ status: 'loading' })
  const [conflicts, setConflicts] = useState<Conflict[]>([])

  useEffect(() => {
    let active = true
    void fetchDetail(professional.id).then((next) => {
      if (active) setDetail(next)
    })
    return () => {
      active = false
    }
  }, [professional.id])

  return (
    <article aria-label={`Ficha de ${professional.display_name}`}>
      <ProfileCard professional={professional} editable={editable} onSaved={onSaved} />
      <TreatmentsPanel professionalId={professional.id} editable={editable} />
      {detail.status === 'loading' ? <LoadingNotice /> : null}
      {detail.status === 'error' ? <p role="alert">{detail.message}</p> : null}
      {detail.status === 'ready' ? (
        <>
          <WeekEditor
            professionalId={professional.id}
            blocks={detail.blocks}
            editable={editable}
            onConflicts={setConflicts}
          />
          <ConflictNotice conflicts={conflicts} />
          <TimeOffPanel
            professionalId={professional.id}
            initial={detail.timeOff}
            editable={editable}
            onConflicts={setConflicts}
          />
        </>
      ) : null}
    </article>
  )
}

export default function ProfessionalsPage() {
  const { user } = useAuth()
  const [list, setList] = useState<ListState>({ status: 'loading' })
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void fetchList().then((next) => {
      if (active) setList(next)
    })
    return () => {
      active = false
    }
  }, [])

  function replaceProfessional(saved: Professional) {
    setList((current) =>
      current.status === 'ready'
        ? {
            status: 'ready',
            professionals: current.professionals.map((p) => (p.id === saved.id ? saved : p)),
          }
        : current,
    )
  }

  const editable = user?.role === 'admin'
  const professionals = list.status === 'ready' ? list.professionals : []
  // Con una sola ficha (el odontólogo ve solo la suya) se abre sin selector.
  const onlyOne = professionals.length === 1 ? professionals[0] : undefined
  const selected = onlyOne ?? professionals.find((p) => p.id === selectedId)

  return (
    <div className="page page--wide">
      <header className="page-header">
        <h1>Profesionales</h1>
      </header>
      {list.status === 'loading' ? <LoadingNotice /> : null}
      {list.status === 'error' ? <p role="alert">{list.message}</p> : null}
      {list.status === 'ready' && professionals.length === 0 ? <p>{NO_FILE_MESSAGE}</p> : null}
      {professionals.length > 1 ? (
        <div className="table-scroll" role="region" aria-label="Profesionales" tabIndex={0}>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Matrícula</th>
                <th scope="col">Estado</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {professionals.map((p) => (
                <tr key={p.id}>
                  <td>{p.display_name}</td>
                  <td>{p.license_number ?? 'Sin matrícula'}</td>
                  <td>{p.active ? 'Activo' : 'Inactivo'}</td>
                  <td className="row-actions">
                    <button
                      type="button"
                      className="secondary"
                      aria-label={`Ver a ${p.display_name}`}
                      onClick={() => {
                        setSelectedId(p.id)
                      }}
                    >
                      Ver
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {selected === undefined ? null : (
        <ProfessionalDetail
          key={selected.id}
          professional={selected}
          editable={editable}
          onSaved={replaceProfessional}
        />
      )}
    </div>
  )
}
