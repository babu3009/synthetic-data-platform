"""Phase 2 synth schemas re-export shim.

Re-export existing Pydantic models used by synth endpoints to keep OpenAPI
stable while co-locating module code.
"""

from app.schemas.schema import (
    CanonicalSchema,
    DAGSchema,
    TableSchema,
    SchemaResponse,
    SourceUploadResponse,
)
from app.schemas.source import (
    Source,
    SourceCreate,
    SourceUpdate,
)
from app.schemas.request import (
    Request,
    RequestCreate,
    RequestUpdate,
)
from app.schemas.artifact import (
    Artifact,
    ArtifactCreate,
    ArtifactUpdate,
)

__all__ = [
    "CanonicalSchema",
    "DAGSchema",
    "TableSchema",
    "SchemaResponse",
    "SourceUploadResponse",
    "Source",
    "SourceCreate",
    "SourceUpdate",
    "Request",
    "RequestCreate",
    "RequestUpdate",
    "Artifact",
    "ArtifactCreate",
    "ArtifactUpdate",
]
