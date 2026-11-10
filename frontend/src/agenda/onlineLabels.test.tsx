import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DayColumn } from "./DayColumn";
import { daySlots, turno } from "./fixtures";
import { buildDayColumn } from "./grid";
import { WeekView } from "./WeekView";

const HOURS = [[9, 13]] as const;
const PENDING = {
  origin: "online",
  created_by: null,
  pending_until: "2026-11-09T16:00:00Z",
} as const;
const CONFIRMED_ONLINE = {
  origin: "online",
  created_by: null,
  pending_until: null,
} as const;

function columnWith(appointment: ReturnType<typeof turno>, busy: string[]) {
  return buildDayColumn({
    date: "2026-11-09",
    slots: daySlots(HOURS, { busy }),
    appointments: [appointment],
    timeOff: [],
    conflicts: [],
  });
}

describe("etiquetas de turnos online en la grilla del día (DD-133)", () => {
  it('un pendiente muestra su franja ocupada y "Pendiente de confirmación" por texto', () => {
    render(
      <DayColumn
        column={columnWith(turno(10, 30, 11, 0, PENDING), ["10:30"])}
      />,
    );

    const row = screen.getByText("Ocupado").closest("li") as HTMLElement;
    expect(
      within(row).getByText("Pendiente de confirmación"),
    ).toBeInTheDocument();
    expect(within(row).getByText("Agendado")).toBeInTheDocument();
    expect(within(row).queryByText("Online")).not.toBeInTheDocument();
  });

  it('un online confirmado muestra "Agendado" y "Online", sin la etiqueta de pendiente', () => {
    render(
      <DayColumn
        column={columnWith(turno(10, 30, 11, 0, CONFIRMED_ONLINE), ["10:30"])}
      />,
    );

    expect(screen.getByText("Agendado")).toBeInTheDocument();
    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(
      screen.queryByText("Pendiente de confirmación"),
    ).not.toBeInTheDocument();
  });

  it("un turno de recepción no lleva ninguna de las dos etiquetas", () => {
    render(<DayColumn column={columnWith(turno(10, 30, 11, 0), ["10:30"])} />);

    expect(screen.getByText("Agendado")).toBeInTheDocument();
    expect(screen.queryByText("Online")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Pendiente de confirmación"),
    ).not.toBeInTheDocument();
  });

  it('un online cancelado conserva la etiqueta "Online" junto a su estado', () => {
    render(
      <DayColumn
        column={columnWith(
          turno(10, 30, 11, 0, { ...CONFIRMED_ONLINE, status: "cancelled" }),
          [],
        )}
      />,
    );

    expect(screen.getByText("Cancelado")).toBeInTheDocument();
    expect(screen.getByText("Online")).toBeInTheDocument();
  });
});

describe("etiquetas de turnos online en la semana", () => {
  it("la semana muestra las etiquetas en el día que corresponde", () => {
    const columns = [columnWith(turno(10, 30, 11, 0, PENDING), ["10:30"])];

    render(
      <WeekView
        columns={columns}
        today="2026-11-09"
        onSelectDay={() => undefined}
      />,
    );

    expect(screen.getByText("Pendiente de confirmación")).toBeInTheDocument();
  });
});
