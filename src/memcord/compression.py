"""Compression utilities for memory slot optimization."""

import gzip
import json
import zlib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from pydantic import BaseModel, Field


class CompressionMetadata(BaseModel):
    """Metadata about compression operations."""
    
    algorithm: str = Field(..., description="Compression algorithm used")
    original_size: int = Field(..., description="Original size in bytes")
    compressed_size: int = Field(..., description="Compressed size in bytes")
    compression_ratio: float = Field(..., description="Compression ratio (compressed/original)")
    compressed_at: datetime = Field(default_factory=datetime.now, description="When compression was applied")
    compression_level: int = Field(6, description="Compression level used (1-9)")


class CompressionStats(BaseModel):
    """Statistics about compression operations."""
    
    total_slots_processed: int = Field(0, description="Total number of slots processed")
    total_original_size: int = Field(0, description="Total original size in bytes") 
    total_compressed_size: int = Field(0, description="Total compressed size in bytes")
    total_savings: int = Field(0, description="Total bytes saved")
    average_compression_ratio: float = Field(0.0, description="Average compression ratio")
    processing_time_seconds: float = Field(0.0, description="Total processing time")
    slots_compressed: List[str] = Field(default_factory=list, description="Names of compressed slots")
    

class ContentCompressor:
    """Handles compression of memory slot content."""
    
    # Minimum size threshold for compression (in bytes)
    MIN_COMPRESSION_SIZE = 1024  # 1KB
    
    # Default compression level (1-9, where 9 is best compression)
    DEFAULT_COMPRESSION_LEVEL = 6
    
    def __init__(self, compression_threshold: int = None, compression_level: int = None):
        """Initialize compressor with configurable settings."""
        self.compression_threshold = compression_threshold or self.MIN_COMPRESSION_SIZE
        self.compression_level = compression_level or self.DEFAULT_COMPRESSION_LEVEL
    
    def should_compress(self, content: str) -> bool:
        """Determine if content should be compressed based on size."""
        return len(content.encode('utf-8')) >= self.compression_threshold
    
    def compress_text(self, text: str) -> Tuple[bytes, CompressionMetadata]:
        """Compress text content using gzip."""
        original_bytes = text.encode('utf-8')
        original_size = len(original_bytes)
        
        # Compress using gzip
        compressed_bytes = gzip.compress(original_bytes, compresslevel=self.compression_level)
        compressed_size = len(compressed_bytes)
        
        # Calculate compression ratio
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        # Create metadata
        metadata = CompressionMetadata(
            algorithm="gzip",
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            compression_level=self.compression_level
        )
        
        return compressed_bytes, metadata
    
    def decompress_text(self, compressed_data: bytes) -> str:
        """Decompress gzip-compressed text content."""
        try:
            decompressed_bytes = gzip.decompress(compressed_data)
            return decompressed_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decompress content: {e}")
    
    def compress_json_content(self, content: str) -> Tuple[str, CompressionMetadata]:
        """Compress text content and return base64-encoded result."""
        import base64
        
        if not self.should_compress(content):
            # Return original content with metadata indicating no compression
            metadata = CompressionMetadata(
                algorithm="none",
                original_size=len(content.encode('utf-8')),
                compressed_size=len(content.encode('utf-8')),
                compression_ratio=1.0
            )
            return content, metadata
        
        compressed_bytes, metadata = self.compress_text(content)
        
        # Encode as base64 for JSON storage
        compressed_b64 = base64.b64encode(compressed_bytes).decode('ascii')
        
        return compressed_b64, metadata
    
    def decompress_json_content(self, compressed_content: str, metadata: CompressionMetadata) -> str:
        """Decompress base64-encoded compressed content."""
        if metadata.algorithm == "none":
            return compressed_content
        
        import base64
        
        try:
            # Decode from base64
            compressed_bytes = base64.b64decode(compressed_content.encode('ascii'))
            
            # Decompress
            return self.decompress_text(compressed_bytes)
        except Exception as e:
            raise ValueError(f"Failed to decompress JSON content: {e}")
    
    def estimate_compression(self, text: str) -> Dict[str, Any]:
        """Estimate compression results without actually compressing."""
        original_size = len(text.encode('utf-8'))
        
        if not self.should_compress(text):
            return {
                "original_size": original_size,
                "estimated_compressed_size": original_size,
                "estimated_ratio": 1.0,
                "would_compress": False,
                "reason": f"Below threshold ({self.compression_threshold} bytes)"
            }
        
        # Quick compression test using zlib (faster than gzip for estimation)
        test_compressed = zlib.compress(text.encode('utf-8'), level=self.compression_level)
        estimated_size = len(test_compressed)
        estimated_ratio = estimated_size / original_size
        
        return {
            "original_size": original_size,
            "estimated_compressed_size": estimated_size,
            "estimated_ratio": estimated_ratio,
            "would_compress": True,
            "estimated_savings": original_size - estimated_size,
            "estimated_savings_percent": (1 - estimated_ratio) * 100
        }
    
    def get_compression_stats(self, slots_data: List[Dict[str, Any]]) -> CompressionStats:
        """Calculate compression statistics for multiple memory slots."""
        stats = CompressionStats()
        start_time = datetime.now()
        
        total_original = 0
        total_compressed = 0
        processed_slots = []
        
        for slot_data in slots_data:
            slot_name = slot_data.get("slot_name", "unknown")
            
            # Calculate size of all entries in the slot
            slot_original_size = 0
            slot_compressed_size = 0
            
            for entry in slot_data.get("entries", []):
                content = entry.get("content", "")
                estimation = self.estimate_compression(content)
                
                slot_original_size += estimation["original_size"]
                slot_compressed_size += estimation["estimated_compressed_size"]
            
            if slot_original_size > 0:
                total_original += slot_original_size
                total_compressed += slot_compressed_size
                processed_slots.append(slot_name)
        
        # Calculate final statistics
        processing_time = (datetime.now() - start_time).total_seconds()
        
        stats.total_slots_processed = len(processed_slots)
        stats.total_original_size = total_original
        stats.total_compressed_size = total_compressed
        stats.total_savings = total_original - total_compressed
        stats.average_compression_ratio = total_compressed / total_original if total_original > 0 else 1.0
        stats.processing_time_seconds = processing_time
        stats.slots_compressed = processed_slots
        
        return stats


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_compression_report(stats: CompressionStats) -> str:
    """Format compression statistics into a readable report."""
    if stats.total_slots_processed == 0:
        return "No slots processed for compression."
    
    savings_percent = (1 - stats.average_compression_ratio) * 100
    
    report = [
        "# Compression Analysis Report",
        "",
        f"**Slots Processed:** {stats.total_slots_processed}",
        f"**Processing Time:** {stats.processing_time_seconds:.2f} seconds",
        "",
        "## Storage Analysis",
        f"- **Original Size:** {format_size(stats.total_original_size)}",
        f"- **Compressed Size:** {format_size(stats.total_compressed_size)}",
        f"- **Space Saved:** {format_size(stats.total_savings)} ({savings_percent:.1f}%)",
        f"- **Average Compression Ratio:** {stats.average_compression_ratio:.3f}",
        "",
        "## Processed Slots",
    ]
    
    for slot_name in stats.slots_compressed:
        report.append(f"- {slot_name}")
    
    report.extend([
        "",
        "---",
        "*Generated by MemCord Compression Analyzer*"
    ])
    
    return "\n".join(report)