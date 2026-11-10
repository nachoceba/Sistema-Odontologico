import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearToken, readToken, saveToken } from "../auth/session";
import { onSessionExpired } from "./client";
import { BASE, jsonResponse, mockApi } from "../test-utils";
import {
  bookOnline,
  confirmOnlineBooking,
  getPublicSlots,
  listPublicProfessionals,
  type OnlineBookingInput,
} from "./publicBooking";
import { ApiError } from "./users";

const DATOS: OnlineBookingInput = {
  professionalId: "p-1",
  startsAt: "2026-11-09T13:30:00Z",
  documentNumber: "40999888",
  firstName: "Lucía",
  lastName: "Díaz",
  email: "lucia@example.com",
  phone: "11 5555-1234",
  website: "",
};

function headersOf(fetchMock: ReturnType<typeof vi.fn>, call = 0): Headers {
  const init = (
    fetchMock.mock.calls[call] as [unknown, RequestInit | undefined]
  )[1];
  return new Headers(init?.headers);
}

beforeEach(() => {
  vi.stubEnv("VITE_API_URL", BASE);
  saveToken("tok-rec");
});

afterEach(() => {
  clearToken();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("cliente público de turnos online", () => {
  it("lista profesionales sin enviar Authorization aunque haya un token guardado", async () => {
    const fetchMock = mockApi({
      "GET /public/professionals": () =>
        jsonResponse([{ id: "p-1", display_name: "Dra. A" }]),
    });

    const result = await listPublicProfessionals();

    expect(result).toEqual([{ id: "p-1", display_name: "Dra. A" }]);
    expect(headersOf(fetchMock).has("Authorization")).toBe(false);
  });

  it("pide las franjas del día con el id y la fecha codificados, sin token", async () => {
    const fetchMock = mockApi({
      "GET /public/professionals/p%201/slots?date=2026-11-09": () =>
        jsonResponse([
          {
            starts_at: "2026-11-09T13:00:00Z",
            ends_at: "2026-11-09T13:30:00Z",
          },
        ]),
    });

    const slots = await getPublicSlots("p 1", "2026-11-09");

    expect(slots).toHaveLength(1);
    expect(headersOf(fetchMock).has("Authorization")).toBe(false);
  });

  it("reserva con el cuerpo de la API (snake_case), campo trampa incluido, sin token", async () => {
    const fetchMock = mockApi({
      "POST /public/appointments": () =>
        jsonResponse(
          {
            starts_at: "2026-11-09T13:30:00Z",
            ends_at: "2026-11-09T14:00:00Z",
            professional_display_name: "Dra. A",
            confirm_before: "2026-11-09T16:00:00Z",
          },
          202,
        ),
    });

    const booked = await bookOnline(DATOS);

    expect(booked.confirm_before).toBe("2026-11-09T16:00:00Z");
    const init = (fetchMock.mock.calls[0] as [unknown, RequestInit])[1];
    expect(JSON.parse(init.body as string)).toEqual({
      professional_id: "p-1",
      starts_at: "2026-11-09T13:30:00Z",
      document_number: "40999888",
      first_name: "Lucía",
      last_name: "Díaz",
      email: "lucia@example.com",
      phone: "11 5555-1234",
      website: "",
    });
    expect(headersOf(fetchMock).has("Authorization")).toBe(false);
  });

  it("omite el teléfono cuando no se escribió", async () => {
    const fetchMock = mockApi({
      "POST /public/appointments": () =>
        jsonResponse(
          {
            starts_at: "a",
            ends_at: "b",
            professional_display_name: "Dra. A",
            confirm_before: "c",
          },
          202,
        ),
    });

    await bookOnline({ ...DATOS, phone: "" });

    const init = (fetchMock.mock.calls[0] as [unknown, RequestInit])[1];
    expect(JSON.parse(init.body as string)).not.toHaveProperty("phone");
  });

  it("confirma con el token en el cuerpo, nunca en la dirección, sin Authorization", async () => {
    const fetchMock = mockApi({
      "POST /public/appointment-confirmations": () =>
        jsonResponse({
          starts_at: "2026-11-09T13:30:00Z",
          ends_at: "2026-11-09T14:00:00Z",
          professional_display_name: "Dra. A",
        }),
    });

    const confirmed = await confirmOnlineBooking("abc123");

    expect(confirmed.professional_display_name).toBe("Dra. A");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).not.toContain("abc123");
    expect(JSON.parse(init.body as string)).toEqual({ token: "abc123" });
    expect(headersOf(fetchMock).has("Authorization")).toBe(false);
  });

  it("un 401 o 403 no cierra la sesión guardada ni avisa a los oyentes", async () => {
    mockApi({
      "GET /public/professionals": () =>
        jsonResponse(
          { error: { code: "NOT_AUTHENTICATED", message: "x" } },
          401,
        ),
    });
    const listener = vi.fn();
    const off = onSessionExpired(listener);

    await expect(listPublicProfessionals()).rejects.toBeInstanceOf(ApiError);

    off();
    expect(listener).not.toHaveBeenCalled();
    expect(readToken()).toBe("tok-rec");
  });

  it("un rechazo de la API llega como ApiError con su código y estado", async () => {
    mockApi({
      "POST /public/appointments": () =>
        jsonResponse(
          {
            error: {
              code: "BOOKING_NOT_POSSIBLE",
              message: "Verifique sus datos ingresados.",
            },
          },
          409,
        ),
    });

    const error = await bookOnline(DATOS).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(409);
    expect((error as ApiError).code).toBe("BOOKING_NOT_POSSIBLE");
  });
});
