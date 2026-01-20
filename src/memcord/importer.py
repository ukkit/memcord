"""Content import system for various file formats and sources."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiofiles
import pandas as pd
import pdfplumber
import requests
import trafilatura
from bs4 import BeautifulSoup
from pydantic import BaseModel

from .security import InputValidator

HAS_MAGIC = False

logger = logging.getLogger(__name__)

# Maximum file size for imports (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class ImportResult(BaseModel):
    """Result of an import operation."""

    success: bool
    content: str | None = None
    metadata: dict[str, Any] = {}
    error: str | None = None
    source_type: str | None = None
    source_location: str | None = None


class ImportHandler(ABC):
    """Base class for content import handlers."""

    @abstractmethod
    async def can_handle(self, source: str, **kwargs) -> bool:
        """Check if this handler can process the given source."""
        pass

    @abstractmethod
    async def import_content(self, source: str, **kwargs) -> ImportResult:
        """Import content from the source."""
        pass

    def _create_metadata(self, source: str, source_type: str, **extra) -> dict[str, Any]:
        """Create standard import metadata."""
        metadata = {
            "imported_at": datetime.now().isoformat(),
            "source": source,
            "source_type": source_type,
            "importer_version": "1.0.0",
        }
        metadata.update(extra)
        return metadata


class TextFileHandler(ImportHandler):
    """Handler for text files (.txt, .md, etc.)."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".log"}

    async def can_handle(self, source: str, **kwargs) -> bool:
        """Check if source is a supported text file."""
        try:
            path = Path(source)
            return path.exists() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        except Exception:
            return False

    async def import_content(self, source: str, **kwargs) -> ImportResult:
        """Import text file content."""
        try:
            path = Path(source)

            if not path.exists():
                return ImportResult(success=False, error=f"File not found: {source}")

            # Check file size before reading
            stat = path.stat()
            if stat.st_size > MAX_FILE_SIZE:
                return ImportResult(
                    success=False,
                    error=f"File too large: {_format_size(stat.st_size)} (max {_format_size(MAX_FILE_SIZE)})",
                )

            # Read file content
            async with aiofiles.open(path, encoding="utf-8") as f:
                content = await f.read()

            metadata = self._create_metadata(
                source=str(path.absolute()),
                source_type="text_file",
                file_size=stat.st_size,
                file_extension=path.suffix,
                encoding="utf-8",
            )

            return ImportResult(
                success=True,
                content=content,
                metadata=metadata,
                source_type="text_file",
                source_location=str(path.absolute()),
            )

        except Exception as e:
            logger.error(f"Error importing text file {source}: {e}")
            return ImportResult(success=False, error=f"Failed to import text file: {str(e)}")


class PDFHandler(ImportHandler):
    """Handler for PDF documents."""

    async def can_handle(self, source: str, **kwargs) -> bool:
        """Check if source is a PDF file."""
        try:
            path = Path(source)
            return path.exists() and path.suffix.lower() == ".pdf"
        except Exception:
            return False

    async def import_content(self, source: str, **kwargs) -> ImportResult:
        """Import PDF content using text extraction."""
        try:
            path = Path(source)

            if not path.exists():
                return ImportResult(success=False, error=f"PDF file not found: {source}")

            # Check file size before processing
            stat = path.stat()
            if stat.st_size > MAX_FILE_SIZE:
                return ImportResult(
                    success=False,
                    error=f"PDF file too large: {_format_size(stat.st_size)} (max {_format_size(MAX_FILE_SIZE)})",
                )

            # Extract text from PDF
            text_content = []
            page_count = 0

            with pdfplumber.open(path) as pdf:
                page_count = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(f"--- Page {page_num} ---\n{page_text}")

            content = "\n\n".join(text_content)

            if not content.strip():
                return ImportResult(success=False, error="No text content could be extracted from PDF")

            # Get file stats
            stat = path.stat()

            metadata = self._create_metadata(
                source=str(path.absolute()),
                source_type="pdf",
                file_size=stat.st_size,
                page_count=page_count,
                extraction_method="pdfplumber",
            )

            return ImportResult(
                success=True,
                content=content,
                metadata=metadata,
                source_type="pdf",
                source_location=str(path.absolute()),
            )

        except Exception as e:
            logger.error(f"Error importing PDF {source}: {e}")
            return ImportResult(success=False, error=f"Failed to import PDF: {str(e)}")


class WebURLHandler(ImportHandler):
    """Handler for web URLs and articles."""

    async def can_handle(self, source: str, **kwargs) -> bool:
        """Check if source is a valid web URL."""
        try:
            parsed = urlparse(source)
            return parsed.scheme in ("http", "https") and parsed.netloc
        except Exception:
            return False

    async def import_content(self, source: str, **kwargs) -> ImportResult:
        """Import content from web URL."""
        # Maximum response size (10 MB)
        MAX_RESPONSE_SIZE = 10 * 1024 * 1024

        try:
            # Validate URL for security (SSRF protection)
            is_valid, error_msg = InputValidator.validate_url(source)
            if not is_valid:
                logger.warning(f"URL validation failed for '{source}': {error_msg}")
                return ImportResult(success=False, error=f"URL validation failed: {error_msg}")

            # Use requests in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def fetch_url():
                headers = {"User-Agent": "MemCord Content Importer 1.0"}
                # Use streaming to check content-length before downloading
                response = requests.get(source, headers=headers, timeout=30, stream=True)
                response.raise_for_status()

                # Check Content-Length header if available
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_RESPONSE_SIZE:
                    response.close()
                    raise ValueError(f"Response too large: {int(content_length)} bytes (max {MAX_RESPONSE_SIZE})")

                # Read content with size limit
                content_chunks = []
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    total_size += len(chunk)
                    if total_size > MAX_RESPONSE_SIZE:
                        response.close()
                        raise ValueError(f"Response exceeded max size of {MAX_RESPONSE_SIZE} bytes")
                    content_chunks.append(chunk)

                # Reconstruct response content
                response._content = b"".join(content_chunks)
                return response

            response = await loop.run_in_executor(None, fetch_url)

            # Try to extract clean content using trafilatura
            def extract_content():
                return trafilatura.extract(
                    response.text, include_comments=False, include_tables=True, include_formatting=True
                )

            clean_content = await loop.run_in_executor(None, extract_content)

            if not clean_content:
                # Fallback to BeautifulSoup for basic extraction
                soup = BeautifulSoup(response.text, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                clean_content = soup.get_text()

            if not clean_content or not clean_content.strip():
                return ImportResult(success=False, error="No content could be extracted from URL")

            # Try to get page title
            soup = BeautifulSoup(response.text, "html.parser")
            title = None
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            metadata = self._create_metadata(
                source=source,
                source_type="web_url",
                title=title,
                content_type=response.headers.get("content-type"),
                status_code=response.status_code,
                extraction_method="trafilatura",
            )

            return ImportResult(
                success=True,
                content=clean_content.strip(),
                metadata=metadata,
                source_type="web_url",
                source_location=source,
            )

        except requests.RequestException as e:
            logger.error(f"HTTP error importing URL {source}: {e}")
            return ImportResult(success=False, error=f"Failed to fetch URL: {str(e)}")
        except Exception as e:
            logger.error(f"Error importing URL {source}: {e}")
            return ImportResult(success=False, error=f"Failed to import URL: {str(e)}")


class StructuredDataHandler(ImportHandler):
    """Handler for structured data (JSON, CSV)."""

    SUPPORTED_EXTENSIONS = {".json", ".csv", ".tsv"}

    async def can_handle(self, source: str, **kwargs) -> bool:
        """Check if source is a supported structured data file."""
        try:
            path = Path(source)
            return path.exists() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        except Exception:
            return False

    async def import_content(self, source: str, **kwargs) -> ImportResult:
        """Import structured data content."""
        try:
            path = Path(source)

            if not path.exists():
                return ImportResult(success=False, error=f"File not found: {source}")

            # Check file size before processing
            stat = path.stat()
            if stat.st_size > MAX_FILE_SIZE:
                return ImportResult(
                    success=False,
                    error=f"File too large: {_format_size(stat.st_size)} (max {_format_size(MAX_FILE_SIZE)})",
                )

            extension = path.suffix.lower()
            content = None
            format_info = {}

            if extension == ".json":
                # Handle JSON files
                async with aiofiles.open(path, encoding="utf-8") as f:
                    json_text = await f.read()

                data = json.loads(json_text)
                content = json.dumps(data, indent=2, ensure_ascii=False)
                format_info = {"format": "json", "structure": type(data).__name__}

            elif extension in (".csv", ".tsv"):
                # Handle CSV/TSV files
                separator = "," if extension == ".csv" else "\t"

                # Read with pandas for better handling
                df = pd.read_csv(path, sep=separator)

                # Convert to readable format
                content = f"Dataset with {len(df)} rows and {len(df.columns)} columns:\n\n"
                content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
                content += df.to_string(index=False)

                format_info = {
                    "format": "csv" if extension == ".csv" else "tsv",
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist(),
                }

            # Get file stats
            stat = path.stat()

            metadata = self._create_metadata(
                source=str(path.absolute()),
                source_type="structured_data",
                file_size=stat.st_size,
                file_extension=extension,
                **format_info,
            )

            return ImportResult(
                success=True,
                content=content,
                metadata=metadata,
                source_type="structured_data",
                source_location=str(path.absolute()),
            )

        except Exception as e:
            logger.error(f"Error importing structured data {source}: {e}")
            return ImportResult(success=False, error=f"Failed to import structured data: {str(e)}")


class ContentImporter:
    """Main content importer that coordinates different handlers."""

    def __init__(self):
        self.handlers: list[ImportHandler] = [
            TextFileHandler(),
            PDFHandler(),
            WebURLHandler(),
            StructuredDataHandler(),
        ]

    async def import_content(self, source: str, **kwargs) -> ImportResult:
        """Import content from various sources."""
        # Find appropriate handler
        for handler in self.handlers:
            if await handler.can_handle(source, **kwargs):
                logger.info(f"Using {handler.__class__.__name__} for {source}")
                return await handler.import_content(source, **kwargs)

        # No handler found
        return ImportResult(success=False, error=f"No suitable import handler found for source: {source}")

    async def get_supported_types(self) -> dict[str, list[str]]:
        """Get information about supported import types."""
        return {
            "text_files": list(TextFileHandler.SUPPORTED_EXTENSIONS),
            "pdf_files": [".pdf"],
            "web_urls": ["http://", "https://"],
            "structured_data": list(StructuredDataHandler.SUPPORTED_EXTENSIONS),
        }
