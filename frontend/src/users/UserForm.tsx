import { useRef, useState, type SyntheticEvent } from 'react'
import type { ManagedUser, NewUserInput, UserChanges } from '../api/users'
import type { Role } from '../auth/AuthContext'
import { ROLES, USER_ROLE_LABELS } from './messages'

function RoleSelect({
  id,
  value,
  options,
  disabled = false,
  onChange,
}: {
  id: string
  value: Role
  options: readonly Role[]
  disabled?: boolean
  onChange: (role: Role) => void
}) {
  return (
    <select
      id={id}
      value={value}
      disabled={disabled}
      onChange={(event) => {
        onChange(event.target.value as Role)
      }}
    >
      {options.map((role) => (
        <option key={role} value={role}>
          {USER_ROLE_LABELS[role]}
        </option>
      ))}
    </select>
  )
}

/** Alta: si la cuenta se creó el formulario se vacía; si no, solo se vacía la contraseña. */
export function CreateUserForm({
  onSubmit,
}: {
  onSubmit: (input: NewUserInput) => Promise<boolean>
}) {
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<Role>('receptionist')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [licenseNumber, setLicenseNumber] = useState('')
  const [submitting, setSubmitting] = useState(false)
  // La ref bloquea el segundo envío incluso antes de que React re-renderice el botón.
  const inFlight = useRef(false)

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    inFlight.current = true
    setSubmitting(true)
    const input: NewUserInput = { email, full_name: fullName, role, password }
    if (role === 'dentist') {
      if (displayName.trim() !== '') input.display_name = displayName
      if (licenseNumber.trim() !== '') input.license_number = licenseNumber
    }
    const created = await onSubmit(input)
    inFlight.current = false
    setSubmitting(false)
    setPassword('')
    if (created) {
      setEmail('')
      setFullName('')
      setRole('receptionist')
      setDisplayName('')
      setLicenseNumber('')
    }
  }

  return (
    <form
      aria-label="Alta de usuario"
      className="user-form"
      onSubmit={(event) => {
        void handleSubmit(event)
      }}
    >
      <h2>Nuevo usuario</h2>
      <label htmlFor="new-email">Email</label>
      <input
        id="new-email"
        type="email"
        autoComplete="off"
        required
        maxLength={254}
        value={email}
        onChange={(event) => {
          setEmail(event.target.value)
        }}
      />
      <label htmlFor="new-full-name">Nombre completo</label>
      <input
        id="new-full-name"
        required
        maxLength={200}
        value={fullName}
        onChange={(event) => {
          setFullName(event.target.value)
        }}
      />
      <label htmlFor="new-role">Rol</label>
      <RoleSelect id="new-role" value={role} options={ROLES} onChange={setRole} />
      {role === 'dentist' ? (
        <>
          <label htmlFor="new-display-name">Nombre a mostrar</label>
          <input
            id="new-display-name"
            maxLength={200}
            value={displayName}
            onChange={(event) => {
              setDisplayName(event.target.value)
            }}
          />
          <label htmlFor="new-license">Matrícula</label>
          <input
            id="new-license"
            maxLength={50}
            value={licenseNumber}
            onChange={(event) => {
              setLicenseNumber(event.target.value)
            }}
          />
        </>
      ) : null}
      <label htmlFor="new-password">Contraseña inicial</label>
      <input
        id="new-password"
        type="password"
        autoComplete="new-password"
        required
        maxLength={128}
        aria-describedby="new-password-hint"
        value={password}
        onChange={(event) => {
          setPassword(event.target.value)
        }}
      />
      <p id="new-password-hint" className="hint">
        Entre 8 y 128 caracteres. Entregásela en mano a la persona.
      </p>
      <button type="submit" disabled={submitting}>
        Crear
      </button>
    </form>
  )
}

/** Edición de nombre, email y rol; envía solo lo que cambió. */
export function EditUserForm({
  user,
  isSelf,
  onSubmit,
  onCancel,
}: {
  user: ManagedUser
  isSelf: boolean
  onSubmit: (changes: UserChanges) => Promise<boolean>
  onCancel: () => void
}) {
  const [email, setEmail] = useState(user.email)
  const [fullName, setFullName] = useState(user.full_name)
  const [role, setRole] = useState<Role>(user.role)
  const [submitting, setSubmitting] = useState(false)
  const inFlight = useRef(false)
  // Un odontólogo no cambia de rol (P-4) y nadie cambia el propio (P-5).
  const roleOptions: readonly Role[] = user.role === 'dentist' ? ['dentist'] : ROLES

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    const changes: UserChanges = {}
    if (fullName !== user.full_name) changes.full_name = fullName
    if (email !== user.email) changes.email = email
    if (role !== user.role) changes.role = role
    if (Object.keys(changes).length === 0) {
      onCancel()
      return
    }
    inFlight.current = true
    setSubmitting(true)
    const saved = await onSubmit(changes)
    inFlight.current = false
    setSubmitting(false)
    if (saved) onCancel()
  }

  return (
    <form
      aria-label="Editar usuario"
      className="user-form"
      onSubmit={(event) => {
        void handleSubmit(event)
      }}
    >
      <h2>Editar a {user.full_name}</h2>
      <label htmlFor="edit-full-name">Nombre completo</label>
      <input
        id="edit-full-name"
        required
        maxLength={200}
        value={fullName}
        onChange={(event) => {
          setFullName(event.target.value)
        }}
      />
      <label htmlFor="edit-email">Email</label>
      <input
        id="edit-email"
        type="email"
        required
        maxLength={254}
        value={email}
        onChange={(event) => {
          setEmail(event.target.value)
        }}
      />
      <label htmlFor="edit-role">Rol</label>
      <RoleSelect
        id="edit-role"
        value={role}
        options={roleOptions}
        disabled={isSelf}
        onChange={setRole}
      />
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
