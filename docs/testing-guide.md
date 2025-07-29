# Memcord Testing Guide

This guide covers how to run tests for the memcord MCP server, from basic unit tests to full Claude Desktop integration testing.

## Quick Start

```bash
# Install test dependencies
uv sync --dev

# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/memcord --cov-report=html
```

## Test Categories

### Unit Tests (`pytest -m unit`)
Fast, isolated tests for individual components:
- **Storage Manager** - Memory slot CRUD operations, search, tags
- **Text Summarizer** - Content compression and summarization  
- **Pydantic Models** - Data validation and serialization
- **Core Components** - Individual module functionality

### Integration Tests (`pytest -m integration`)
Multi-component interaction tests:
- **Tool Integration** - Complete workflows using multiple tools
- **Error Scenarios** - Error handling and recovery testing
- **Resource Integration** - MCP resource handling across tools
- **Concurrent Operations** - Multi-threaded operation testing

### MCP Protocol Tests (`pytest -m mcp`)
MCP protocol compliance and tool testing:
- **Protocol Compliance** - MCP specification adherence
- **Tool Functionality** - All 19 memcord tools (11 basic + 8 advanced)
- **Resource Handling** - MCP resource creation and access
- **Error Handling** - Graceful error responses

### UI Tests (`pytest -m ui`)
Claude Desktop integration and UI automation:
- **Claude Desktop Integration** - Real integration testing
- **Server Lifecycle** - Process management and startup/shutdown
- **Performance Testing** - Load testing and benchmarking
- **Workflow Validation** - End-to-end usage scenarios

### Selenium Tests (`pytest -m selenium`)
Browser automation and UI testing:
- **WebDriver Setup** - Automated browser control
- **Mock Interfaces** - Simulated Claude Desktop UI
- **Tool Interaction** - Automated tool execution testing

## Running Tests

### Basic Test Execution

```bash
# All tests
pytest

# Specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest -m mcp                     # MCP protocol tests only
pytest -m ui                      # UI integration tests only
pytest -m selenium                # Selenium automation tests

# Exclude slow tests
pytest -m "not slow"

# Only fast tests for development
pytest -m "unit or integration" --tb=short
```

### Advanced Test Options

```bash
# Parallel execution (faster)
pytest -n auto

# Verbose output with test names
pytest -v

# Stop on first failure
pytest -x

# Run specific test file
pytest tests/unit/test_storage.py

# Run specific test class
pytest tests/mcp/test_memcord_tools.py::TestBasicMemcordTools

# Run specific test method
pytest tests/integration/test_tool_integration.py::TestToolIntegration::test_complete_memory_lifecycle
```

### Coverage and Reporting

```bash
# Generate HTML coverage report
pytest --cov=src/memcord --cov-report=html

# Coverage with minimum threshold
pytest --cov=src/memcord --cov-fail-under=80

# Coverage for specific modules
pytest --cov=src/memcord/storage --cov=src/memcord/server

# Generate XML coverage for CI
pytest --cov=src/memcord --cov-report=xml
```

## Test Environment Setup

### Basic Requirements

```bash
# Install all dependencies including test tools
uv sync --dev

# Required packages are installed automatically:
# - pytest (test framework)
# - pytest-asyncio (async test support)
# - pytest-mock (mocking utilities)
# - pytest-cov (coverage reporting)
# - factory-boy (test data generation)
```

### Selenium Setup (Optional)

For UI automation tests:

```bash
# Selenium is included in dev dependencies
# Chrome/Firefox drivers are managed automatically

# Run selenium tests
pytest -m selenium

# Skip selenium tests if not needed
pytest -m "not selenium"
```

### Claude Desktop Integration

For testing actual Claude Desktop integration:

1. **Install Claude Desktop** (from Anthropic)
2. **Configure memcord** in Claude Desktop settings:

```json
{
  "mcpServers": {
    "memcord": {
      "command": "uv",
      "args": ["--directory", "/path/to/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/path/to/memcord/src",
        "MEMCORD_ENABLE_ADVANCED": "true"
      }
    }
  }
}
```

3. **Run integration tests**:
```bash
pytest -m requires_claude_desktop
```

## Test Organization

### Directory Structure

```
tests/
├── conftest.py                   # Shared fixtures and configuration
├── fixtures/
│   └── memory_factories.py      # Test data factories
├── utils/
│   └── test_helpers.py         # Testing utilities
├── unit/                        # Unit tests
│   ├── test_storage.py         # Storage manager tests
│   ├── test_summarizer.py      # Text summarization tests
│   └── test_models.py          # Pydantic model tests
├── integration/                 # Integration tests
│   ├── test_tool_integration.py    # Multi-tool workflows
│   └── test_error_scenarios.py     # Error handling tests
├── mcp/                         # MCP protocol tests
│   ├── test_mcp_protocol.py    # Protocol compliance
│   ├── test_mcp_base.py        # Base test classes
│   └── test_memcord_tools.py   # All 16 tools testing
└── ui/                          # UI automation tests
    ├── test_claude_desktop_integration.py  # Claude Desktop integration
    ├── test_mcp_server_lifecycle.py        # Server lifecycle
    └── test_selenium_automation.py         # Browser automation
```

### Test Markers

```python
# Test markers for organization
@pytest.mark.unit              # Fast unit tests
@pytest.mark.integration       # Multi-component tests
@pytest.mark.mcp               # MCP protocol tests
@pytest.mark.ui                # UI integration tests
@pytest.mark.selenium          # Browser automation
@pytest.mark.slow              # Long-running tests
@pytest.mark.requires_claude_desktop     # Needs Claude Desktop
@pytest.mark.requires_external          # External dependencies
```

## Common Test Scenarios

### Testing All Memcord Tools

```bash
# Test all 17 memcord tools
pytest tests/mcp/test_memcord_tools.py

# Test only basic tools (9 tools)
pytest tests/mcp/test_memcord_tools.py::TestBasicMemcordTools

# Test only advanced tools (9 tools)
pytest tests/mcp/test_memcord_tools.py::TestAdvancedMemcordTools

# Test specific tool
pytest tests/mcp/test_memcord_tools.py -k "test_memcord_name"
```

### Testing Complete Workflows

```bash
# Complete memory management lifecycle
pytest tests/integration/test_tool_integration.py::TestToolIntegration::test_complete_memory_lifecycle

# Research and summarization workflow
pytest tests/ui/test_claude_desktop_integration.py::TestClaudeDesktopWorkflows::test_research_and_summarization_workflow

# Collaborative memory sharing
pytest tests/ui/test_claude_desktop_integration.py::TestClaudeDesktopWorkflows::test_collaborative_memory_workflow
```

### Performance and Stress Testing

```bash
# All performance tests
pytest -m slow

# Large data handling
pytest tests/ui/test_mcp_server_lifecycle.py::TestMCPServerStressTests::test_large_data_handling

# High frequency operations
pytest tests/ui/test_mcp_server_lifecycle.py::TestMCPServerStressTests::test_high_frequency_operations

# Memory usage monitoring
pytest tests/ui/test_claude_desktop_integration.py::TestClaudeDesktopPerformance::test_large_memory_slot_performance
```

### Error Handling and Recovery

```bash
# All error scenarios
pytest tests/integration/test_error_scenarios.py

# Cascading error recovery
pytest tests/integration/test_error_scenarios.py::TestErrorHandlingIntegration::test_cascading_error_recovery

# File system error handling
pytest tests/integration/test_error_scenarios.py::TestErrorHandlingIntegration::test_file_system_error_handling
```

## Configuration and Environment Variables

### Test Configuration

The test suite supports several environment variables:

```bash
# Enable/disable advanced tools for testing
export MEMCORD_ENABLE_ADVANCED=true

# Custom memory directory for tests
export MEMCORD_MEMORY_DIR=/tmp/test_memory

# Custom shared directory for tests
export MEMCORD_SHARED_DIR=/tmp/test_shared

# Disable UI tests
export MEMCORD_SKIP_UI_TESTS=true
```

### Pytest Configuration

The `pytest.ini` file configures test behavior:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Fast unit tests for individual components
    integration: Multi-component interaction tests
    mcp: MCP protocol compliance and tool tests
    ui: Claude Desktop integration tests
    selenium: Browser automation tests
    slow: Long-running performance tests
    requires_claude_desktop: Tests requiring Claude Desktop
    requires_external: Tests requiring external dependencies
addopts = 
    --strict-markers
    --tb=short
    --asyncio-mode=auto
```

## Continuous Integration

### CI-Friendly Test Run

```bash
# Fast CI run (excludes UI and slow tests)
pytest -m "not ui and not selenium and not slow and not requires_claude_desktop" --tb=short

# Full CI validation
pytest --cov=src/memcord --cov-fail-under=80 --tb=short

# Parallel CI execution
pytest -n auto -m "not ui" --tb=short
```

### Test Coverage Requirements

- **Minimum Coverage**: 80%
- **Unit Tests**: >90% coverage expected
- **Integration Tests**: Focus on workflow coverage
- **MCP Tests**: 100% tool coverage (all 16 tools)

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure PYTHONPATH includes src directory
   export PYTHONPATH=/path/to/memcord/src:$PYTHONPATH
   pytest
   ```

2. **Async Test Issues**
   ```bash
   # Install pytest-asyncio
   pip install pytest-asyncio
   
   # Or use uv
   uv add pytest-asyncio --dev
   ```

3. **Selenium WebDriver Issues**
   ```bash
   # Skip selenium tests if drivers unavailable
   pytest -m "not selenium"
   
   # Or install drivers manually
   pip install webdriver-manager
   ```

4. **Permission Errors**
   ```bash
   # Use temporary directory for tests
   export MEMCORD_MEMORY_DIR=/tmp/memcord_test
   pytest
   ```

### Debug Mode

```bash
# Run with maximum verbosity
pytest -vvv --tb=long

# Drop into debugger on failure
pytest --pdb

# Print all output (disable capture)
pytest -s

# Run single test with debugging
pytest -vvv -s tests/unit/test_storage.py::TestStorageManager::test_create_memory_slot
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py`, `Test*` classes, `test_*` methods
2. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
3. **Add docstrings**: Describe what the test validates
4. **Use fixtures**: Leverage existing fixtures in `conftest.py`
5. **Test edge cases**: Include error conditions and boundary cases
6. **Keep tests isolated**: Each test should be independent
7. **Mock external dependencies**: Use `pytest-mock` for external services

### Example Test

```python
import pytest
from tests.mcp.test_mcp_base import MCPTestBase

@pytest.mark.unit
class TestNewFeature(MCPTestBase):
    """Test new feature functionality."""
    
    async def test_new_feature_basic_functionality(self, temp_dir):
        """Test that new feature works with valid input."""
        server = await self.create_test_server(temp_dir)
        
        # Test implementation
        result = await self.call_tool("new_tool", {"param": "value"})
        self.assert_tool_call_successful(result)
        
        text = self.extract_text_content(result)
        assert "expected_result" in text
    
    async def test_new_feature_error_handling(self, temp_dir):
        """Test that new feature handles errors gracefully."""
        server = await self.create_test_server(temp_dir)
        
        # Test error condition
        result = await self.call_tool("new_tool", {"param": ""})
        self.assert_tool_call_failed(result, "cannot be empty")
```

This comprehensive testing framework ensures memcord works reliably across all usage scenarios, from individual components to full Claude Desktop integration.