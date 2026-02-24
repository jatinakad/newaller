import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, ForeignKey, Index, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(20))
    weight_kg: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    allergies: Mapped[list["PatientAllergy"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    lab_sensitivities: Mapped[list["LabSensitivity"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    conditions: Mapped[list["PatientCondition"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class PatientAllergy(Base):
    __tablename__ = "patient_allergies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    allergen_code: Mapped[str | None] = mapped_column(String(50))  # SNOMED CT code
    allergen_name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="drug")  # drug, food, environment, biologic
    criticality: Mapped[str] = mapped_column(String(30), default="high")  # low, high, unable-to-assess
    reaction_manifestations: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    reaction_severity: Mapped[str | None] = mapped_column(String(20))  # mild, moderate, severe
    verification_status: Mapped[str] = mapped_column(String(20), default="confirmed")
    recorded_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patient: Mapped["Patient"] = relationship(back_populates="allergies")

    __table_args__ = (
        Index("idx_patient_allergies_patient", "patient_id"),
        Index("idx_patient_allergies_name", "allergen_name"),
    )


class LabSensitivity(Base):
    __tablename__ = "lab_sensitivities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    test_code: Mapped[str | None] = mapped_column(String(50))  # LOINC code
    test_name: Mapped[str] = mapped_column(String(300), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_range: Mapped[str | None] = mapped_column(String(100))
    interpretation: Mapped[str] = mapped_column(String(20), default="normal")  # normal, elevated, high
    related_substances: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    report_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patient: Mapped["Patient"] = relationship(back_populates="lab_sensitivities")

    __table_args__ = (
        Index("idx_lab_sensitivities_patient", "patient_id"),
    )


class PatientCondition(Base):
    __tablename__ = "patient_conditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    condition_code: Mapped[str | None] = mapped_column(String(50))  # ICD-10 / SNOMED
    condition_name: Mapped[str] = mapped_column(String(300), nullable=False)
    contraindicated_ingredients: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patient: Mapped["Patient"] = relationship(back_populates="conditions")

    __table_args__ = (
        Index("idx_patient_conditions_patient", "patient_id"),
    )