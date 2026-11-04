import { useRef, useState, type SyntheticEvent } from 'react'
import { updateProfessional, type Professional } from '../api/professionals'
import { NAME_REQUIRED_MESSAGE, messageForError } from './messages'

/** Ficha del profesional; el administrador puede editar nombre a mostrar y matrícula. */
export function ProfileCard({
  professional,
  editable,
  onSaved,
}: {
  professional: Professional
  editable: boolean
  onSaved: (saved: Professional) => void
}) {
  const [editing, setEditing] = useState(false)
  const [displayName, setDisplayName] = useState(professional.display_name)
  const [licenseNumber, setLicenseNumber] = useState(professional.license_number ?? '')
  const [error, setError] = useState<string | null>(null)
  const inFlight = useRef(false)

  function startEditing() {
    setDisplayName(professional.display_name)
    setLicenseNumber(professional.license_number ?? '')
    setError(null)
    setEditing(true)
  }

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    const name = displayName.trim()
    if (name === '') {
      setError(NAME_REQUIRED_MESSAGE)
      return
    }
    const license = licenseNumber.trim()
    inFlight.current = true
    setError(null)
    try {
      const saved = await updateProfessional(professional.id, {
        display_name: name,
        license_number: license === '' ? null : license,
      })
      onSaved(saved)
      setEditing(false)
    } catch (failure) {
      setError(messageForError(failure))
    } finally {
      inFlight.current = false
    }
  }

  return (
    <header>
      <h2>{professional.display_name}</h2>
      <p>
        Matrícula: {professional.license_number ?? 'Sin matrícula'} ·{' '}
        {professional.active ? 'Activo' : 'Inactivo'}
      </p>
      {editable && !editing ? (
        <button type="button" className="secondary" onClick={startEditing}>
          Editar ficha
        </button>
      ) : null}
      {editing ? (
        <form
          className="user-form"
          onSubmit={(event) => {
            void handleSubmit(event)
          }}
        >
          <label htmlFor="profile-name">Nombre a mostrar</label>
          <input
            id="profile-name"
            value={displayName}
            maxLength={200}
            onChange={(event) => {
              setDisplayName(event.target.value)
            }}
          />
          <label htmlFor="profile-license">Matrícula</label>
          <input
            id="profile-license"
            value={licenseNumber}
            maxLength={50}
            onChange={(event) => {
              setLicenseNumber(event.target.value)
            }}
          />
          {error === null ? null : <p role="alert">{error}</p>}
          <div className="form-actions">
            <button type="submit">Guardar ficha</button>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setEditing(false)
              }}
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : null}
    </header>
  )
}
