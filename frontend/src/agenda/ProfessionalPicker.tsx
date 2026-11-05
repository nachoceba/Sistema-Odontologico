import type { Professional } from '../api/professionals'

interface ProfessionalPickerProps {
  professionals: readonly Professional[]
  selectedId: string
  onChange: (professionalId: string) => void
}

/** Selector de un profesional por vez; las fichas inactivas figuran como "(inactivo)". */
export function ProfessionalPicker({
  professionals,
  selectedId,
  onChange,
}: ProfessionalPickerProps) {
  return (
    <label>
      Profesional{' '}
      <select
        value={selectedId}
        onChange={(event) => {
          onChange(event.target.value)
        }}
      >
        {professionals.map((p) => (
          <option key={p.id} value={p.id}>
            {p.active ? p.display_name : `${p.display_name} (inactivo)`}
          </option>
        ))}
      </select>
    </label>
  )
}
