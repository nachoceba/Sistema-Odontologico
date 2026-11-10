"""Casos de uso de la reserva online con repositorios en memoria (spec public-booking, C-15)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest

from app.application.appointments import day_slots
from app.application.public_booking import (
    OnlineBooking,
    book_online,
    confirm_online_booking,
    list_public_professionals,
    list_public_treatments,
    public_day_slots,
)
from app.core.errors import DomainError
from app.core.security import hash_confirmation_token
from app.domain.appointments import (
    AppointmentStatus,
    NewAppointment,
    SlotStatus,
    WorkingHours,
)
from app.domain.appointments.errors import ProfessionalNotFoundError, SlotTakenError
from app.domain.patients.errors import DocumentTakenError
from app.domain.patients.types import NewPatient
from app.domain.public_booking.errors import (
    BookingNotPossibleError,
    ConfirmationLinkInvalidError,
    SlotUnavailableError,
)
from app.domain.treatments.errors import TreatmentNotAvailableError
from app.domain.treatments.types import NewTreatment
from tests.unit.application.agenda_helpers import PROF_A, PROF_B, RECEPTION, World
from tests.unit.domain.appointments.helpers import local, monday

MONDAY_DATE = date(2026, 10, 5)
JUAN_DOC = "30111222"


def make_world(**kwargs: object) -> World:
    """Hoy es el sabado 3/10 a las 10:00 locales; la Dra. A atiende los lunes de 9 a 13."""
    world = World(**kwargs)  # type: ignore[arg-type]
    world.patients.add(NewPatient("Juan", "Pérez", JUAN_DOC, "juan@example.com"))
    return world


def book(
    world: World,
    starts_at: datetime | None = None,
    *,
    document: str = "40999888",
    first: str = "Lucía",
    last: str = "Díaz",
    email: str = "lucia@example.com",
    phone: str | None = None,
    professional: str = PROF_A,
    hold: int = 60,
    treatment: str | None = None,
) -> OnlineBooking:
    return book_online(
        world.public_deps(hold_minutes=hold),
        professional_id=professional,
        treatment_id=treatment or world.treatment_id,
        starts_at=monday(10) if starts_at is None else starts_at,
        document_number=document,
        first_name=first,
        last_name=last,
        email=email,
        phone=phone,
    )


# --- 4.1 Profesionales ofrecidos -----------------------------------------------------------


def test_only_active_professionals_with_hours_are_offered_with_id_and_display_name() -> None:
    world = make_world()

    offered = list_public_professionals(world.public_deps())

    assert [(p.id, p.display_name) for p in offered] == [
        (PROF_B, world.accounts.professionals[PROF_B].display_name),
        (PROF_A, world.accounts.professionals[PROF_A].display_name),
    ]
    assert set(vars(offered[0])) == {"id", "display_name"}


def test_an_inactive_professional_is_not_offered() -> None:
    world = make_world()
    world.set_professional_active(PROF_B, False)

    assert [p.id for p in list_public_professionals(world.public_deps())] == [PROF_A]


def test_an_active_professional_without_working_hours_is_not_offered() -> None:
    world = make_world()
    world.working_hours.replace_for_professional(PROF_B, [])

    assert [p.id for p in list_public_professionals(world.public_deps())] == [PROF_A]


def test_professionals_are_ordered_by_display_name() -> None:
    world = make_world()
    from dataclasses import replace

    world.accounts.professionals[PROF_A] = replace(
        world.accounts.professionals[PROF_A], display_name="Zeta"
    )
    world.accounts.professionals[PROF_B] = replace(
        world.accounts.professionals[PROF_B], display_name="alfa"
    )

    assert [p.display_name for p in list_public_professionals(world.public_deps())] == [
        "alfa",
        "Zeta",
    ]


# --- 4.2 Franjas reservables ---------------------------------------------------------------


def slot_starts(world: World, day: date = MONDAY_DATE) -> list[object]:
    return [s.starts_at for s in public_day_slots(world.public_deps(), PROF_A, day)]


def test_free_slots_skip_the_busy_one() -> None:
    world = make_world()
    world.seed(monday(10))

    starts = slot_starts(world)

    morning = [monday(h, m) for h in (9, 10, 11, 12) for m in (0, 30)]
    afternoon = [monday(h, m) for h in (14, 15, 16, 17) for m in (0, 30)]
    assert starts == [slot for slot in [*morning, *afternoon] if slot != monday(10)]


def test_a_pending_online_appointment_holds_its_slot() -> None:
    world = make_world()
    book(world, monday(11))

    assert monday(11) not in slot_starts(world)
    assert monday(10, 30) in slot_starts(world)


def test_a_cancelled_appointment_frees_its_slot() -> None:
    world = make_world()
    busy = world.seed(monday(10))
    assert monday(10) not in slot_starts(world)

    world.appointments.change_status(busy.id, AppointmentStatus.CANCELLED, "motivo")

    assert monday(10) in slot_starts(world)


def test_the_slot_exactly_at_the_minimum_notice_is_offered_and_one_minute_earlier_is_not() -> None:
    world = make_world()
    world.now = monday(9) - timedelta(hours=6)
    assert slot_starts(world)[0] == monday(9)

    world.now = monday(9) - timedelta(hours=6) + timedelta(minutes=1)
    assert slot_starts(world)[0] == monday(9, 30)


def test_a_time_off_day_has_no_slots() -> None:
    world = make_world()
    world.time_off.add(PROF_A, MONDAY_DATE, MONDAY_DATE)

    assert slot_starts(world) == []


def test_days_beyond_the_horizon_or_in_the_past_are_empty() -> None:
    world = make_world()
    world.now = local(2026, 10, 5, 8)  # lunes
    day_14 = date(2026, 10, 19)
    assert slot_starts(world, day_14) == []
    assert slot_starts(world, date(2026, 10, 12)) != []  # hoy + 7

    world.now = local(2026, 10, 6, 10)  # martes: el lunes 19 es hoy + 13
    assert slot_starts(world, day_14) != []
    assert slot_starts(world, MONDAY_DATE) == []  # el lunes 5 ya paso


def test_a_slot_late_at_night_belongs_to_the_local_day_even_if_it_is_next_day_in_utc() -> None:
    world = make_world()
    world.working_hours.replace_for_professional(
        PROF_A, [WorkingHours(weekday=0, start_time=time(20), end_time=time(22))]
    )

    starts = slot_starts(world)

    assert monday(21, 30) in starts
    assert monday(21, 30).date() > MONDAY_DATE  # en UTC es el martes
    assert slot_starts(world, date(2026, 10, 6)) == []


def test_every_public_slot_is_free_in_the_internal_day_slots() -> None:
    world = make_world()
    world.seed(monday(10))
    book(world, monday(11))

    internal = {
        s.starts_at: s.status for s in day_slots(world.deps(), RECEPTION, PROF_A, MONDAY_DATE)
    }

    public = slot_starts(world)
    assert public
    assert all(internal[start] is SlotStatus.FREE for start in public)  # type: ignore[index]


def test_slots_of_a_professional_not_offered_are_rejected() -> None:
    world = make_world()
    world.set_professional_active(PROF_A, False)

    with pytest.raises(ProfessionalNotFoundError):
        public_day_slots(world.public_deps(), PROF_A, MONDAY_DATE)


# --- 4.3 Reservar: caminos felices ---------------------------------------------------------


def test_a_new_document_creates_the_patient_and_a_pending_appointment() -> None:
    world = make_world()
    world.now = local(2026, 10, 3, 12)

    result = book(world, monday(10), phone="11 5555-1234")

    patient = world.patients.get_by_document("40999888")
    assert patient is not None
    assert (patient.first_name, patient.last_name, patient.email) == (
        "Lucía",
        "Díaz",
        "lucia@example.com",
    )
    assert patient.phone == "11 5555-1234"
    assert patient.active is True
    [saved] = [a for a in world.everything() if a.patient_id == patient.id]
    assert saved.status is AppointmentStatus.SCHEDULED
    assert saved.created_by is None
    assert saved.pending_until == local(2026, 10, 3, 13)
    assert (result.starts_at, result.ends_at, result.confirm_before) == (
        monday(10),
        monday(10, 30),
        local(2026, 10, 3, 13),
    )
    assert result.professional_display_name == world.accounts.professionals[PROF_A].display_name
    assert world.notifications.list_for_appointment(saved.id) == []
    assert world.dispatcher.calls == []


def test_the_verification_is_requested_after_saving_with_the_clear_token() -> None:
    world = make_world()

    book(world, monday(10))

    [saved] = [a for a in world.everything() if a.created_by is None]
    assert world.verification.calls == [(saved.id, "tok-1")]
    # solo el hash esta guardado: confirmar con el token claro funciona
    assert world.appointments.confirm_by_token_hash(hash_confirmation_token("tok-1"), world.now)


def test_the_hold_never_goes_past_the_start_of_the_appointment() -> None:
    world = make_world(min_notice_hours=0)
    world.now = monday(9, 30)

    result = book(world, monday(10), hold=120)

    assert result.confirm_before == monday(10)


def test_an_existing_document_with_the_same_name_links_without_touching_the_record() -> None:
    world = make_world()
    before = world.patients.get_by_document(JUAN_DOC)

    book(world, monday(10), document="30.111.222", first="juan  ", last="PEREZ", email="otro@x.com")

    assert world.patients.get_by_document(JUAN_DOC) == before
    assert len(world.patients.search(text="", include_inactive=True, limit=100)) == 4
    [saved] = [a for a in world.everything() if a.created_by is None]
    assert before is not None
    assert saved.patient_id == before.id
    assert world.verification.calls[0][0] == saved.id


def test_new_and_existing_documents_get_the_same_response() -> None:
    new_world, existing_world = make_world(), make_world()

    first = book(new_world, monday(10))
    second = book(
        existing_world, monday(10), document=JUAN_DOC, first="Juan", last="Perez", email="j@x.com"
    )

    assert first == second


# --- 4.4 Reservar: rechazos ----------------------------------------------------------------


def snapshot(world: World) -> tuple[object, object]:
    return (
        world.patients.search(text="", include_inactive=True, limit=100),
        world.everything(),
    )


def assert_rejected(world: World, error: type[DomainError], **kwargs: object) -> None:
    before = snapshot(world)
    with pytest.raises(error):
        book(world, **kwargs)  # type: ignore[arg-type]
    assert snapshot(world) == before
    assert world.verification.calls == []


def test_a_different_name_for_an_existing_document_is_not_possible() -> None:
    world = make_world()
    assert_rejected(world, BookingNotPossibleError, document=JUAN_DOC, first="Pedro", last="Gómez")


def test_a_different_last_name_alone_is_not_possible() -> None:
    world = make_world()
    assert_rejected(world, BookingNotPossibleError, document=JUAN_DOC, first="Juan", last="Gómez")


def test_an_inactive_patient_is_not_possible_with_the_same_generic_error() -> None:
    world = make_world()
    juan = world.patients.get_by_document(JUAN_DOC)
    assert juan is not None
    world.patients.set_active(juan.id, False)

    assert_rejected(world, BookingNotPossibleError, document=JUAN_DOC, first="Juan", last="Pérez")


def test_a_patient_with_another_appointment_at_that_time_is_not_possible() -> None:
    world = make_world()
    juan = world.patients.get_by_document(JUAN_DOC)
    assert juan is not None
    world.seed(monday(10), patient_id=juan.id, professional_id=PROF_B)

    assert_rejected(world, BookingNotPossibleError, document=JUAN_DOC, first="Juan", last="Pérez")


def test_losing_the_document_race_is_not_possible_and_creates_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = make_world()

    def lose(_patient: NewPatient) -> None:
        raise DocumentTakenError

    monkeypatch.setattr(world.patients, "add", lose)

    assert_rejected(world, BookingNotPossibleError)


def test_a_taken_slot_is_slot_taken_and_leaves_no_patient() -> None:
    world = make_world()
    world.seed(monday(10))

    assert_rejected(world, SlotTakenError, starts_at=monday(10))
    assert world.patients.get_by_document("40999888") is None


def test_losing_the_slot_race_after_creating_the_patient_rolls_the_patient_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = make_world()

    def lose(*_args: object) -> None:
        raise SlotTakenError(PROF_A, monday(10))

    monkeypatch.setattr(world.appointments, "add_pending", lose)

    assert_rejected(world, SlotTakenError)
    assert world.patients.get_by_document("40999888") is None


@pytest.mark.parametrize(
    "starts_at",
    [
        monday(10, 15),  # fuera de la grilla
        monday(20),  # fuera del horario
        monday(9) - timedelta(days=2) + timedelta(hours=1),  # anticipacion insuficiente
        local(2026, 10, 26, 10),  # mas alla del horizonte (hoy + 23)
        local(2026, 10, 5, 10) - timedelta(days=30),  # pasado
    ],
    ids=["grilla", "horario", "anticipacion", "horizonte", "pasado"],
)
def test_a_start_that_is_not_bookable_is_slot_unavailable(starts_at: object) -> None:
    world = make_world()
    assert_rejected(world, SlotUnavailableError, starts_at=starts_at)


def test_a_time_off_day_is_slot_unavailable() -> None:
    world = make_world()
    world.time_off.add(PROF_A, MONDAY_DATE, MONDAY_DATE)
    assert_rejected(world, SlotUnavailableError, starts_at=monday(10))


def test_the_first_day_past_the_horizon_is_slot_unavailable_but_the_last_is_bookable() -> None:
    world = make_world()
    world.now = local(2026, 10, 6, 10)  # martes
    book(world, local(2026, 10, 19, 10))  # hoy + 13
    world.verification.calls.clear()

    world.now = local(2026, 10, 5, 8)  # lunes: el lunes 19 es hoy + 14
    assert_rejected(world, SlotUnavailableError, starts_at=local(2026, 10, 19, 11))


@pytest.mark.parametrize("professional", ["99999999-9999-4999-8999-999999999999", PROF_B])
def test_a_professional_not_offered_is_not_found(professional: str) -> None:
    world = make_world()
    if professional == PROF_B:
        world.set_professional_active(PROF_B, False)
    assert_rejected(world, ProfessionalNotFoundError, professional=professional)


def test_a_professional_without_hours_is_not_found() -> None:
    world = make_world()
    world.working_hours.replace_for_professional(PROF_A, [])
    assert_rejected(world, ProfessionalNotFoundError)


def test_a_failure_to_enqueue_the_verification_keeps_the_appointment() -> None:
    world = make_world()
    world.verification.error = ConnectionError("redis caido")

    result = book(world, monday(10))

    assert result.starts_at == monday(10)
    assert [a for a in world.everything() if a.created_by is None]
    assert world.patients.get_by_document("40999888") is not None


# --- 4.5 Confirmar --------------------------------------------------------------------------


def confirm(world: World, token: str = "tok-1") -> object:
    return confirm_online_booking(world.public_deps(), token)


def test_confirming_in_time_registers_and_dispatches_the_confirmation() -> None:
    world = make_world()
    world.now = local(2026, 10, 3, 12)
    book(world, monday(10))
    world.now = local(2026, 10, 3, 12, 20)

    result = confirm(world)

    [saved] = [a for a in world.everything() if a.created_by is None]
    assert saved.pending_until is None
    assert saved.status is AppointmentStatus.SCHEDULED
    assert (result.starts_at, result.ends_at) == (monday(10), monday(10, 30))  # type: ignore[attr-defined]
    [row] = world.notifications.list_for_appointment(saved.id)
    assert world.dispatcher.calls == [[row]]


def test_a_failing_dispatcher_does_not_undo_the_confirmation() -> None:
    world = make_world()
    book(world, monday(10))
    world.dispatcher.error = ConnectionError("redis caido")

    confirm(world)

    [saved] = [a for a in world.everything() if a.created_by is None]
    assert saved.pending_until is None


def test_a_used_token_does_not_confirm_twice() -> None:
    world = make_world()
    book(world, monday(10))
    confirm(world)

    with pytest.raises(ConfirmationLinkInvalidError):
        confirm(world)
    [saved] = [a for a in world.everything() if a.created_by is None]
    assert len(world.notifications.list_for_appointment(saved.id)) == 1


def test_an_expired_token_is_invalid_and_the_appointment_stays_pending() -> None:
    world = make_world()
    world.now = local(2026, 10, 3, 12)
    book(world, monday(10))
    world.now = local(2026, 10, 3, 13, 1)  # 61 minutos

    with pytest.raises(ConfirmationLinkInvalidError):
        confirm(world)
    [saved] = [a for a in world.everything() if a.created_by is None]
    assert saved.pending_until is not None
    assert world.notifications.list_for_appointment(saved.id) == []


def test_the_last_instant_before_expiry_still_confirms() -> None:
    world = make_world()
    world.now = local(2026, 10, 3, 12)
    book(world, monday(10))
    world.now = local(2026, 10, 3, 12, 59) + timedelta(seconds=59)

    assert confirm(world) is not None


def test_a_cancelled_reservation_cannot_be_confirmed() -> None:
    world = make_world()
    book(world, monday(10))
    [saved] = [a for a in world.everything() if a.created_by is None]
    world.appointments.change_status(saved.id, AppointmentStatus.CANCELLED, "motivo")

    with pytest.raises(ConfirmationLinkInvalidError):
        confirm(world)


def test_an_unknown_token_and_the_stored_hash_are_invalid() -> None:
    world = make_world()
    book(world, monday(10))

    with pytest.raises(ConfirmationLinkInvalidError):
        confirm(world, "otro-token")
    with pytest.raises(ConfirmationLinkInvalidError):
        confirm(world, hash_confirmation_token("tok-1"))


def test_a_started_appointment_cannot_be_confirmed() -> None:
    world = make_world(min_notice_hours=0)
    world.now = monday(9, 30)
    book(world, monday(10), hold=120)
    world.now = monday(10)

    with pytest.raises(ConfirmationLinkInvalidError):
        confirm(world)


# --- Tratamiento (C-17, DD-141, DD-142) ----------------------------------------------------


def test_a_professional_without_active_treatments_is_not_offered() -> None:
    world = make_world()
    world.treatments.replace_for_professional(PROF_B, [])

    assert [p.id for p in list_public_professionals(world.public_deps())] == [PROF_A]


def test_a_professional_whose_only_treatment_is_inactive_is_not_offered() -> None:
    world = make_world()
    world.treatments.replace_for_professional(PROF_B, [world.consulta.id])
    world.treatments.update(world.consulta.id, active=False)

    assert [p.id for p in list_public_professionals(world.public_deps())] == [PROF_A]


def test_slots_and_treatments_of_a_professional_without_active_treatments_are_not_found() -> None:
    world = make_world()
    world.treatments.replace_for_professional(PROF_A, [])

    with pytest.raises(ProfessionalNotFoundError):
        public_day_slots(world.public_deps(), PROF_A, MONDAY_DATE)
    with pytest.raises(ProfessionalNotFoundError):
        list_public_treatments(world.public_deps(), PROF_A)


def test_public_treatments_are_the_assigned_active_ones_ordered_by_name() -> None:
    world = make_world()
    blanqueamiento = world.treatments.add(NewTreatment("Blanqueamiento"))
    world.treatments.replace_for_professional(
        PROF_A, [world.limpieza.id, world.consulta.id, blanqueamiento.id]
    )
    world.treatments.update(blanqueamiento.id, active=False)

    offered = list_public_treatments(world.public_deps(), PROF_A)

    assert [(t.id, t.name) for t in offered] == [
        (world.consulta.id, "Consulta"),
        (world.limpieza.id, "Limpieza dental"),
    ]
    assert set(vars(offered[0])) == {"id", "name"}


def test_each_professional_gets_only_their_own_treatments() -> None:
    world = make_world()
    assert [t.name for t in list_public_treatments(world.public_deps(), PROF_B)] == ["Consulta"]
    assert [t.name for t in list_public_treatments(world.public_deps(), PROF_A)] == [
        "Consulta",
        "Limpieza dental",
    ]


def test_public_treatments_of_a_professional_not_offered_are_rejected() -> None:
    world = make_world()
    world.set_professional_active(PROF_A, False)
    with pytest.raises(ProfessionalNotFoundError):
        list_public_treatments(world.public_deps(), PROF_A)


def test_booking_with_a_treatment_saves_it_and_answers_with_its_name() -> None:
    world = make_world()

    result = book(world, monday(10), treatment=world.limpieza.id)

    [saved] = [a for a in world.everything() if a.created_by is None]
    assert saved.treatment_id == world.limpieza.id
    assert result.treatment_name == "Limpieza dental"
    assert (result.starts_at, result.ends_at) == (monday(10), monday(10, 30))


def test_new_and_existing_documents_get_the_same_treatment_name() -> None:
    new_world, existing_world = make_world(), make_world()

    first = book(new_world, monday(10), treatment=new_world.limpieza.id)
    second = book(
        existing_world,
        monday(10),
        document=JUAN_DOC,
        first="Juan",
        last="Perez",
        email="j@x.com",
        treatment=existing_world.limpieza.id,
    )

    assert first.treatment_name == second.treatment_name == "Limpieza dental"


def test_an_unknown_treatment_is_not_available_and_creates_nothing() -> None:
    world = make_world()
    assert_rejected(world, TreatmentNotAvailableError, treatment="no-existe")
    assert world.patients.get_by_document("40999888") is None


def test_an_inactive_treatment_is_not_available_and_creates_nothing() -> None:
    world = make_world()
    world.treatments.update(world.limpieza.id, active=False)
    assert_rejected(world, TreatmentNotAvailableError, treatment=world.limpieza.id)
    assert world.patients.get_by_document("40999888") is None


def test_a_treatment_of_another_professional_is_not_available_even_for_an_existing_patient() -> (
    None
):
    world = make_world()
    # El Dr. B no ofrece "Limpieza dental": mismo error que con un DNI nuevo (DD-129).
    assert_rejected(
        world,
        TreatmentNotAvailableError,
        professional=PROF_B,
        treatment=world.limpieza.id,
        document=JUAN_DOC,
        first="Juan",
        last="Perez",
    )


def test_the_treatment_is_checked_before_the_slot() -> None:
    world = make_world()
    world.treatments.update(world.limpieza.id, active=False)
    # 10:15 no es una franja reservable, pero el tratamiento se chequea antes.
    assert_rejected(
        world, TreatmentNotAvailableError, starts_at=monday(10, 15), treatment=world.limpieza.id
    )


def test_a_professional_not_offered_wins_over_a_bad_treatment() -> None:
    world = make_world()
    world.set_professional_active(PROF_A, False)
    assert_rejected(world, ProfessionalNotFoundError, treatment="no-existe")


def test_the_treatment_does_not_change_the_duration_or_the_free_slots() -> None:
    world = make_world()
    book(world, monday(10), treatment=world.consulta.id)
    book(
        world,
        monday(10, 30),
        document="40111000",
        email="otra@example.com",
        treatment=world.limpieza.id,
    )

    assert monday(10) not in slot_starts(world)
    assert monday(10, 30) not in slot_starts(world)
    assert monday(11) in slot_starts(world)
    assert {a.ends_at - a.starts_at for a in world.everything()} == {timedelta(minutes=30)}


def test_confirming_answers_with_the_treatment_name() -> None:
    world = make_world()
    world.now = local(2026, 10, 3, 12)
    book(world, monday(10), treatment=world.limpieza.id)
    world.now = local(2026, 10, 3, 12, 20)

    result = confirm(world)

    assert result.treatment_name == "Limpieza dental"  # type: ignore[attr-defined]


def test_confirming_still_works_after_the_treatment_was_deactivated() -> None:
    world = make_world()
    world.now = local(2026, 10, 3, 12)
    book(world, monday(10), treatment=world.limpieza.id)
    world.treatments.update(world.limpieza.id, active=False)
    world.treatments.replace_for_professional(PROF_A, [world.consulta.id])
    world.now = local(2026, 10, 3, 12, 20)

    result = confirm(world)

    assert result.treatment_name == "Limpieza dental"  # type: ignore[attr-defined]
    [saved] = [a for a in world.everything() if a.created_by is None]
    assert saved.pending_until is None


def test_confirming_an_old_reservation_without_treatment_has_no_treatment_name() -> None:
    world = make_world()
    world.now = local(2026, 10, 3, 12)
    old = world.appointments.add_pending(
        NewAppointment("pac-1", PROF_A, monday(10), monday(10, 30), None),
        hash_confirmation_token("tok-viejo"),
        local(2026, 10, 3, 13),
    )
    assert old.treatment_id is None

    result = confirm(world, "tok-viejo")

    assert result.treatment_name is None  # type: ignore[attr-defined]
