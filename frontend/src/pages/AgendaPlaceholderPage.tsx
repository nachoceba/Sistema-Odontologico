import { Link } from 'react-router'
import { ROLE_LABELS } from '../auth/AuthContext'
import { useAuth } from '../auth/useAuth'

/** Página provisoria hasta que exista la agenda (C-10). */
export default function AgendaPlaceholderPage() {
  const { user, logout } = useAuth()
  if (user === null) return null

  return (
    <main className="page">
      <h1>Agenda</h1>
      <p>Hola, {user.full_name}</p>
      <p>{ROLE_LABELS[user.role]}</p>
      {user.role === 'admin' ? <Link to="/usuarios">Usuarios</Link> : null}
      <button type="button" onClick={logout}>
        Salir
      </button>
    </main>
  )
}
