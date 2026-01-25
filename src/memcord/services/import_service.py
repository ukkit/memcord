"""Import service for content import operations.

Extracts business logic from the import handler for better testability
and separation of concerns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..importer import ContentImporter
    from ..storage import StorageManager


@dataclass
class ImportResult:
    """Result of an import operation."""

    success: bool
    slot_name: str = ""
    source: str = ""
    source_type: str = ""
    source_location: str | None = None
    content_length: int = 0
    file_size: int | None = None
    timestamp: datetime | None = None
    tags_applied: list[str] = field(default_factory=list)
    group_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class ImportService:
    """Service for content import operations."""

    def __init__(self, storage: "StorageManager", importer: "ContentImporter"):
        """Initialize import service.

        Args:
            storage: Storage manager for slot operations
            importer: ContentImporter instance
        """
        self.storage = storage
        self.importer = importer

    async def import_content(
        self,
        source: str,
        slot_name: str,
        description: str | None = None,
        tags: list[str] | None = None,
        group_path: str | None = None,
    ) -> ImportResult:
        """Import content from a source into a memory slot.

        Args:
            source: Source path, URL, or '-' for clipboard
            slot_name: Target memory slot name
            description: Optional description
            tags: Optional tags to apply
            group_path: Optional group path

        Returns:
            ImportResult with operation results
        """
        tags = tags or []

        if not source or not source.strip():
            return ImportResult(
                success=False,
                error="Source cannot be empty",
            )

        if not slot_name:
            return ImportResult(
                success=False,
                error="No memory slot selected. Use 'memname' first.",
            )

        try:
            # Import content using the importer
            import_result = await self.importer.import_content(source.strip())

            if not import_result.success:
                return ImportResult(
                    success=False,
                    source=source,
                    error=f"Import failed: {import_result.error}",
                )

            # Prepare content with import metadata
            content_parts = []

            # Add import header
            import_header = (
                f"=== IMPORTED CONTENT ===\n"
                f"Source: {import_result.source_location or source}\n"
                f"Type: {import_result.source_type}\n"
                f"Imported: {import_result.metadata.get('imported_at', 'unknown')}\n"
            )

            if description:
                import_header += f"Description: {description}\n"

            import_header += "========================\n\n"
            content_parts.append(import_header)
            if import_result.content:
                content_parts.append(import_result.content)

            final_content = "".join(content_parts)

            # Save to memory slot
            entry = await self.storage.save_memory(slot_name, final_content)

            # Apply metadata if provided
            if tags or group_path:
                slot = await self.storage.read_memory(slot_name)
                if slot:
                    # Update tags
                    if tags:
                        existing_tags = set(slot.tags or set())
                        existing_tags.update(tags)
                        slot.tags = existing_tags

                    # Update group
                    if group_path:
                        slot.group_path = group_path

                    # Update description
                    if description and not slot.description:
                        slot.description = description

                    # Save updated slot
                    await self.storage._save_slot(slot)

            # Build result with metadata
            result_metadata = dict(import_result.metadata)

            return ImportResult(
                success=True,
                slot_name=slot_name,
                source=source,
                source_type=import_result.source_type or "unknown",
                source_location=import_result.source_location,
                content_length=len(import_result.content) if import_result.content else 0,
                file_size=import_result.metadata.get("file_size"),
                timestamp=entry.timestamp,
                tags_applied=tags,
                group_path=group_path,
                metadata=result_metadata,
            )

        except Exception as e:
            return ImportResult(
                success=False,
                source=source,
                slot_name=slot_name,
                error=str(e),
            )
