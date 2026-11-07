import { useRef, type MouseEvent } from 'react'
import { Outlet } from 'react-router'
import { AppNav } from './agenda/AppNav'

/** Marco común de las pantallas con sesión: enlace para saltar al contenido, barra y contenido principal. */
export default function AppLayout() {
  const mainRef = useRef<HTMLElement>(null)

  function skipToContent(event: MouseEvent<HTMLAnchorElement>) {
    event.preventDefault()
    mainRef.current?.focus()
  }

  return (
    <>
      <a className="skip-link" href="#contenido" onClick={skipToContent}>
        Saltar al contenido
      </a>
      <AppNav />
      <main id="contenido" className="app-main" tabIndex={-1} ref={mainRef}>
        <Outlet />
      </main>
    </>
  )
}
