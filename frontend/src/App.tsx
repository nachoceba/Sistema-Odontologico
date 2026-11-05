import { Navigate, Route, Routes } from 'react-router'
import { AuthProvider } from './auth/AuthProvider'
import RequireAuth from './auth/RequireAuth'
import RequireRole from './auth/RequireRole'
import { useAuth } from './auth/useAuth'
import AgendaPage from './pages/AgendaPage'
import LoginPage from './pages/LoginPage'
import PatientsPage from './pages/PatientsPage'
import ProfessionalsPage from './pages/ProfessionalsPage'
import UsersPage from './pages/UsersPage'

function AppRoutes() {
  const { status } = useAuth()
  if (status === 'loading') {
    return (
      <main className="page">
        <p role="status">Cargando…</p>
      </main>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/agenda" element={<AgendaPage />} />
        <Route path="/pacientes" element={<PatientsPage />} />
        <Route path="/profesionales" element={<ProfessionalsPage />} />
        <Route element={<RequireRole roles={['admin']} />}>
          <Route path="/usuarios" element={<UsersPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/agenda" replace />} />
    </Routes>
  )
}

/** Raíz de la app; el router (BrowserRouter o MemoryRouter en tests) lo pone quien la monta. */
export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
