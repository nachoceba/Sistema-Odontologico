import { request } from "./users";

/** Cliente de la reserva online sin cuenta (C-15): ningún pedido lleva el token ni cierra la sesión. */
const PUBLIC = { auth: false } as const;

/** De un profesional ofrecido, solo identificador y nombre visible. */
export interface PublicProfessional {
  id: string;
  display_name: string;
}

/** De un tratamiento ofrecido, solo identificador y nombre (C-17). */
export interface PublicTreatment {
  id: string;
  name: string;
}

/** Franja reservable de un día local; instantes UTC. */
export interface PublicSlot {
  starts_at: string;
  ends_at: string;
}

export interface OnlineBookingInput {
  professionalId: string;
  treatmentId: string;
  startsAt: string;
  documentNumber: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  /** Campo trampa: una persona lo deja vacío. */
  website: string;
}

/** Respuesta de la reserva: igual para un DNI nuevo y para uno existente. */
export interface OnlineBooking {
  starts_at: string;
  ends_at: string;
  professional_display_name: string;
  confirm_before: string;
  treatment_name: string | null;
}

export interface OnlineConfirmation {
  starts_at: string;
  ends_at: string;
  professional_display_name: string;
  /** null: reserva anterior a los tratamientos (C-17). */
  treatment_name: string | null;
}

export async function listPublicProfessionals(): Promise<PublicProfessional[]> {
  const response = await request(
    "/public/professionals",
    "GET",
    undefined,
    PUBLIC,
  );
  return (await response.json()) as PublicProfessional[];
}

export async function listPublicTreatments(
  professionalId: string,
): Promise<PublicTreatment[]> {
  const response = await request(
    `/public/professionals/${encodeURIComponent(professionalId)}/treatments`,
    "GET",
    undefined,
    PUBLIC,
  );
  return (await response.json()) as PublicTreatment[];
}

export async function getPublicSlots(
  professionalId: string,
  date: string,
): Promise<PublicSlot[]> {
  const response = await request(
    `/public/professionals/${encodeURIComponent(professionalId)}/slots?date=${encodeURIComponent(date)}`,
    "GET",
    undefined,
    PUBLIC,
  );
  return (await response.json()) as PublicSlot[];
}

export async function bookOnline(
  input: OnlineBookingInput,
): Promise<OnlineBooking> {
  const phone = input.phone.trim();
  const body = {
    professional_id: input.professionalId,
    treatment_id: input.treatmentId,
    starts_at: input.startsAt,
    document_number: input.documentNumber,
    first_name: input.firstName,
    last_name: input.lastName,
    email: input.email,
    ...(phone === "" ? {} : { phone }),
    website: input.website,
  };
  const response = await request("/public/appointments", "POST", body, PUBLIC);
  return (await response.json()) as OnlineBooking;
}

/** El token viaja en el cuerpo del `POST`, nunca en la dirección. */
export async function confirmOnlineBooking(
  token: string,
): Promise<OnlineConfirmation> {
  const response = await request(
    "/public/appointment-confirmations",
    "POST",
    { token },
    PUBLIC,
  );
  return (await response.json()) as OnlineConfirmation;
}
