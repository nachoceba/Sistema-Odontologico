import { useState } from 'react'
import {
  deactivatePatient,
  deletePatient,
  reactivatePatient,
  type Patient,
  type UpcomingAppointment,
} from '../api/patients'
import { ApiError } from '../api/users'
import { useAuth } from '../auth/useAuth'
import { ConfirmDialog } from '../patients/ConfirmDialog'
import { DeactivationNotice } from '../patients/DeactivationNotice'
import {
  EMPTY_MESSAGE,
  PATIENT_GONE_CODE,
  TRUNCATED_MESSAGE,
  listName,
  messageForError,
} from '../patients/messages'
import { PatientForm } from '../patients/PatientForm'
import { usePatientSearch } from '../patients/usePatientSearch'
import { EmptyNotice, LoadingNotice } from '../ui/Notices'

type FormState = 'closed' | 'create' | Patient
type ConfirmState = { kind: 'deactivate' | 'delete'; patient: Patient } | null

export default function PatientsPage() {
  const { user } = useAuth()
  const [includeInactive, setIncludeInactive] = useState(false)
  const { query, setQuery, list, reload, replace } = usePatientSearch(includeInactive)
  const [form, setForm] = useState<FormState>('closed')
  const [confirm, setConfirm] = useState<ConfirmState>(null)
  const [alertMessage, setAlertMessage] = useState<string | null>(null)
  const [upcoming, setUpcoming] = useState<UpcomingAppointment[]>([])
  const canWrite = user?.role === 'admin' || user?.role === 'receptionist'
  const canDelete = user?.role === 'admin'

  /** Muestra el rechazo; si el paciente ya no existe, vuelve a pedir la lista. */
  function fail(error: unknown) {
    setAlertMessage(messageForError(error))
    if (error instanceof ApiError && error.code === PATIENT_GONE_CODE) {
      setForm('closed')
      reload()
    }
  }

  async function runConfirmed(action: NonNullable<ConfirmState>) {
    setConfirm(null)
    setAlertMessage(null)
    setUpcoming([])
    try {
      if (action.kind === 'deactivate') {
        const result = await deactivatePatient(action.patient.id)
        replace(result.patient)
        setUpcoming(result.upcoming_appointments)
      } else {
        await deletePatient(action.patient.id)
        reload()
      }
    } catch (error) {
      fail(error)
    }
  }

  async function reactivate(patient: Patient) {
    setAlertMessage(null)
    setUpcoming([])
    try {
      replace(await reactivatePatient(patient.id))
    } catch (error) {
      fail(error)
    }
  }

  return (
    <div className="page page--wide">
      <header className="page-header">
        <h1>Pacientes</h1>
      </header>
      <div className="search-bar">
        <input
          type="search"
          aria-label="Buscar paciente"
          placeholder="Apellido o documento"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
          }}
        />
        <label>
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(event) => {
              setIncludeInactive(event.target.checked)
            }}
          />{' '}
          Incluir inactivos
        </label>
        {canWrite ? (
          <button
            type="button"
            onClick={() => {
              setForm('create')
            }}
          >
            Nuevo paciente
          </button>
        ) : null}
      </div>
      {alertMessage === null ? null : <p role="alert">{alertMessage}</p>}
      <DeactivationNotice appointments={upcoming} />
      {list.status === 'loading' ? <LoadingNotice /> : null}
      {list.status === 'error' ? <p role="alert">{list.message}</p> : null}
      {list.status === 'ready' && list.result.items.length === 0 ? (
        <EmptyNotice>{EMPTY_MESSAGE}</EmptyNotice>
      ) : null}
      {list.status === 'ready' && list.result.truncated ? (
        <p role="status">{TRUNCATED_MESSAGE}</p>
      ) : null}
      {list.status === 'ready' && list.result.items.length > 0 ? (
        <div className="table-scroll" role="region" aria-label="Pacientes" tabIndex={0}>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Paciente</th>
                <th scope="col">Documento</th>
                <th scope="col">Email</th>
                <th scope="col">Teléfono</th>
                <th scope="col">Estado</th>
                {canWrite ? <th scope="col">Acciones</th> : null}
              </tr>
            </thead>
            <tbody>
              {list.result.items.map((p) => (
                <tr key={p.id}>
                  <td>{listName(p)}</td>
                  <td>{p.document_number}</td>
                  <td>{p.email}</td>
                  <td>{p.phone ?? ''}</td>
                  <td>{p.active ? 'Activo' : 'Inactivo'}</td>
                  {canWrite ? (
                    <td className="row-actions">
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => {
                          setForm(p)
                        }}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => {
                          if (p.active) setConfirm({ kind: 'deactivate', patient: p })
                          else void reactivate(p)
                        }}
                      >
                        {p.active ? 'Desactivar' : 'Reactivar'}
                      </button>
                      {canDelete ? (
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => {
                            setConfirm({ kind: 'delete', patient: p })
                          }}
                        >
                          Borrar
                        </button>
                      ) : null}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {canWrite && form !== 'closed' ? (
        <PatientForm
          key={form === 'create' ? 'create' : form.id}
          patient={form === 'create' ? undefined : form}
          onSaved={() => {
            setForm('closed')
            reload()
          }}
          onCancel={() => {
            setForm('closed')
          }}
        />
      ) : null}
      {confirm === null ? null : (
        <ConfirmDialog
          title={confirm.kind === 'deactivate' ? 'Desactivar paciente' : 'Borrar paciente'}
          message={
            confirm.kind === 'deactivate'
              ? `¿Desactivar a ${confirm.patient.first_name} ${confirm.patient.last_name}? Sus turnos no se cancelan.`
              : `¿Borrar a ${confirm.patient.first_name} ${confirm.patient.last_name}? Esta acción no se puede deshacer.`
          }
          confirmLabel={confirm.kind === 'deactivate' ? 'Desactivar' : 'Borrar'}
          onConfirm={() => {
            void runConfirmed(confirm)
          }}
          onCancel={() => {
            setConfirm(null)
          }}
        />
      )}
    </div>
  )
}
