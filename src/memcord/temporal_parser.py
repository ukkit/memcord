"""Temporal parsing utilities for memory entry selection."""

import re
from datetime import datetime, timedelta


class TemporalParser:
    """Parse relative time expressions and timestamps for memory entry selection."""

    # Relative time patterns
    RELATIVE_PATTERNS = {
        "latest": lambda: datetime.now(),
        "newest": lambda: datetime.now(),
        "recent": lambda: datetime.now(),
        "oldest": lambda: datetime.min,
        "first": lambda: datetime.min,
        "earliest": lambda: datetime.min,
    }

    # Time delta patterns (relative to now)
    TIME_DELTA_PATTERNS = [
        (r"(\d+)\s*minutes?\s*ago", lambda m: datetime.now() - timedelta(minutes=int(m.group(1)))),
        (r"(\d+)\s*hours?\s*ago", lambda m: datetime.now() - timedelta(hours=int(m.group(1)))),
        (r"(\d+)\s*days?\s*ago", lambda m: datetime.now() - timedelta(days=int(m.group(1)))),
        (r"(\d+)\s*weeks?\s*ago", lambda m: datetime.now() - timedelta(weeks=int(m.group(1)))),
        (r"yesterday", lambda m: datetime.now() - timedelta(days=1)),
        (r"last\s*week", lambda m: datetime.now() - timedelta(weeks=1)),
        (r"last\s*month", lambda m: datetime.now() - timedelta(days=30)),
    ]

    # Ordinal patterns
    ORDINAL_PATTERNS = [
        (r"(\d+)(st|nd|rd|th)\s*(latest|newest|recent)", lambda m: ("latest", int(m.group(1)))),
        (r"(\d+)(st|nd|rd|th)\s*(oldest|earliest|first)", lambda m: ("oldest", int(m.group(1)))),
        (r"second\s*(latest|newest)", lambda m: ("latest", 2)),
        (r"third\s*(latest|newest)", lambda m: ("latest", 3)),
        (r"second\s*(oldest|earliest)", lambda m: ("oldest", 2)),
        (r"third\s*(oldest|earliest)", lambda m: ("oldest", 3)),
    ]

    @classmethod
    def parse_timestamp(cls, timestamp_str: str) -> datetime | None:
        """Parse an exact timestamp string."""
        try:
            # Clean up the timestamp string
            timestamp_str = timestamp_str.strip()

            # Handle timezone suffix 'Z' (UTC)
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"

            # Try ISO format first
            if "T" in timestamp_str:
                return datetime.fromisoformat(timestamp_str)

            # Try date-only format
            if "-" in timestamp_str and ":" not in timestamp_str:
                # Parse as date and set time to midnight
                date_part = datetime.strptime(timestamp_str, "%Y-%m-%d")
                return date_part

            # Try other common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
                "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y %H:%M",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue

            return None
        except (ValueError, TypeError):
            return None

    @classmethod
    def parse_relative_time(cls, relative_str: str) -> tuple[str, int | None, datetime | None] | None:
        """
        Parse relative time expression.

        Returns:
            Tuple of (mode, ordinal, target_datetime)
            - mode: 'latest', 'oldest', 'absolute'
            - ordinal: None for simple expressions, int for ordinal (2nd latest, etc.)
            - target_datetime: Specific datetime for time delta expressions
        """
        relative_str = relative_str.lower().strip()

        # Check ordinal patterns first
        for pattern, handler in cls.ORDINAL_PATTERNS:
            match = re.search(pattern, relative_str)
            if match:
                mode, ordinal = handler(match)
                return (mode, ordinal, None)

        # Check simple relative patterns
        if relative_str in cls.RELATIVE_PATTERNS:
            if relative_str in ["latest", "newest", "recent"]:
                return ("latest", None, None)
            else:
                return ("oldest", None, None)

        # Check time delta patterns
        for pattern, handler in cls.TIME_DELTA_PATTERNS:
            match = re.search(pattern, relative_str)
            if match:
                target_time = handler(match)
                return ("absolute", None, target_time)

        return None

    @classmethod
    def find_closest_entry_by_time(
        cls, entries: list, target_time: datetime, tolerance_minutes: int = 30
    ) -> tuple[int, object] | None:
        """
        Find the entry closest to the target time within tolerance.

        Returns:
            Tuple of (index, entry) or None if no match within tolerance
        """
        if not entries:
            return None

        best_match = None
        best_diff = timedelta.max
        best_index = -1

        for i, entry in enumerate(entries):
            time_diff = abs(entry.timestamp - target_time)
            if time_diff < best_diff and time_diff <= timedelta(minutes=tolerance_minutes):
                best_diff = time_diff
                best_match = entry
                best_index = i

        return (best_index, best_match) if best_match else None

    @classmethod
    def get_entry_by_ordinal(cls, entries: list, mode: str, ordinal: int) -> tuple[int, object] | None:
        """
        Get entry by ordinal position (2nd latest, 3rd oldest, etc.).

        Returns:
            Tuple of (index, entry) or None if ordinal is out of range
        """
        if not entries or ordinal < 1 or ordinal > len(entries):
            return None

        if mode == "latest":
            # For latest, we want reverse chronological order
            index = len(entries) - ordinal
            if index >= 0:
                return (index, entries[index])
        elif mode == "oldest":
            # For oldest, we want chronological order
            index = ordinal - 1
            if index < len(entries):
                return (index, entries[index])

        return None

    @classmethod
    def format_time_description(cls, timestamp: datetime) -> str:
        """Format a timestamp into a human-readable description."""
        now = datetime.now()
        diff = now - timestamp

        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "just now"

    @classmethod
    def validate_selection_input(
        cls, timestamp: str | None = None, relative_time: str | None = None, entry_index: int | None = None
    ) -> tuple[bool, str]:
        """
        Validate that exactly one selection method is provided.

        Returns:
            Tuple of (is_valid, error_message)
        """
        provided_methods = sum([timestamp is not None, relative_time is not None, entry_index is not None])

        if provided_methods == 0:
            return (False, "Must provide exactly one of: timestamp, relative_time, or entry_index")
        elif provided_methods > 1:
            return (
                False,
                (
                    "Cannot specify multiple selection methods. Choose only one of: "
                    "timestamp, relative_time, or entry_index"
                ),
            )

        return (True, "")
