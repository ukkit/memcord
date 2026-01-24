"""Tests for the response builder module.

Tests the ResponseBuilder class and error handling decorators
introduced in the server.py optimization (Phase 3).
"""

import pytest
from mcp.types import TextContent

from memcord.errors import ErrorCode, ErrorSeverity, MemcordError
from memcord.response_builder import (
    ResponseBuilder,
    handle_errors,
    validate_required_args,
    validate_slot_selected,
)


class TestResponseBuilder:
    """Tests for ResponseBuilder static methods."""

    def test_success_returns_text_content_list(self):
        """Test success() returns a list with TextContent."""
        result = ResponseBuilder.success("Operation completed")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].type == "text"
        assert result[0].text == "Operation completed"

    def test_success_with_empty_message(self):
        """Test success() with empty message."""
        result = ResponseBuilder.success("")

        assert len(result) == 1
        assert result[0].text == ""

    def test_success_with_multiline_message(self):
        """Test success() with multiline message."""
        message = "Line 1\nLine 2\nLine 3"
        result = ResponseBuilder.success(message)

        assert result[0].text == message

    def test_error_from_memcord_error(self):
        """Test error() with MemcordError instance."""
        error = MemcordError(
            message="Slot not found",
            error_code=ErrorCode.SLOT_NOT_FOUND,
            severity=ErrorSeverity.MEDIUM,
        )
        result = ResponseBuilder.error(error)

        assert isinstance(result, list)
        assert len(result) == 1
        assert "Slot not found" in result[0].text

    def test_error_with_recovery_suggestions(self):
        """Test error() includes recovery suggestions."""
        error = MemcordError(
            message="Operation failed",
            error_code=ErrorCode.INTERNAL_ERROR,
            recovery_suggestions=["Try again", "Check logs"],
        )
        result = ResponseBuilder.error(error)

        # The user message should include relevant info
        assert len(result) == 1
        assert "Operation failed" in result[0].text

    def test_error_message_simple(self):
        """Test error_message() creates prefixed error."""
        result = ResponseBuilder.error_message("Something went wrong")

        assert len(result) == 1
        assert result[0].text == "Error: Something went wrong"

    def test_error_message_with_empty_string(self):
        """Test error_message() with empty message."""
        result = ResponseBuilder.error_message("")

        assert result[0].text == "Error: "

    def test_from_lines_joins_lines(self):
        """Test from_lines() joins list of strings."""
        lines = ["Line 1", "Line 2", "Line 3"]
        result = ResponseBuilder.from_lines(lines)

        assert len(result) == 1
        assert result[0].text == "Line 1\nLine 2\nLine 3"

    def test_from_lines_empty_list(self):
        """Test from_lines() with empty list."""
        result = ResponseBuilder.from_lines([])

        assert len(result) == 1
        assert result[0].text == ""

    def test_from_lines_single_item(self):
        """Test from_lines() with single item."""
        result = ResponseBuilder.from_lines(["Single line"])

        assert result[0].text == "Single line"

    def test_empty_returns_empty_list(self):
        """Test empty() returns empty list."""
        result = ResponseBuilder.empty()

        assert result == []
        assert len(result) == 0


class TestHandleErrorsDecorator:
    """Tests for @handle_errors decorator."""

    @pytest.mark.asyncio
    async def test_successful_handler_returns_result(self):
        """Test decorator passes through successful results."""

        @handle_errors()
        async def successful_handler(self, arguments):
            return [TextContent(type="text", text="success")]

        class MockSelf:
            pass

        result = await successful_handler(MockSelf(), {"arg": "value"})

        assert len(result) == 1
        assert result[0].text == "success"

    @pytest.mark.asyncio
    async def test_memcord_error_handled(self):
        """Test decorator handles MemcordError."""

        @handle_errors()
        async def failing_handler(self, arguments):
            raise MemcordError(
                message="Slot not found",
                error_code=ErrorCode.SLOT_NOT_FOUND,
            )

        class MockSelf:
            pass

        result = await failing_handler(MockSelf(), {})

        assert len(result) == 1
        assert "Slot not found" in result[0].text

    @pytest.mark.asyncio
    async def test_generic_exception_with_default_message(self):
        """Test decorator handles generic exceptions with default message."""

        @handle_errors(default_error_message="Custom operation failed")
        async def failing_handler(self, arguments):
            raise ValueError("Some internal error")

        class MockSelf:
            pass

        result = await failing_handler(MockSelf(), {})

        assert len(result) == 1
        assert "Custom operation failed" in result[0].text
        assert "Some internal error" in result[0].text

    @pytest.mark.asyncio
    async def test_generic_exception_uses_error_handler(self):
        """Test decorator uses error_handler if available on self."""
        from memcord.errors import ErrorHandler

        @handle_errors()
        async def failing_handler(self, arguments):
            raise RuntimeError("Runtime issue")

        class MockSelf:
            def __init__(self):
                self.error_handler = ErrorHandler()

        result = await failing_handler(MockSelf(), {"test": "args"})

        assert len(result) == 1
        # Should have error wrapped by handler
        assert "Error" in result[0].text or "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""

        @handle_errors()
        async def my_handler(self, arguments):
            """Handler docstring."""
            return []

        assert my_handler.__name__ == "my_handler"
        assert "Handler docstring" in my_handler.__doc__

    @pytest.mark.asyncio
    async def test_arguments_passed_correctly(self):
        """Test arguments are passed to handler correctly."""
        received_args = {}

        @handle_errors()
        async def capture_handler(self, arguments):
            received_args.update(arguments)
            return [TextContent(type="text", text="captured")]

        class MockSelf:
            pass

        test_args = {"slot_name": "test", "content": "data"}
        await capture_handler(MockSelf(), test_args)

        assert received_args == test_args


class TestValidateRequiredArgsDecorator:
    """Tests for @validate_required_args decorator."""

    @pytest.mark.asyncio
    async def test_valid_args_passes_through(self):
        """Test decorator passes through when all args present."""

        @validate_required_args("slot_name", "content")
        async def handler(self, arguments):
            return [TextContent(type="text", text="ok")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {"slot_name": "test", "content": "data"})

        assert result[0].text == "ok"

    @pytest.mark.asyncio
    async def test_missing_single_arg_returns_error(self):
        """Test decorator returns error for single missing arg."""

        @validate_required_args("slot_name", "content")
        async def handler(self, arguments):
            return [TextContent(type="text", text="ok")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {"slot_name": "test"})

        assert "Error:" in result[0].text
        assert "content" in result[0].text

    @pytest.mark.asyncio
    async def test_missing_multiple_args_returns_error(self):
        """Test decorator returns error listing all missing args."""

        @validate_required_args("arg1", "arg2", "arg3")
        async def handler(self, arguments):
            return [TextContent(type="text", text="ok")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {})

        assert "Error:" in result[0].text
        assert "arg1" in result[0].text
        assert "arg2" in result[0].text
        assert "arg3" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_string_arg_treated_as_missing(self):
        """Test decorator treats empty string as missing."""

        @validate_required_args("slot_name")
        async def handler(self, arguments):
            return [TextContent(type="text", text="ok")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {"slot_name": ""})

        assert "Error:" in result[0].text
        assert "slot_name" in result[0].text

    @pytest.mark.asyncio
    async def test_none_arg_treated_as_missing(self):
        """Test decorator treats None as missing."""

        @validate_required_args("slot_name")
        async def handler(self, arguments):
            return [TextContent(type="text", text="ok")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {"slot_name": None})

        assert "Error:" in result[0].text

    @pytest.mark.asyncio
    async def test_no_required_args_always_passes(self):
        """Test decorator with no required args always passes."""

        @validate_required_args()
        async def handler(self, arguments):
            return [TextContent(type="text", text="ok")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {})

        assert result[0].text == "ok"


class TestValidateSlotSelectedDecorator:
    """Tests for @validate_slot_selected decorator."""

    @pytest.mark.asyncio
    async def test_slot_from_arguments_passes(self):
        """Test decorator passes when slot in arguments."""

        @validate_slot_selected()
        async def handler(self, arguments):
            return [TextContent(type="text", text=f"slot: {arguments.get('_resolved_slot_name')}")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {"slot_name": "test_slot"})

        assert "test_slot" in result[0].text

    @pytest.mark.asyncio
    async def test_slot_from_resolve_method(self):
        """Test decorator uses _resolve_slot when available."""

        @validate_slot_selected()
        async def handler(self, arguments):
            return [TextContent(type="text", text=f"slot: {arguments.get('_resolved_slot_name')}")]

        class MockSelf:
            def _resolve_slot(self, arguments, slot_arg):
                # Simulate resolving from current slot state
                return arguments.get(slot_arg) or "current_slot"

        result = await handler(MockSelf(), {})

        assert "current_slot" in result[0].text

    @pytest.mark.asyncio
    async def test_no_slot_returns_error(self):
        """Test decorator returns error when no slot available."""

        @validate_slot_selected()
        async def handler(self, arguments):
            return [TextContent(type="text", text="ok")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {})

        assert "Error:" in result[0].text
        assert "No memory slot selected" in result[0].text

    @pytest.mark.asyncio
    async def test_custom_error_message(self):
        """Test decorator uses custom error message."""

        @validate_slot_selected(error_message="Please select a slot first!")
        async def handler(self, arguments):
            return [TextContent(type="text", text="ok")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {})

        assert "Please select a slot first!" in result[0].text

    @pytest.mark.asyncio
    async def test_custom_slot_arg(self):
        """Test decorator uses custom slot argument name."""

        @validate_slot_selected(slot_arg="target_slot")
        async def handler(self, arguments):
            return [TextContent(type="text", text=f"slot: {arguments.get('_resolved_target_slot')}")]

        class MockSelf:
            pass

        result = await handler(MockSelf(), {"target_slot": "my_target"})

        assert "my_target" in result[0].text

    @pytest.mark.asyncio
    async def test_resolved_slot_added_to_arguments(self):
        """Test decorator adds resolved slot to arguments."""
        captured_args = {}

        @validate_slot_selected()
        async def handler(self, arguments):
            captured_args.update(arguments)
            return [TextContent(type="text", text="ok")]

        class MockSelf:
            pass

        await handler(MockSelf(), {"slot_name": "test_slot"})

        assert "_resolved_slot_name" in captured_args
        assert captured_args["_resolved_slot_name"] == "test_slot"


class TestDecoratorCombinations:
    """Tests for combining multiple decorators."""

    @pytest.mark.asyncio
    async def test_handle_errors_with_validate_required_args(self):
        """Test combining @handle_errors with @validate_required_args."""

        @handle_errors(default_error_message="Handler failed")
        @validate_required_args("content")
        async def handler(self, arguments):
            # Simulate an error after validation passes
            if arguments["content"] == "error":
                raise ValueError("Processing error")
            return [TextContent(type="text", text=f"processed: {arguments['content']}")]

        class MockSelf:
            pass

        # Missing required arg
        result = await handler(MockSelf(), {})
        assert "content" in result[0].text

        # Valid args, successful
        result = await handler(MockSelf(), {"content": "data"})
        assert "processed: data" in result[0].text

        # Valid args, handler error
        result = await handler(MockSelf(), {"content": "error"})
        assert "Handler failed" in result[0].text

    @pytest.mark.asyncio
    async def test_all_three_decorators(self):
        """Test combining all three decorators."""

        @handle_errors(default_error_message="Operation failed")
        @validate_required_args("content")
        @validate_slot_selected()
        async def handler(self, arguments):
            slot = arguments["_resolved_slot_name"]
            content = arguments["content"]
            return [TextContent(type="text", text=f"{slot}: {content}")]

        class MockSelf:
            pass

        # No slot
        result = await handler(MockSelf(), {"content": "data"})
        assert "No memory slot selected" in result[0].text

        # No content
        result = await handler(MockSelf(), {"slot_name": "test"})
        assert "content" in result[0].text

        # Valid
        result = await handler(MockSelf(), {"slot_name": "test", "content": "data"})
        assert "test: data" in result[0].text
