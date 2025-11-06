"""
Schema Pydantic schemas for DDL ingestion and schema representation.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class ColumnSchema(BaseModel):
    """Column definition in a table schema."""
    name: str = Field(..., description="Column name")
    dtype: str = Field(..., description="Data type (normalized)")
    nullable: bool = Field(default=True, description="Whether column allows NULL")
    pii_tag: Optional[str] = Field(None, description="PII classification tag")


class CheckConstraint(BaseModel):
    """Check constraint definition."""
    name: Optional[str] = Field(None, description="Constraint name")
    expression: str = Field(..., description="Check constraint expression")


class ForeignKey(BaseModel):
    """Foreign key constraint definition."""
    from_col: str = Field(..., description="Source column name")
    to_table: str = Field(..., description="Target table name")
    to_col: str = Field(..., description="Target column name")


class TableSchema(BaseModel):
    """Table definition with columns and constraints."""
    name: str = Field(..., description="Table name")
    columns: List[ColumnSchema] = Field(default_factory=list, description="Column definitions")
    pk: List[str] = Field(default_factory=list, description="Primary key column names")
    uniques: List[List[str]] = Field(default_factory=list, description="Unique constraint column lists")
    checks: List[CheckConstraint] = Field(default_factory=list, description="Check constraints")
    fks: List[ForeignKey] = Field(default_factory=list, description="Foreign key constraints")


class DAGSchema(BaseModel):
    """Directed Acyclic Graph representation of table dependencies."""
    nodes: List[str] = Field(default_factory=list, description="Table names")
    edges: List[List[str]] = Field(default_factory=list, description="Foreign key edges [from_table, to_table]")


class CanonicalSchema(BaseModel):
    """Canonical schema representation parsed from DDL or JSON."""
    tables: List[TableSchema] = Field(default_factory=list, description="Table definitions")
    dag: DAGSchema = Field(default_factory=DAGSchema, description="Table dependency graph")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")


class SchemaResponse(BaseModel):
    """API response for schema retrieval."""
    id: UUID = Field(..., description="Schema ID")
    source_id: UUID = Field(..., description="Associated source ID")
    schema: CanonicalSchema = Field(..., description="Parsed schema definition")
    dag: DAGSchema = Field(..., description="Table dependency graph")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")
    created_at: datetime = Field(..., description="Schema creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class SourceUploadResponse(BaseModel):
    """Response after uploading and parsing a source file."""
    source_id: UUID = Field(..., description="Created source ID")
    schema_id: UUID = Field(..., description="Created schema ID")
    kind: str = Field(..., description="Source kind (ddl/json)")
    tables_count: int = Field(..., description="Number of tables parsed")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")
