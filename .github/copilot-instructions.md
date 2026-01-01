# Git MCP - AI Coding Instructions

## Project Overview

**gitMCP** is a Model Context Protocol (MCP) server exposing Git analytics for development managers. It provides 7 analytical tools for team insights: project dashboard, commit history, developer stats, branch tracking, file change monitoring, developer comparison, and repository sync.

**Key Purpose**: Enable managers to understand team productivity, code health, and project trends through natural language conversations with Claude—no Git commands required.

## Architecture & Components

### Core Pattern: Three-Layer Tool Architecture

Each tool in `tools/` follows this pattern:
1. **Async Git Fetcher** (`get_*_raw()`) - Executes Git command with filters via [git_runner.py](git_runner.py)
2. **Parser** (`parse_*()`) - Transforms raw output into structured dicts
3. **MCP Tool** (`@mcp.tool()` in `register()`) - Exposes parsed data as API endpoint

Example flow: [git_commit_history.py](tools/git_commit_history.py)
- `get_commit_history_raw()` runs `git log --numstat --pretty=format:COMMIT|%H|%an|%ae|%ai|%s`
- `parse_commit_history()` parses each `COMMIT|` line into dict with author, date, files changed, stats
- `@mcp.tool()` decorated function exposes as "get_commit_history" tool with filters (since, until, author, max_count)

### Tool Modules

| Module | Purpose | Key Functions |
|--------|---------|---|
| [git_branches.py](tools/git_branches.py) | List all branches with activity | `get_branches_raw()`, `parse_branches()` |
| [git_commit_history.py](tools/git_commit_history.py) | Detailed commit analysis | `get_commit_history_raw()`, `parse_commit_history()` |
| [git_developer_stats.py](tools/git_developer_stats.py) | Per-developer metrics | `analyze_developer_stats()` - aggregates from commits |
| [git_compare_developers.py](tools/git_compare_developers.py) | Side-by-side developer comparison | Compares multiple authors across time |
| [git_file_changes.py](tools/git_file_changes.py) | Track changes to specific files | `get_file_history_raw()` with `--follow` |
| [git_dashboard.py](tools/git_dashboard.py) | Comprehensive project snapshot | Orchestrator: aggregates status, metrics, risk analysis |
| [git_sync.py](tools/git_sync.py) | Repository sync operations | Handles fetch/pull operations |

### Foundation Layer

**[git_runner.py](git_runner.py)** - Unified Git executor
- `run_git(repo_path, args, timeout_s=60)` - Single async function for all Git calls
- Environment setup: `GIT_PAGER=""`, `GIT_TERMINAL_PROMPT="0"` (prevents interactive hanging)
- Subprocess stderr → custom exceptions (see [exceptions.py](exceptions.py))
- Default timeout 60s; uses `asyncio.wait_for()` for control

**[exceptions.py](exceptions.py)** - Error hierarchy
- `GitNotFoundError` - Git executable missing from PATH
- `GitRepositoryError` - Invalid repo path
- `GitCommandError` - Non-zero git exit
- `GitTimeoutError` - Command exceeded timeout

All tools catch these and wrap in response dicts (no exceptions bubble to MCP layer).

## Critical Patterns & Conventions

### 1. Parsing Strategy
- **Commit lines use pipe delimiter** (`|`): `COMMIT|hash|author|email|date|message`
- **File changes use tab delimiter**: `additions\tdeletions\tpath`
- Defensive parsing: Check part counts before unpacking to avoid IndexError
- Filenames with spaces/special chars handled by tab-based splitting

Example from [git_commit_history.py](tools/git_commit_history.py):
```python
if line_stripped.startswith("COMMIT|"):
    parts = line_stripped.split("|", 5)  # Max 5 splits to preserve message content
    if len(parts) != 6:
        continue  # Skip malformed lines
```

### 2. Time Filtering Pattern
All analytical tools support `since` / `until` parameters (ISO8601 dates):
- `get_commit_history_raw()`, `get_file_history_raw()`, etc. append to git args
- Allows queries like "commits in last week" without hardcoding date math
- Dashboard risk analysis uses thresholds: see [git_dashboard.py](tools/git_dashboard.py) lines ~17-19

### 3. Response Schema
All MCP tools return:
```python
{
    "commits": [...],        # tool-specific main data
    "repo_path": str,
    "since": Optional[str],  # if applicable
    "until": Optional[str],
    "error": None or str     # wraps exceptions gracefully
}
```

No exceptions thrown from `@mcp.tool()` handlers; errors wrapped in response.

### 4. Repository Validation
- `ensure_is_git_repo(repo_path)` called first in each tool
- Verifies path exists and is directory, then runs `git rev-parse --git-dir`
- Raises `GitRepositoryError` if invalid; caught and wrapped in response

### 5. Async All The Way
- All Git calls async via `asyncio.create_subprocess_exec()` (non-blocking I/O)
- Tools are async coroutines; MCP framework handles awaiting
- Dashboard aggregates multiple tool results with `asyncio.gather()` for parallelism

## Development Workflow

### Running the Server
```bash
python server.py
```
- Starts on stdio (Claude Desktop connects here)
- Registers all tools from `tools/` modules

### Running Tests
```bash
pytest tests/
# Set TEST_REPO_PATH env var to test against different repo
TEST_REPO_PATH=/path/to/repo pytest tests/
```
- Fixtures in [tests/conftest.py](tests/conftest.py)
- Tests are async (`pytest-asyncio`)

### Adding a New Tool
1. Create `tools/git_new_feature.py`
2. Implement:
   ```python
   async def get_data_raw(repo_path: str, ...) -> str:
       """Execute git command."""
       args = [...]
       return await run_git(repo_path, args)
   
   def parse_data(raw: str) -> List[Dict]:
       """Parse output."""
       ...
   
   def register(mcp: FastMCP):
       @mcp.tool()
       async def my_tool(repo_path: str) -> Dict:
           await ensure_is_git_repo(repo_path)
           raw = await get_data_raw(repo_path)
           return {"data": parse_data(raw), "repo_path": repo_path}
   ```
3. Import and call in [server.py](server.py):
   ```python
   from tools.git_new_feature import register as register_new
   register_new(mcp)
   ```

## Project-Specific Patterns

1. **Test Repository**: Default test repo hardcoded in [conftest.py](tests/conftest.py) (ONNX runtime); override with `TEST_REPO_PATH` env var
2. **Risk Thresholds**: [git_dashboard.py](tools/git_dashboard.py) defines constants for "high/medium" risk (e.g., >15 commits = high risk); tweak for your team's norms
3. **Manager-First Design**: All tools return summary stats + top-N items (not full lists) to stay readable in conversation
4. **File Exclusions**: No built-in filtering; if needed, filter in parser or git args (e.g., `--` glob patterns)

## Key Files Reference

- [server.py](server.py) - Entry point; registers all tools
- [git_runner.py](git_runner.py) - Core async Git executor; **modify for custom git config**
- [git_dashboard.py](tools/git_dashboard.py) - Largest/most complex; reference for aggregation patterns
- [pyproject.toml](pyproject.toml) - Dependencies: mcp, httpx, pytest-asyncio
- [README.md](README.md) - User-facing feature docs
