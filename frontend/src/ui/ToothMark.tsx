/** Diente simple y decorativo (D-10): oculto para lectores de pantalla y sin foco. */
export function ToothMark({ pulse = false, large = false }: { pulse?: boolean; large?: boolean }) {
  const classes = ['tooth-mark', large ? 'tooth-mark--large' : '', pulse ? 'tooth-mark--pulse' : '']
    .filter((name) => name !== '')
    .join(' ')

  return (
    <svg
      className={classes}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path
        className="tooth-mark__fill"
        d="M12 6.5c-1.2-1.3-2.8-2-4.5-2C5 4.5 3.5 6.3 3.5 8.7c0 1.8.8 3 1.4 4.7.7 2 .8 4.6 1.5 6 .4.8 1.3.9 1.8.2.8-1.1.9-3.4 1.4-4.4.3-.6.9-.9 1.4-.9s1.1.3 1.4.9c.5 1 .6 3.3 1.4 4.4.5.7 1.4.6 1.8-.2.7-1.4.8-4 1.5-6 .6-1.7 1.4-2.9 1.4-4.7 0-2.4-1.5-4.2-4-4.2-1.7 0-3.3.7-4.5 2z"
      />
    </svg>
  )
}
