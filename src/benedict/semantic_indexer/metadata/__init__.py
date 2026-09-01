"""Metadata overlay system module.

Provides content-agnostic metadata generation and reading.
"""

from .content_handlers import (
    ContentHandler,
    CodeHandler,
    ConversationHistoryHandler,
    DocumentHandler,
    DataHandler,
)
from .directory_boost import apply_directory_boost
from .metadata_generator import MetadataGenerator
from .metadata_location import sidecar_path
from .metadata_reader import MetadataReader

__all__ = [
    "ContentHandler",
    "CodeHandler",
    "ConversationHistoryHandler",
    "DocumentHandler",
    "DataHandler",
    "MetadataGenerator",
    "MetadataReader",
    "apply_directory_boost",
    "sidecar_path",
]
