import { useRef, useState } from 'react'
import { messageForAppointmentError, shouldReloadAfter } from './messages'

/**
 * Envía una acción una sola vez a la vez (la ref bloquea el segundo clic antes de que React
 * vuelva a dibujar), guarda el error ya traducido y avisa éxito o rechazo con código (P-7).
 */
export function useAppointmentAction<T>({
  onDone,
  onRejected,
}: {
  onDone: (result: T) => void
  onRejected: () => void
}) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inFlight = useRef(false)

  async function run(action: () => Promise<T>): Promise<void> {
    if (inFlight.current) return
    inFlight.current = true
    setPending(true)
    setError(null)
    try {
      onDone(await action())
    } catch (failure) {
      setError(messageForAppointmentError(failure))
      if (shouldReloadAfter(failure)) onRejected()
    } finally {
      inFlight.current = false
      setPending(false)
    }
  }

  return { run, pending, error, clearError: () => { setError(null) } }
}
