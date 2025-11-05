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
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, SCHEMA_NAME


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


class Project(Base):
    """Project model for organizing synthetic data generation projects."""
    __tablename__ = "projects"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    owner = Column(String(255), nullable=False, index=True)
    tags = Column(ARRAY(String), default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    sources = relationship("Source", back_populates="project", cascade="all, delete-orphan")
    requests = relationship("Request", back_populates="project", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="project", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="project", cascade="all, delete-orphan")


class Source(Base):
    """Source data definition for synthetic data generation."""
    __tablename__ = "sources"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=False, index=True)
    kind = Column(Enum(SourceKind), nullable=False, index=True)
    storage_uri = Column(String(2048), nullable=False)
    checksum = Column(String(64), nullable=True)  # SHA-256 hash
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="sources")


class Request(Base):
    """Synthetic data generation request."""
    __tablename__ = "requests"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=False, index=True)
    type = Column(Enum(RequestType), nullable=False, index=True)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False, index=True)
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
    format = Column(Enum(ArtifactFormat), nullable=False, index=True)
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
    scopes = Column(ARRAY(String), default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="api_keys")


class AuditEvent(Base):
    """Audit log for tracking user actions."""
    __tablename__ = "audit_events"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor = Column(String(255), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=True, index=True)
    action = Column(String(255), nullable=False, index=True)
    payload_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="audit_events")