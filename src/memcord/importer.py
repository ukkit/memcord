"""Content import system for various file formats and sources."""

import asyncio
import json
import logging
import mimetypes
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlparse

import aiofiles
import pandas as pd
import pdfplumber
import requests
import trafilatura
from bs4 import BeautifulSoup
from pydantic import BaseModel

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

logger = logging.getLogger(__name__)


class ImportResult(BaseModel):
    """Result of an import operation."""
    success: bool
    content: Optional[str] = None
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None
    source_type: Optional[str] = None
    source_location: Optional[str] = None


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
    
    def _create_metadata(self, source: str, source_type: str, **extra) -> Dict[str, Any]:
        """Create standard import metadata."""
        metadata = {
            "imported_at": datetime.now().isoformat(),
            "source": source,
            "source_type": source_type,
            "importer_version": "1.0.0"
        }
        metadata.update(extra)
        return metadata


class TextFileHandler(ImportHandler):
    """Handler for text files (.txt, .md, etc.)."""
    
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.markdown', '.rst', '.log'}
    
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
                return ImportResult(
                    success=False,
                    error=f"File not found: {source}"
                )
            
            # Read file content
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Get file stats
            stat = path.stat()
            
            metadata = self._create_metadata(
                source=str(path.absolute()),
                source_type="text_file",
                file_size=stat.st_size,
                file_extension=path.suffix,
                encoding="utf-8"
            )
            
            return ImportResult(
                success=True,
                content=content,
                metadata=metadata,
                source_type="text_file",
                source_location=str(path.absolute())
            )
            
        except Exception as e:
            logger.error(f"Error importing text file {source}: {e}")
            return ImportResult(
                success=False,
                error=f"Failed to import text file: {str(e)}"
            )


class PDFHandler(ImportHandler):
    """Handler for PDF documents."""
    
    async def can_handle(self, source: str, **kwargs) -> bool:
        """Check if source is a PDF file."""
        try:
            path = Path(source)
            return path.exists() and path.suffix.lower() == '.pdf'
        except Exception:
            return False
    
    async def import_content(self, source: str, **kwargs) -> ImportResult:
        """Import PDF content using text extraction."""
        try:
            path = Path(source)
            
            if not path.exists():
                return ImportResult(
                    success=False,
                    error=f"PDF file not found: {source}"
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
                return ImportResult(
                    success=False,
                    error="No text content could be extracted from PDF"
                )
            
            # Get file stats
            stat = path.stat()
            
            metadata = self._create_metadata(
                source=str(path.absolute()),
                source_type="pdf",
                file_size=stat.st_size,
                page_count=page_count,
                extraction_method="pdfplumber"
            )
            
            return ImportResult(
                success=True,
                content=content,
                metadata=metadata,
                source_type="pdf",
                source_location=str(path.absolute())
            )
            
        except Exception as e:
            logger.error(f"Error importing PDF {source}: {e}")
            return ImportResult(
                success=False,
                error=f"Failed to import PDF: {str(e)}"
            )


class WebURLHandler(ImportHandler):
    """Handler for web URLs and articles."""
    
    async def can_handle(self, source: str, **kwargs) -> bool:
        """Check if source is a valid web URL."""
        try:
            parsed = urlparse(source)
            return parsed.scheme in ('http', 'https') and parsed.netloc
        except Exception:
            return False
    
    async def import_content(self, source: str, **kwargs) -> ImportResult:
        """Import content from web URL."""
        try:
            # Use requests in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def fetch_url():
                headers = {
                    'User-Agent': 'MemCord Content Importer 1.0'
                }
                response = requests.get(source, headers=headers, timeout=30)
                response.raise_for_status()
                return response
            
            response = await loop.run_in_executor(None, fetch_url)
            
            # Try to extract clean content using trafilatura
            def extract_content():
                return trafilatura.extract(
                    response.text,
                    include_comments=False,
                    include_tables=True,
                    include_formatting=True
                )
            
            clean_content = await loop.run_in_executor(None, extract_content)
            
            if not clean_content:
                # Fallback to BeautifulSoup for basic extraction
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                clean_content = soup.get_text()
            
            if not clean_content or not clean_content.strip():
                return ImportResult(
                    success=False,
                    error="No content could be extracted from URL"
                )
            
            # Try to get page title
            soup = BeautifulSoup(response.text, 'html.parser')
            title = None
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            
            metadata = self._create_metadata(
                source=source,
                source_type="web_url",
                title=title,
                content_type=response.headers.get('content-type'),
                status_code=response.status_code,
                extraction_method="trafilatura"
            )
            
            return ImportResult(
                success=True,
                content=clean_content.strip(),
                metadata=metadata,
                source_type="web_url",
                source_location=source
            )
            
        except requests.RequestException as e:
            logger.error(f"HTTP error importing URL {source}: {e}")
            return ImportResult(
                success=False,
                error=f"Failed to fetch URL: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error importing URL {source}: {e}")
            return ImportResult(
                success=False,
                error=f"Failed to import URL: {str(e)}"
            )


class StructuredDataHandler(ImportHandler):
    """Handler for structured data (JSON, CSV)."""
    
    SUPPORTED_EXTENSIONS = {'.json', '.csv', '.tsv'}
    
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
                return ImportResult(
                    success=False,
                    error=f"File not found: {source}"
                )
            
            extension = path.suffix.lower()
            content = None
            format_info = {}
            
            if extension == '.json':
                # Handle JSON files
                async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                    json_text = await f.read()
                
                data = json.loads(json_text)
                content = json.dumps(data, indent=2, ensure_ascii=False)
                format_info = {
                    "format": "json",
                    "structure": type(data).__name__
                }
                
            elif extension in ('.csv', '.tsv'):
                # Handle CSV/TSV files
                separator = ',' if extension == '.csv' else '\t'
                
                # Read with pandas for better handling
                df = pd.read_csv(path, sep=separator)
                
                # Convert to readable format
                content = f"Dataset with {len(df)} rows and {len(df.columns)} columns:\n\n"
                content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
                content += df.to_string(index=False)
                
                format_info = {
                    "format": "csv" if extension == '.csv' else "tsv",
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist()
                }
            
            # Get file stats
            stat = path.stat()
            
            metadata = self._create_metadata(
                source=str(path.absolute()),
                source_type="structured_data",
                file_size=stat.st_size,
                file_extension=extension,
                **format_info
            )
            
            return ImportResult(
                success=True,
                content=content,
                metadata=metadata,
                source_type="structured_data",
                source_location=str(path.absolute())
            )
            
        except Exception as e:
            logger.error(f"Error importing structured data {source}: {e}")
            return ImportResult(
                success=False,
                error=f"Failed to import structured data: {str(e)}"
            )


class ContentImporter:
    """Main content importer that coordinates different handlers."""
    
    def __init__(self):
        self.handlers: List[ImportHandler] = [
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
        return ImportResult(
            success=False,
            error=f"No suitable import handler found for source: {source}"
        )
    
    async def get_supported_types(self) -> Dict[str, List[str]]:
        """Get information about supported import types."""
        return {
            "text_files": list(TextFileHandler.SUPPORTED_EXTENSIONS),
            "pdf_files": [".pdf"],
            "web_urls": ["http://", "https://"],
            "structured_data": list(StructuredDataHandler.SUPPORTED_EXTENSIONS)
        }