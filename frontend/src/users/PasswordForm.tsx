import { useRef, useState, type SyntheticEvent } from 'react'
import type { ManagedUser } from '../api/users'

/** Asigna una contraseña nueva; el campo se vacía siempre al terminar (haya salido bien o mal). */
export function PasswordForm({
  user,
  onSubmit,
  onCancel,
}: {
  user: ManagedUser
  onSubmit: (password: string) => Promise<void>
  onCancel: () => void
}) {
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const inFlight = useRef(false)

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    inFlight.current = true
    setSubmitting(true)
    await onSubmit(password)
    inFlight.current = false
    setSubmitting(false)
    setPassword('')
  }

  return (
    <form
      aria-label="Asignar contraseña"
      className="user-form"
      onSubmit={(event) => {
        void handleSubmit(event)
      }}
    >
      <h2>Contraseña de {user.full_name}</h2>
      <label htmlFor="password-new">Contraseña nueva</label>
      <input
        id="password-new"
        type="password"
        autoComplete="new-password"
        required
        maxLength={128}
        aria-describedby="password-new-hint"
        value={password}
        onChange={(event) => {
          setPassword(event.target.value)
        }}
      />
      <p id="password-new-hint" className="hint">
        Entre 8 y 128 caracteres.
      </p>
      <div className="form-actions">
        <button type="submit" disabled={submitting}>
          Guardar contraseña
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cerrar
        </button>
      </div>
    </form>
  )
}
