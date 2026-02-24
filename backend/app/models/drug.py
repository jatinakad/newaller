import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, Index, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Drug(Base):
    __tablename__ = "drugs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rxcui: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    generic_name: Mapped[str | None] = mapped_column(String(500))
    dosage_form: Mapped[str | None] = mapped_column(String(100))
    route: Mapped[str | None] = mapped_column(String(100))
    brand_names: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    ndc_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    source: Mapped[str] = mapped_column(String(50), default="OPENFDA")
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    ingredients: Mapped[list["DrugIngredient"]] = relationship(back_populates="drug", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_drugs_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
        Index("idx_drugs_generic_trgm", "generic_name", postgresql_using="gin", postgresql_ops={"generic_name": "gin_trgm_ops"}),
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    chemical_family: Mapped[str | None] = mapped_column(String(200))
    allergen_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    drug_links: Mapped[list["DrugIngredient"]] = relationship(back_populates="ingredient")


class DrugIngredient(Base):
    __tablename__ = "drug_ingredients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="active")  # active, inactive, excipient
    strength: Mapped[str | None] = mapped_column(String(100))

    drug: Mapped["Drug"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="drug_links")

    __table_args__ = (
        UniqueConstraint("drug_id", "ingredient_id", name="uq_drug_ingredient"),
        Index("idx_drug_ingredients_drug", "drug_id"),
        Index("idx_drug_ingredients_ingredient", "ingredient_id"),
    )


class CrossReactivityGroup(Base):
    __tablename__ = "cross_reactivity_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    members: Mapped[list["CrossReactivityMember"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class CrossReactivityMember(Base):
    __tablename__ = "cross_reactivity_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cross_reactivity_groups.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingredients.id"), nullable=False)
    probability: Mapped[str] = mapped_column(String(20), default="high")  # high, moderate, low

    group: Mapped["CrossReactivityGroup"] = relationship(back_populates="members")
    ingredient: Mapped["Ingredient"] = relationship()