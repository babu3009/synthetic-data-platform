"""
CRUD operations for the synthetic data platform.
"""

from .base import CRUDBase
from .project import project
from .request import request
from .artifact import artifact

__all__ = ["project", "request", "artifact", "CRUDBase"]