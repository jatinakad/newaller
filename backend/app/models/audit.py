import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # PRESCRIPTION_CHECK, OVERRIDE, PROFILE_ACCESS
    doctor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False)
    facility_id: Mapped[str] = mapped_column(String(100), default="default")
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    overall_signal: Mapped[str | None] = mapped_column(String(10))
    drug_results: Mapped[dict | None] = mapped_column(JSONB)
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    override: Mapped["AuditOverride | None"] = relationship(back_populates="audit_log", uselist=False, cascade="all, delete-orphan")


class AuditOverride(Base):
    __tablename__ = "audit_overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("audit_logs.id", ondelete="CASCADE"), nullable=False)
    overridden_warnings: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    digital_signature: Mapped[str] = mapped_column(Text, nullable=False)
    witness_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    audit_log: Mapped["AuditLog"] = relationship(back_populates="override")