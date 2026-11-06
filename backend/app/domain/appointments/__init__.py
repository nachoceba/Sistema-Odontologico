from app.domain.appointments.errors import AppointmentNotFoundError, SlotTakenError
from app.domain.appointments.ports import (
    AgendaUnitOfWork,
    AppointmentRepository,
    NotificationDispatcher,
    NotificationRepository,
    NotificationSendUnitOfWork,
)
from app.domain.appointments.slots import compute_slots
from app.domain.appointments.transitions import (
    TransitionRejection,
    TransitionResult,
    validate_reschedule_eligibility,
    validate_status_change,
)
from app.domain.appointments.types import (
    Appointment,
    AppointmentStatus,
    ExistingAppointment,
    NewAppointment,
    Notification,
    NotificationKind,
    NotificationStatus,
    RejectionReason,
    Slot,
    SlotStatus,
    TimeOff,
    ValidationResult,
    WorkingHours,
)
from app.domain.appointments.validation import validate_appointment

__all__ = [
    "AgendaUnitOfWork",
    "Appointment",
    "AppointmentNotFoundError",
    "AppointmentRepository",
    "AppointmentStatus",
    "ExistingAppointment",
    "NewAppointment",
    "Notification",
    "NotificationDispatcher",
    "NotificationKind",
    "NotificationRepository",
    "NotificationSendUnitOfWork",
    "NotificationStatus",
    "RejectionReason",
    "Slot",
    "SlotStatus",
    "SlotTakenError",
    "TimeOff",
    "TransitionRejection",
    "TransitionResult",
    "ValidationResult",
    "WorkingHours",
    "compute_slots",
    "validate_appointment",
    "validate_reschedule_eligibility",
    "validate_status_change",
]
