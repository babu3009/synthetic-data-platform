"""
SQLAlchemy models for the synthetic data platform.
"""
import enum
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, SCHEMA_NAME
from .types import StringArray


class SourceKind(str, enum.Enum):
    """Source data kind enumeration."""
    DDL = "ddl"
    JSON = "json"
    INTROSPECTION = "introspection"


class RequestType(str, enum.Enum):
    """Request type enumeration."""
    RELATIONAL = "relational"
    FLAT = "flat"
    TIMESERIES = "timeseries"


class RequestStatus(str, enum.Enum):
    """Request status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactFormat(str, enum.Enum):
    """Artifact format enumeration."""
    CSV = "csv"
    XLSX = "xlsx"
    PARQUET = "parquet"
    JSONL = "jsonl"
    HTML = "html"


class Project(Base):
    """Project model for organizing synthetic data generation projects."""
    __tablename__ = "projects"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    # New: owner as user FK (prefer this over owner email)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.users.id"), nullable=True, index=True)
    tags = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    # Settings
    webhook_run_status_url = Column(String(2048), nullable=True)
    artifact_ttl_days = Column(Integer, nullable=True)

    # Relationships
    sources = relationship("Source", back_populates="project", cascade="all, delete-orphan")
    requests = relationship("Request", back_populates="project", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="project", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="project", cascade="all, delete-orphan")
    # Optional relationship to owner user for read-only access to email
    owner_user = relationship("User", foreign_keys=[owner_user_id], viewonly=True)

    @property
    def owner(self) -> Optional[str]:
        try:
            return getattr(self.owner_user, "email", None)
        except Exception:
            return None

    def __init__(self, **kwargs):
        # Absorb legacy 'owner' kwarg for backward compatibility
        kwargs.pop("owner", None)
        super().__init__(**kwargs)


class Source(Base):
    """Source data definition for synthetic data generation."""
    __tablename__ = "sources"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=False, index=True)
    kind = Column(String(50), nullable=False, index=True)  # Changed from Enum to String
    storage_uri = Column(String(2048), nullable=False)
    checksum = Column(String(64), nullable=True)  # SHA-256 hash
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="sources")
    schema = relationship("Schema", back_populates="source", uselist=False, cascade="all, delete-orphan")


class Schema(Base):
    """Parsed schema definition from DDL or JSON source."""
    __tablename__ = "schemas"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.sources.id"), nullable=False, unique=True, index=True)
    schema_json = Column(JSONB, nullable=False)
    # schema_json structure:
    # {
    #   "tables": [{
    #     "name": str,
    #     "columns": [{"name": str, "dtype": str, "nullable": bool, "pii_tag": str?}],
    #     "pk": [str],
    #     "uniques": [[str]],
    #     "checks": [{"name": str?, "expression": str}],
    #     "fks": [{"from_col": str, "to_table": str, "to_col": str}]
    #   }],
    #   "dag": {"nodes": [str], "edges": [[str, str]]},
    #   "warnings": [str]
    # }
    dag_json = Column(JSONB, nullable=False)  # Precomputed DAG for quick access
    warnings = Column(StringArray(), default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    source = relationship("Source", back_populates="schema")


class Request(Base):
    """Synthetic data generation request."""
    __tablename__ = "requests"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=False, index=True)
    type = Column(Enum(RequestType, values_callable=lambda e: [m.value for m in e]), nullable=False, index=True)
    status = Column(Enum(RequestStatus, values_callable=lambda e: [m.value for m in e]), default=RequestStatus.PENDING, nullable=False, index=True)
    seed = Column(Integer, nullable=True)
    params_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="requests")
    configs = relationship("Config", back_populates="request", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="request", cascade="all, delete-orphan")


class Config(Base):
    """Configuration for synthetic data generation."""
    __tablename__ = "configs"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.requests.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    body_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    request = relationship("Request", back_populates="configs")


class Artifact(Base):
    """Generated synthetic data artifact."""
    __tablename__ = "artifacts"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.requests.id"), nullable=False, index=True)
    format = Column(Enum(ArtifactFormat, values_callable=lambda e: [m.value for m in e]), nullable=False, index=True)
    storage_uri = Column(String(2048), nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    request = relationship("Request", back_populates="artifacts")


class ApiKey(Base):
    """API key for project access control."""
    __tablename__ = "api_keys"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_key = Column(String(255), nullable=False, unique=True, index=True)
    scopes = Column(StringArray(), default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="api_keys")


class AuditEvent(Base):
    """Audit log for tracking user actions."""
    __tablename__ = "audit_events"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # New optional user actor reference (auth flow)
    actor_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    actor = Column(String(255), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=True, index=True)
    action = Column(String(255), nullable=False, index=True)
    payload_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="audit_events")


class ProjectRole(str, enum.Enum):
    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class ProjectMember(Base):
    """Membership and RBAC role per project for a user (OIDC subject/email)."""
    __tablename__ = "project_members"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=False, index=True)
    # New: membership by concrete user id (preferred; NOT NULL in migration)
    user_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.users.id"), nullable=True, index=True)
    role = Column(Enum(ProjectRole, values_callable=lambda e: [m.value for m in e]), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")

# ---------------- Auth & Onboarding Models ---------------- #

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    PENDING_EMAIL_VERIFICATION = "PENDING_EMAIL_VERIFICATION"
    PENDING_ADMIN_APPROVAL = "PENDING_ADMIN_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=True)
    role = Column(Enum(UserRole, values_callable=lambda e: [m.value for m in e]), nullable=False, default=UserRole.USER, index=True)
    status = Column(Enum(UserStatus, values_callable=lambda e: [m.value for m in e]), nullable=False, default=UserStatus.PENDING_EMAIL_VERIFICATION, index=True)
    profile_image_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class EmailOTPPurpose(str, enum.Enum):
    EMAIL_VERIFY = "email_verify"
    FORGOT_PWD = "forgot_pwd"
    CHANGE_PWD = "change_pwd"

    # Ensure SQLAlchemy / driver bindings use the lowercase .value rather than the Enum name.
    # Without this, str(member) produced the enum qualified name (e.g. 'EmailOTPPurpose.EMAIL_VERIFY'),
    # leading the PostgreSQL enum binder to send 'EMAIL_VERIFY' which is not a valid label.
    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class EmailOTP(Base):
    __tablename__ = "email_otps"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.users.id"), nullable=False, index=True)
    # Revert to native enum; rely on __str__ override + values_callable for consistent lowercase binding
    purpose = Column(Enum(EmailOTPPurpose, name="emailotppurpose", values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True)
    otp_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ---------------- LLM Models ---------------- #


class LLMProviderKind(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    CUSTOM = "custom"

    def __str__(self) -> str:  # pragma: no cover
        return self.value


class LLMTaskType(str, enum.Enum):
    """Task types for which a provider can have distinct default models.

    Keep values lowercase to align with enum/value conventions in this codebase.
    """
    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    TOOLS = "tools"


class LLMProvider(Base):
    __tablename__ = "llm_providers"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Align enum type name with migrations to avoid driver cast issues
    # Use values_callable to ensure lowercase .value strings are bound (avoids uppercase enum names reaching DB)
    kind = Column(Enum(LLMProviderKind, name="llm_provider_kind", values_callable=lambda enum: [e.value for e in enum]), nullable=False, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    base_url = Column(String(1024), nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Denormalized pointer to the current default model for this provider (nullable)
    default_model_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.llm_models.id"), nullable=True, index=True)

    credentials = relationship("LLMCredential", back_populates="provider", cascade="all, delete-orphan")
    # Disambiguate relationship since there are two FKs between providers and models
    models = relationship(
        "LLMModel",
        back_populates="provider",
        cascade="all, delete-orphan",
        foreign_keys="LLMModel.provider_id",
        primaryjoin="LLMProvider.id==LLMModel.provider_id",
    )
    # Optional relationship to the default model record
    default_model = relationship(
        "LLMModel",
        foreign_keys=[default_model_id],
        viewonly=True,
        primaryjoin="LLMProvider.default_model_id==LLMModel.id",
    )


class LLMCredential(Base):
    __tablename__ = "llm_credentials"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.llm_providers.id"), nullable=False, index=True)
    enc_payload_json = Column(Text, nullable=False)  # encrypted/encoded secret payload
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    provider = relationship("LLMProvider", back_populates="credentials")


class LLMModel(Base):
    __tablename__ = "llm_models"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.llm_providers.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    context_tokens = Column(Integer, nullable=True)
    supports_json = Column(Boolean, nullable=False, default=False)
    is_default = Column(Boolean, nullable=False, default=False)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Disambiguate the many-to-one backref to provider
    provider = relationship(
        "LLMProvider",
        back_populates="models",
        foreign_keys=[provider_id],
        primaryjoin="LLMProvider.id==LLMModel.provider_id",
    )


class LLMProviderTaskDefault(Base):
    """Per-task default model selection for an LLM provider.

    Enforces a single default model per (provider, task_type).
    """
    __tablename__ = "llm_provider_task_defaults"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.llm_providers.id"), nullable=False, index=True)
    task_type = Column(Enum(LLMTaskType, name="llm_task_type", values_callable=lambda e: [m.value for m in e]), nullable=False, index=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.llm_models.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    provider = relationship("LLMProvider")
    model = relationship("LLMModel")


class ProjectLLMSetting(Base):
    __tablename__ = "project_llm_settings"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.llm_providers.id"), nullable=True, index=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.llm_models.id"), nullable=True, index=True)
    temperature = Column(Float, nullable=True)
    top_p = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    guardrails_json = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project")
    provider = relationship("LLMProvider")
    model = relationship("LLMModel")