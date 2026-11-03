import { useApiHealth, type ApiHealth } from './useApiHealth'

const MESSAGES: Record<ApiHealth, string> = {
  unconfigured: 'Falta configurar la URL de la API',
  checking: 'Verificando…',
  up: 'API disponible',
  down: 'API no disponible',
}

export default function App() {
  const health = useApiHealth()

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', margin: '3rem auto', maxWidth: '40rem', padding: '0 1rem' }}>
      <h1>Sistema Odontológico</h1>
      <p role="status">{MESSAGES[health]}</p>
    </main>
  )
}
