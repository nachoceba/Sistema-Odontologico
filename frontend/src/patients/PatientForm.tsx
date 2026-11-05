import { useRef, useState, type SyntheticEvent } from 'react'
import {
  createPatient,
  updatePatient,
  type NewPatientInput,
  type Patient,
  type PatientChanges,
} from '../api/patients'
import { ApiError } from '../api/users'
import { DOCUMENT_TAKEN_MESSAGE, REQUIRED_MESSAGE, messageForError } from './messages'

type RequiredField = 'first_name' | 'last_name' | 'document_number' | 'email'
type FieldErrors = Partial<Record<RequiredField, string>>

const REQUIRED_FIELDS: readonly RequiredField[] = [
  'first_name',
  'last_name',
  'document_number',
  'email',
]

const ERROR_IDS: Record<RequiredField, string> = {
  first_name: 'patient-first-name-error',
  last_name: 'patient-last-name-error',
  document_number: 'patient-document-error',
  email: 'patient-email-error',
}

function FieldError({ id, message }: { id: string; message: string | undefined }) {
  return message === undefined ? null : (
    <p id={id} className="field-error">
      {message}
    </p>
  )
}

/**
 * Alta (sin `patient`) y edición de un paciente. Hace la llamada a la API y avisa con
 * `onSaved` la ficha guardada, así lo puede usar también la pantalla de turnos (C-10).
 */
export function PatientForm({
  patient,
  onSaved,
  onCancel,
}: {
  patient?: Patient
  onSaved: (saved: Patient) => void
  onCancel: () => void
}) {
  const [firstName, setFirstName] = useState(patient?.first_name ?? '')
  const [lastName, setLastName] = useState(patient?.last_name ?? '')
  const [documentNumber, setDocumentNumber] = useState(patient?.document_number ?? '')
  const [email, setEmail] = useState(patient?.email ?? '')
  const [phone, setPhone] = useState(patient?.phone ?? '')
  const [birthDate, setBirthDate] = useState(patient?.birth_date ?? '')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  // La ref bloquea el segundo envío incluso antes de que React re-renderice el botón.
  const inFlight = useRef(false)

  const values: Record<RequiredField, string> = {
    first_name: firstName,
    last_name: lastName,
    document_number: documentNumber,
    email,
  }

  function changesFor(original: Patient): PatientChanges {
    const changes: PatientChanges = {}
    if (firstName.trim() !== original.first_name) changes.first_name = firstName
    if (lastName.trim() !== original.last_name) changes.last_name = lastName
    if (documentNumber.trim() !== original.document_number) {
      changes.document_number = documentNumber
    }
    if (email.trim() !== original.email) changes.email = email
    if (phone.trim() !== (original.phone ?? '')) {
      changes.phone = phone.trim() === '' ? null : phone
    }
    if (birthDate !== (original.birth_date ?? '')) {
      changes.birth_date = birthDate === '' ? null : birthDate
    }
    return changes
  }

  function newInput(): NewPatientInput {
    const input: NewPatientInput = {
      first_name: firstName,
      last_name: lastName,
      document_number: documentNumber,
      email,
    }
    if (phone.trim() !== '') input.phone = phone
    if (birthDate !== '') input.birth_date = birthDate
    return input
  }

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    setFormError(null)
    const missing: FieldErrors = {}
    for (const field of REQUIRED_FIELDS) {
      if (values[field].trim() === '') missing[field] = REQUIRED_MESSAGE
    }
    setErrors(missing)
    if (Object.keys(missing).length > 0) return

    let changes: PatientChanges | null = null
    if (patient !== undefined) {
      changes = changesFor(patient)
      if (Object.keys(changes).length === 0) {
        onCancel()
        return
      }
    }
    inFlight.current = true
    setSubmitting(true)
    try {
      const saved =
        patient === undefined || changes === null
          ? await createPatient(newInput())
          : await updatePatient(patient.id, changes)
      onSaved(saved)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'DOCUMENT_TAKEN') {
        setErrors({ document_number: DOCUMENT_TAKEN_MESSAGE })
      } else {
        setFormError(messageForError(error))
      }
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }

  function describe(field: RequiredField) {
    const invalid = errors[field] !== undefined
    return {
      'aria-invalid': invalid ? true : undefined,
      'aria-describedby': invalid ? ERROR_IDS[field] : undefined,
    } as const
  }

  const idFor = (field: string) => `patient-${field}`

  return (
    <form
      aria-label={patient === undefined ? 'Alta de paciente' : 'Editar paciente'}
      className="user-form"
      noValidate
      onSubmit={(event) => {
        void handleSubmit(event)
      }}
    >
      <h2>
        {patient === undefined
          ? 'Nuevo paciente'
          : `Editar a ${patient.first_name} ${patient.last_name}`}
      </h2>
      <label htmlFor={idFor('first-name')}>Nombre</label>
      <input
        id={idFor('first-name')}
        maxLength={100}
        value={firstName}
        {...describe('first_name')}
        onChange={(event) => {
          setFirstName(event.target.value)
        }}
      />
      <FieldError id={ERROR_IDS.first_name} message={errors.first_name} />
      <label htmlFor={idFor('last-name')}>Apellido</label>
      <input
        id={idFor('last-name')}
        maxLength={100}
        value={lastName}
        {...describe('last_name')}
        onChange={(event) => {
          setLastName(event.target.value)
        }}
      />
      <FieldError id={ERROR_IDS.last_name} message={errors.last_name} />
      <label htmlFor={idFor('document')}>Documento</label>
      <input
        id={idFor('document')}
        maxLength={40}
        value={documentNumber}
        {...describe('document_number')}
        onChange={(event) => {
          setDocumentNumber(event.target.value)
        }}
      />
      <FieldError id={ERROR_IDS.document_number} message={errors.document_number} />
      <label htmlFor={idFor('email')}>Email</label>
      <input
        id={idFor('email')}
        type="email"
        maxLength={254}
        value={email}
        {...describe('email')}
        onChange={(event) => {
          setEmail(event.target.value)
        }}
      />
      <FieldError id={ERROR_IDS.email} message={errors.email} />
      <label htmlFor={idFor('phone')}>Teléfono</label>
      <input
        id={idFor('phone')}
        maxLength={30}
        value={phone}
        onChange={(event) => {
          setPhone(event.target.value)
        }}
      />
      <label htmlFor={idFor('birth-date')}>Fecha de nacimiento</label>
      <input
        id={idFor('birth-date')}
        type="date"
        value={birthDate}
        onChange={(event) => {
          setBirthDate(event.target.value)
        }}
      />
      {formError === null ? null : <p role="alert">{formError}</p>}
      <div className="form-actions">
        <button type="submit" disabled={submitting}>
          Guardar
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </form>
  )
}
