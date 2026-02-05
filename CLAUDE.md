# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Git MCP Server is a Model Context Protocol (MCP) server providing Git analytics tools for development managers. It exposes 7 analytical tools through natural language conversations: project dashboard, commit history, developer stats, developer comparison, file changes, branch tracking, and repository sync.

## Commands

```bash
# Run the MCP server
python server.py

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_commit_history.py

# Run tests with coverage
pytest --cov=. --cov-report=html

# Run tests against a different repository
set TEST_REPO_PATH=C:\path\to\repo   # Windows
export TEST_REPO_PATH=/path/to/repo  # Linux/Mac
pytest tests/
```

## Architecture

### Three-Layer Tool Pattern

Each tool in `tools/` follows this pattern:
1. **Async Git Fetcher** (`get_*_raw()`) - Executes Git command via `git_runner.py`
2. **Parser** (`parse_*()`) - Transforms raw output into structured dicts
3. **MCP Tool** (`@mcp.tool()` in `register()`) - Exposes parsed data as API endpoint

### Core Components

- **server.py** - Entry point; imports and registers all tools from `tools/` modules
- **git_runner.py** - Unified async Git executor using `asyncio.create_subprocess_exec()`
  - Sets `GIT_PAGER=""` and `GIT_TERMINAL_PROMPT="0"` to prevent interactive hanging
  - Default 60s timeout via `asyncio.wait_for()`
- **exceptions.py** - Error hierarchy: `GitNotFoundError`, `GitRepositoryError`, `GitCommandError`, `GitTimeoutError`
- **prompts.py** - Pre-configured MCP prompts for common manager tasks

### Tool Modules (tools/)

| Module | Purpose |
|--------|---------|
| git_dashboard.py | Comprehensive project snapshot; orchestrates other tools |
| git_commit_history.py | Detailed commit analysis with file changes |
| git_developer_stats.py | Per-developer metrics aggregated from commits |
| git_compare_developers.py | Side-by-side developer comparison |
| git_file_changes.py | Track changes to specific files with `--follow` |
| git_branches.py | List all branches sorted by activity |
| git_sync.py | Repository fetch/pull operations |

## Key Patterns

### Parsing Convention
- Commit lines use pipe delimiter: `COMMIT|hash|author|email|date|message`
- File changes use tab delimiter: `additions\tdeletions\tpath`
- Always check part counts before unpacking to avoid `IndexError`

### Response Schema
All MCP tools return dicts with:
- Tool-specific data (e.g., `commits`, `branches`)
- `repo_path`
- Optional `since`/`until` filters
- `error` field (wraps exceptions; no exceptions bubble to MCP layer)

### Repository Validation
`ensure_is_git_repo(repo_path)` runs first in each tool - verifies path exists and runs `git rev-parse --git-dir`

### Adding a New Tool

1. Create `tools/git_new_feature.py`:
```python
async def get_data_raw(repo_path: str, ...) -> str:
    args = [...]
    return await run_git(repo_path, args)

def parse_data(raw: str) -> List[Dict]:
    ...

def register(mcp: FastMCP):
    @mcp.tool()
    async def my_tool(repo_path: str) -> Dict:
        await ensure_is_git_repo(repo_path)
        raw = await get_data_raw(repo_path)
        return {"data": parse_data(raw), "repo_path": repo_path}
```

2. Import and register in `server.py`:
```python
from tools.git_new_feature import register as register_new
register_new(mcp)
```

## Testing

Tests use `pytest-asyncio`. The default test repository is configured in `tests/conftest.py` and can be overridden with the `TEST_REPO_PATH` environment variable.
