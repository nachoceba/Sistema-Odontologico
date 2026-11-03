import { useRef, useState, type SyntheticEvent } from 'react'
import { Navigate } from 'react-router'
import { useAuth } from '../auth/useAuth'
import { useApiHealth, type ApiHealth } from '../useApiHealth'

const HEALTH_MESSAGES: Record<ApiHealth, string> = {
  unconfigured: 'Falta configurar la URL de la API',
  checking: 'Verificando…',
  up: 'API disponible',
  down: 'API no disponible',
}

const LOGIN_ERRORS = {
  invalid: 'Email o contraseña incorrectos',
  unavailable: 'No se pudo conectar con el servidor',
} as const

export default function LoginPage() {
  const { status, notice, login } = useAuth()
  const health = useApiHealth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  // La ref bloquea el segundo envío incluso antes de que React re-renderice el botón.
  const inFlight = useRef(false)

  if (status === 'authenticated') return <Navigate to="/agenda" replace />

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current) return
    inFlight.current = true
    setSubmitting(true)
    setError(null)
    const result = await login(email, password)
    inFlight.current = false
    setSubmitting(false)
    if (result !== 'ok') setError(LOGIN_ERRORS[result])
  }

  const message = error ?? notice

  return (
    <main className="page">
      <h1>Sistema Odontológico</h1>
      <form
        onSubmit={(event) => {
          void handleSubmit(event)
        }}
        className="login-form"
      >
        <label htmlFor="email">Email</label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(event) => {
            setEmail(event.target.value)
          }}
        />
        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => {
            setPassword(event.target.value)
          }}
        />
        {message === null ? null : <p role="alert">{message}</p>}
        <button type="submit" disabled={submitting}>
          Ingresar
        </button>
      </form>
      <p role="status">{HEALTH_MESSAGES[health]}</p>
    </main>
  )
}
