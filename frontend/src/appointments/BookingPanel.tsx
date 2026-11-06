import { useState } from 'react'
import { bookAppointment } from '../api/appointments'
import { formatLocalTime } from '../agenda/dates'
import { PatientForm } from '../patients/PatientForm'
import { PatientSearch, type SelectedPatient } from '../patients/PatientSearch'
import { listName } from '../patients/messages'
import { ACCENT_NOTE, BOOK_SUBMIT_LABEL, dayAndTime } from './messages'
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
  onBooked: (patientName: string, startsAt: string) => void
  onRejected: () => void
  onClose: () => void
}) {
  const [step, setStep] = useState<Step>('search')
  const [patient, setPatient] = useState<SelectedPatient | null>(null)
  const action = useAppointmentAction({
    onDone: () => {
      if (patient !== null) onBooked(patient.name, slot.startsAt)
    },
    onRejected,
  })

  function submit() {
    if (patient === null) return
    void action.run(() =>
      bookAppointment({ patientId: patient.id, professionalId, startsAt: slot.startsAt }),
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

  return (
    <SidePanel
      title={`${dayAndTime(slot.startsAt)}–${formatLocalTime(slot.endsAt)}`}
      onClose={onClose}
    >
      <p>{professionalName}</p>
      {chooser}
      {action.error === null ? null : <p role="alert">{action.error}</p>}
      <div className="form-actions">
        <button type="button" disabled={patient === null || action.pending} onClick={submit}>
          {BOOK_SUBMIT_LABEL}
        </button>
      </div>
    </SidePanel>
  )
}
