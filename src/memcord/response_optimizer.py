"""Response optimization for token efficiency.

This module provides response compression, formatting, and optimization features
to reduce token usage in MCP responses while maintaining clarity.
"""

from datetime import datetime
from typing import Any

from mcp.types import TextContent


class ResponseOptimizer:
    """Optimizes MCP response content for token efficiency."""

    def __init__(self, compression_threshold: int = 500):
        """Initialize response optimizer.

        Args:
            compression_threshold: Min characters to trigger compression
        """
        self.compression_threshold = compression_threshold

    def optimize_response(self, content: str, mode: str = "auto") -> list[TextContent]:
        """Optimize response content based on size and type.

        Args:
            content: Response content to optimize
            mode: Optimization mode - "auto", "compress", "paginate", "summarize"

        Returns:
            Optimized TextContent list
        """
        if mode == "auto":
            # Auto-select optimization based on content size - more aggressive thresholds
            if len(content) < 200:
                return [TextContent(type="text", text=content)]
            elif len(content) < 800:
                return self._format_compact(content)
            elif len(content) < 2000:
                return self._compress_content(content)  # Use compression earlier
            else:
                return self._compress_content(content)

        elif mode == "compress":
            return self._compress_content(content)
        elif mode == "paginate":
            return self._paginate_content(content)
        elif mode == "summarize":
            return self._summarize_content(content)
        else:
            return [TextContent(type="text", text=content)]

    def _format_compact(self, content: str) -> list[TextContent]:
        """Format content in compact form without compression."""
        # Remove excessive whitespace and newlines
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        # Group related content more aggressively
        compact_lines = []
        for line in lines:
            if line.startswith("•") or line.startswith("-") or line.startswith("*"):
                # Condense consecutive list items on same line
                marker = line[0]
                content_part = line[1:].strip()

                if compact_lines and (
                    compact_lines[-1].startswith(marker)
                    or compact_lines[-1].startswith("•")
                    or compact_lines[-1].startswith("-")
                ):
                    # Add to previous line, separated by pipe
                    compact_lines[-1] += f" | {content_part}"
                else:
                    compact_lines.append(f"{marker} {content_part}")
            else:
                # For regular lines, just strip and add
                compact_lines.append(line)

        optimized_content = "\n".join(compact_lines)
        return [TextContent(type="text", text=optimized_content)]

    def _paginate_content(self, content: str, page_size: int = 1000) -> list[TextContent]:
        """Split content into pages for better readability."""
        pages = []
        lines = content.split("\n")
        current_page = []
        current_size = 0

        for line in lines:
            line_size = len(line) + 1  # +1 for newline

            if current_size + line_size > page_size and current_page:
                # Start new page
                pages.append("\n".join(current_page))
                current_page = [line]
                current_size = line_size
            else:
                current_page.append(line)
                current_size += line_size

        if current_page:
            pages.append("\n".join(current_page))

        # Return paginated content
        if len(pages) == 1:
            return [TextContent(type="text", text=pages[0])]

        result = []
        for i, page in enumerate(pages, 1):
            page_header = f"📄 Page {i}/{len(pages)}\n{'=' * 20}\n"
            result.append(TextContent(type="text", text=page_header + page))

        return result

    def _compress_content(self, content: str) -> list[TextContent]:
        """Compress large content and provide summary."""
        lines = content.split("\n")

        # Extract key lines (headers, important content)
        key_lines = []
        for line in lines[:30]:  # First 30 lines only
            stripped = line.strip()
            if stripped and (
                stripped.startswith(("=", "#", "**", "•", "-", "*")) or len(stripped) > 50
            ):  # Headers or substantial content
                key_lines.append(stripped)

        # Create preview content - limit to reasonable size
        if not key_lines:
            # If no key lines found, show truncated original content
            preview_content = content[:200] + "..." if len(content) > 200 else content
        else:
            preview_content = "\n".join(key_lines[:5])  # Show first 5 key lines only
            if len(key_lines) > 5:
                preview_content += f"\n... {len(key_lines) - 5} more key lines"

        # Ensure preview is not too long
        if len(preview_content) > 500:
            preview_content = preview_content[:500] + "..."

        # Calculate compression stats
        original_size = len(content)
        compressed_size = len(preview_content)
        compression_ratio = ((original_size - compressed_size) / original_size) * 100

        # Format compressed response with required headers
        compressed_response = [
            "📦 Compressed Response",
            "",
            f"Original: {original_size:,} characters ({len(lines)} lines)",
            f"Compressed: {compressed_size:,} characters ({compression_ratio:.1f}% reduction)",
            "",
            "📋 Preview:",
            preview_content,
            "",
            "💡 Use specific search queries for detailed content.",
        ]

        return [TextContent(type="text", text="\n".join(compressed_response))]

    def _summarize_content(self, content: str) -> list[TextContent]:
        """Create a summarized version of the content."""
        lines = content.split("\n")

        # Extract key information
        headers = [line for line in lines if line.startswith(("=", "#", "##", "###", "**"))]
        list_items = [line for line in lines if line.strip().startswith(("•", "-", "*"))][:10]

        # Create summary
        summary_parts = []

        if headers:
            summary_parts.append("📝 Key Sections:")
            summary_parts.extend(headers[:5])  # Top 5 headers
            summary_parts.append("")

        if list_items:
            summary_parts.append("📋 Key Items:")
            summary_parts.extend(list_items)
            summary_parts.append("")

        # Add stats
        stats = [
            "📊 Content Stats:",
            f"• Total lines: {len(lines)}",
            f"• Total characters: {len(content):,}",
            f"• Sections: {len(headers)}",
            f"• List items: {len(list_items)}",
        ]
        summary_parts.extend(stats)

        summary_parts.append("\n💡 Use 'memcord_read' for full content if needed.")

        return [TextContent(type="text", text="\n".join(summary_parts))]

    def optimize_list_response(self, items: list[dict[str, Any]], max_items: int = 10) -> list[TextContent]:
        """Optimize list responses with smart truncation."""
        if len(items) <= max_items:
            # No optimization needed
            return self._format_full_list(items)

        # Show top items + summary
        top_items = items[:max_items]
        remaining = len(items) - max_items

        content_parts = []
        content_parts.append(f"📋 Showing top {max_items} of {len(items)} items:")
        content_parts.append("")

        # Format top items
        for i, item in enumerate(top_items, 1):
            content_parts.append(self._format_list_item(item, i))

        content_parts.append("")
        content_parts.append(f"📄 {remaining} more items available.")
        content_parts.append("💡 Use search filters to narrow results.")

        return [TextContent(type="text", text="\n".join(content_parts))]

    def _format_full_list(self, items: list[dict[str, Any]]) -> list[TextContent]:
        """Format complete list without truncation."""
        content_parts = []

        for i, item in enumerate(items, 1):
            content_parts.append(self._format_list_item(item, i))

        return [TextContent(type="text", text="\n".join(content_parts))]

    def _format_list_item(self, item: dict[str, Any], index: int) -> str:
        """Format individual list item efficiently."""
        # Extract key fields efficiently
        name = item.get("name", item.get("slot_name", f"Item {index}"))

        # Build compact representation
        info_parts = []

        if "entry_count" in item:
            info_parts.append(f"{item['entry_count']} entries")

        if "total_length" in item:
            length = item["total_length"]
            if length > 1000:
                info_parts.append(f"{length // 1000}K chars")
            else:
                info_parts.append(f"{length} chars")

        if "updated_at" in item:
            # Show only date, not full timestamp
            date_str = item["updated_at"][:10]  # YYYY-MM-DD
            info_parts.append(f"updated {date_str}")

        # Format tags compactly
        if "tags" in item and item["tags"]:
            tags_str = ", ".join(item["tags"][:3])  # Show max 3 tags
            if len(item["tags"]) > 3:
                tags_str += f" +{len(item['tags']) - 3}"
            info_parts.append(f"tags: {tags_str}")

        info_text = " • ".join(info_parts) if info_parts else ""
        current_marker = " (current)" if item.get("is_current") else ""

        return f"{index}. {name}{current_marker} - {info_text}"

    def optimize_search_results(self, results: list[dict[str, Any]], query: str) -> list[TextContent]:
        """Optimize search result display."""
        if not results:
            return [TextContent(type="text", text=f"No results for '{query}'")]

        # Group results by type for better organization
        by_type = {}
        for result in results:
            result_type = result.get("match_type", "unknown")
            if result_type not in by_type:
                by_type[result_type] = []
            by_type[result_type].append(result)

        content_parts = []
        content_parts.append(f"🔍 '{query}' → {len(results)} results")
        content_parts.append("")

        # Show results grouped by type
        type_icons = {"slot": "📁", "entry": "📝", "tag": "🏷️", "group": "📂"}

        for result_type, type_results in by_type.items():
            if len(type_results) == 1:
                continue  # Skip type header for single items

            icon = type_icons.get(result_type, "🔍")
            content_parts.append(f"{icon} {result_type.title()} matches ({len(type_results)}):")

        # Format all results efficiently
        for i, result in enumerate(results[:15], 1):  # Limit to 15 results
            match_type = result.get("match_type", "unknown")
            icon = type_icons.get(match_type, "🔍")

            score = result.get("relevance_score", 0)
            slot_name = result.get("slot_name", "Unknown")
            snippet = result.get("snippet", "")[:100]  # Truncate snippets

            if snippet and not snippet.endswith("..."):
                snippet += "..."

            content_parts.append(f"{i}. {icon} {slot_name} ({score:.2f}) - {snippet}")

        if len(results) > 15:
            content_parts.append("")
            content_parts.append(f"📄 {len(results) - 15} more results...")
            content_parts.append("💡 Use filters to narrow search.")

        return [TextContent(type="text", text="\n".join(content_parts))]


def format_size_compact(size_bytes: int) -> str:
    """Format file size in compact form."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024}K"
    else:
        return f"{size_bytes // (1024 * 1024)}M"


def format_timestamp_compact(timestamp: str | datetime) -> str:
    """Format timestamp in compact form."""
    if isinstance(timestamp, str):
        # Extract date part only
        return timestamp[:10]  # YYYY-MM-DD
    elif isinstance(timestamp, datetime):
        return timestamp.strftime("%m/%d")  # MM/DD
    else:
        return str(timestamp)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text efficiently."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
