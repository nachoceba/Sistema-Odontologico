"""Puerto del repositorio de pacientes (DD-34: ``get`` es el de C-05d, el resto es de C-06)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.patients.types import NewPatient, Patient, PatientChanges, PatientRecord


class PatientRepository(Protocol):
    def get(self, patient_id: str) -> Patient | None:
        """El paciente, o None si no existe (no es un error). Lo usa la agenda (RN-PA-04)."""
        ...

    def get_record(self, patient_id: str) -> PatientRecord | None:
        """La ficha completa, o None si no existe o el identificador no tiene formato valido."""
        ...

    def search(self, *, text: str, include_inactive: bool, limit: int) -> list[PatientRecord]:
        """Pacientes cuyo apellido contiene ``text`` o cuyo documento empieza con el.

        Sin distinguir mayusculas en el apellido; el texto se normaliza como documento para
        comparar con el inicio del documento. Texto en blanco = todos. Solo activos salvo
        ``include_inactive``. Ordenados por apellido, nombre e identificador; hasta ``limit``.
        """
        ...

    def add(self, patient: NewPatient) -> PatientRecord:
        """Guarda un paciente activo. ``DocumentTakenError`` si el documento ya existe."""
        ...

    def update(self, patient_id: str, changes: PatientChanges) -> PatientRecord:
        """Aplica los cambios. ``PatientNotFoundError`` o ``DocumentTakenError`` si corresponde."""
        ...

    def set_active(self, patient_id: str, active: bool) -> PatientRecord:
        """Activa o desactiva (idempotente) sin tocar turnos. ``PatientNotFoundError`` si falta."""
        ...

    def delete(self, patient_id: str) -> bool:
        """Borra definitivamente; False si no existia. Con turnos: PatientHasAppointmentsError."""
        ...
