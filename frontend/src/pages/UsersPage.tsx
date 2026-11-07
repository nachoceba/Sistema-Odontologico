import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  createUser,
  deactivateUser,
  listUsers,
  reactivateUser,
  setPassword,
  updateUser,
  type ManagedUser,
  type NewUserInput,
  type UserChanges,
} from '../api/users'
import { useAuth } from '../auth/useAuth'
import { USER_GONE_CODE, USER_ROLE_LABELS, messageForError } from '../users/messages'
import { PasswordForm } from '../users/PasswordForm'
import { CreateUserForm, EditUserForm } from '../users/UserForm'
import { LoadingNotice } from '../ui/Notices'

type ListState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; users: ManagedUser[] }

async function fetchUsers(): Promise<ListState> {
  try {
    return { status: 'ready', users: await listUsers() }
  } catch (error) {
    return { status: 'error', message: messageForError(error) }
  }
}

function byName(a: ManagedUser, b: ManagedUser): number {
  return a.full_name.localeCompare(b.full_name, 'es', { sensitivity: 'base' })
}

function confirmMessage(user: ManagedUser): string {
  const base = `¿Desactivar a ${user.full_name}?`
  return user.role === 'dentist'
    ? `${base} Sus turnos futuros no se cancelan: recepción debe reprogramarlos o cancelarlos.`
    : base
}

export default function UsersPage() {
  const { user: me } = useAuth()
  const [list, setList] = useState<ListState>({ status: 'loading' })
  const [alertMessage, setAlertMessage] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [editing, setEditing] = useState<ManagedUser | null>(null)
  const [passwordFor, setPasswordFor] = useState<ManagedUser | null>(null)

  useEffect(() => {
    let active = true
    void fetchUsers().then((next) => {
      if (active) setList(next)
    })
    return () => {
      active = false
    }
  }, [])

  const reload = useCallback(() => {
    void fetchUsers().then(setList)
  }, [])

  function applyChange(saved: ManagedUser) {
    setList((current) =>
      current.status === 'ready'
        ? {
            status: 'ready',
            users: current.users.map((u) => (u.id === saved.id ? saved : u)),
          }
        : current,
    )
  }

  /** Muestra el rechazo; si la cuenta ya no existe, recarga la tabla. */
  function fail(error: unknown) {
    setNotice(null)
    setAlertMessage(messageForError(error))
    if (error instanceof ApiError && error.code === USER_GONE_CODE) {
      setEditing(null)
      setPasswordFor(null)
      reload()
    }
  }

  async function handleCreate(input: NewUserInput): Promise<boolean> {
    setAlertMessage(null)
    setNotice(null)
    try {
      const created = await createUser(input)
      setList((current) =>
        current.status === 'ready'
          ? { status: 'ready', users: [...current.users, created].sort(byName) }
          : current,
      )
      return true
    } catch (error) {
      fail(error)
      return false
    }
  }

  async function handleEdit(target: ManagedUser, changes: UserChanges): Promise<boolean> {
    setAlertMessage(null)
    setNotice(null)
    try {
      applyChange(await updateUser(target.id, changes))
      return true
    } catch (error) {
      fail(error)
      return false
    }
  }

  async function handleToggle(target: ManagedUser) {
    if (target.active && !window.confirm(confirmMessage(target))) return
    setAlertMessage(null)
    setNotice(null)
    try {
      applyChange(await (target.active ? deactivateUser(target.id) : reactivateUser(target.id)))
    } catch (error) {
      fail(error)
    }
  }

  async function handlePassword(target: ManagedUser, password: string): Promise<void> {
    setAlertMessage(null)
    setNotice(null)
    try {
      await setPassword(target.id, password)
      setNotice('Contraseña actualizada')
    } catch (error) {
      fail(error)
    }
  }

  return (
    <div className="page page--wide">
      <header className="page-header">
        <h1>Usuarios</h1>
      </header>
      {alertMessage === null ? null : <p role="alert">{alertMessage}</p>}
      {notice === null ? null : <p role="status">{notice}</p>}
      {list.status === 'loading' ? <LoadingNotice /> : null}
      {list.status === 'error' ? <p role="alert">{list.message}</p> : null}
      {list.status === 'ready' ? (
        <div className="table-scroll" role="region" aria-label="Usuarios" tabIndex={0}>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Email</th>
                <th scope="col">Rol</th>
                <th scope="col">Estado</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {list.users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>{USER_ROLE_LABELS[u.role]}</td>
                  <td>{u.active ? 'Activo' : 'Inactivo'}</td>
                  <td className="row-actions">
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => {
                        setEditing(u)
                      }}
                    >
                      Editar
                    </button>
                    {u.id === me?.id ? null : (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => {
                          void handleToggle(u)
                        }}
                      >
                        {u.active ? 'Desactivar' : 'Reactivar'}
                      </button>
                    )}
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => {
                        setNotice(null)
                        setPasswordFor(u)
                      }}
                    >
                      Asignar contraseña
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {editing === null ? null : (
        <EditUserForm
          key={editing.id}
          user={editing}
          isSelf={editing.id === me?.id}
          onSubmit={(changes) => handleEdit(editing, changes)}
          onCancel={() => {
            setEditing(null)
          }}
        />
      )}
      {passwordFor === null ? null : (
        <PasswordForm
          key={passwordFor.id}
          user={passwordFor}
          onSubmit={(password) => handlePassword(passwordFor, password)}
          onCancel={() => {
            setPasswordFor(null)
          }}
        />
      )}
      <CreateUserForm onSubmit={handleCreate} />
    </div>
  )
}
