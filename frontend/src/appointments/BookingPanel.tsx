import { useState } from 'react'
import { bookAppointment } from '../api/appointments'
import { listProfessionalTreatments } from '../api/treatments'
import { ApiError } from '../api/users'
import { useRemote } from '../public/useRemote'
import { LoadingNotice } from '../ui/Notices'
import { formatLocalTime } from '../agenda/dates'
import { PatientForm } from '../patients/PatientForm'
import { PatientSearch, type SelectedPatient } from '../patients/PatientSearch'
import { listName } from '../patients/messages'
import {
  ACCENT_NOTE,
  BOOK_SUBMIT_LABEL,
  NO_ACTIVE_TREATMENTS_MESSAGE,
  TREATMENTS_FAILED_MESSAGE,
  dayAndTime,
} from './messages'
import { SidePanel } from './SidePanel'
import { useAppointmentAction } from './useAppointmentAction'

type Step = 'search' | 'new'

/** Panel para agendar en una franja libre: elegir o crear el paciente y confirmar (US-007). */
export function BookingPanel({
  slot,
  professionalId,
  professionalName,
  onBooked,
  onRejected,
  onClose,
}: {
  slot: { startsAt: string; endsAt: string }
  professionalId: string
  professionalName: string
  onBooked: (patientName: string, startsAt: string, treatmentName: string) => void
  onRejected: () => void
  onClose: () => void
}) {
  const [step, setStep] = useState<Step>('search')
  const [patient, setPatient] = useState<SelectedPatient | null>(null)
  const [treatmentId, setTreatmentId] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const treatments = useRemote(
    professionalId,
    () => listProfessionalTreatments(professionalId),
    reloadKey,
  )
  const offered = treatments.status === 'ready' ? treatments.data.filter((t) => t.active) : []
  const chosen = offered.find((t) => t.id === treatmentId)
  const action = useAppointmentAction({
    onDone: () => {
      if (patient !== null && chosen !== undefined) onBooked(patient.name, slot.startsAt, chosen.name)
    },
    onRejected,
  })

  function submit() {
    if (patient === null || chosen === undefined) return
    void action.run(() =>
      bookAppointment({
        patientId: patient.id,
        professionalId,
        treatmentId: chosen.id,
        startsAt: slot.startsAt,
      }).catch((failure: unknown) => {
        if (failure instanceof ApiError && failure.code === 'TREATMENT_NOT_AVAILABLE') {
          setTreatmentId('')
          setReloadKey((key) => key + 1)
        }
        throw failure
      }),
    )
  }

  let chooser
  if (patient !== null) {
    chooser = (
      <p>
        <span>{`Paciente: ${patient.name}`}</span>{' '}
        <button
          type="button"
          className="link-button"
          onClick={() => {
            setPatient(null)
            action.clearError()
          }}
        >
          Cambiar
        </button>
      </p>
    )
  } else if (step === 'new') {
    chooser = (
      <PatientForm
        onSaved={(saved) => {
          setPatient({ id: saved.id, name: listName(saved) })
          setStep('search')
        }}
        onCancel={() => {
          setStep('search')
        }}
      />
    )
  } else {
    chooser = (
      <>
        <PatientSearch onSelect={setPatient} />
        <p className="hint">{ACCENT_NOTE}</p>
        <button
          type="button"
          className="secondary"
          onClick={() => {
            setStep('new')
          }}
        >
          Nuevo paciente
        </button>
      </>
    )
  }

  let treatmentChooser
  if (treatments.status === 'loading') {
    treatmentChooser = <LoadingNotice>Cargando tratamientos…</LoadingNotice>
  } else if (treatments.status === 'error') {
    treatmentChooser = (
      <p role="alert">
        {TREATMENTS_FAILED_MESSAGE}{' '}
        <button
          type="button"
          className="link-button"
          onClick={() => {
            setReloadKey((key) => key + 1)
          }}
        >
          Reintentar
        </button>
      </p>
    )
  } else if (offered.length === 0) {
    treatmentChooser = <p className="hint">{NO_ACTIVE_TREATMENTS_MESSAGE}</p>
  } else {
    treatmentChooser = (
      <label>
        Tratamiento
        <select
          value={treatmentId}
          onChange={(event) => {
            setTreatmentId(event.target.value)
            action.clearError()
          }}
        >
          <option value="">Elegí el tratamiento</option>
          {offered.map((treatment) => (
            <option key={treatment.id} value={treatment.id}>
              {treatment.name}
            </option>
          ))}
        </select>
      </label>
    )
  }

  return (
    <SidePanel
      title={`${dayAndTime(slot.startsAt)}–${formatLocalTime(slot.endsAt)}`}
      onClose={onClose}
    >
      <p>{professionalName}</p>
      {chooser}
      {treatmentChooser}
      {action.error === null ? null : <p role="alert">{action.error}</p>}
      <div className="form-actions">
        <button type="button" disabled={patient === null || chosen === undefined || action.pending} onClick={submit}>
          {BOOK_SUBMIT_LABEL}
        </button>
      </div>
    </SidePanel>
  )
}
