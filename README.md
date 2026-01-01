# Git MCP Server - Development Manager Analytics Tools

A Model Context Protocol (MCP) server providing Git repository analysis tools designed specifically for development managers. Get instant insights into team performance, code health, and project trends through natural language conversations with Claude.

## Overview

This MCP server enables development managers to analyze Git repositories without writing any code. Simply ask Claude questions about your project, and get detailed analytics about commits, developers, code changes, and team performance.

**Perfect for managers who want to:**
- Track team productivity and individual contributions
- Identify bottlenecks and inactive developers
- Monitor project health and code quality trends
- Generate weekly/monthly progress reports
-  Make data-driven decisions with insights into team performance and workload distribution

## Features

### 7 Powerful Analytics Tools

1. **Project Dashboard** - Comprehensive overview of repository activity
2. **Commit History** - Detailed commit analysis with file changes and statistics
3. **Developer Statistics** - Individual developer performance metrics
4. **Developer Comparison** - Side-by-side comparison of team members
5. **File Change Tracking** - Monitor changes to critical files over time
6. **Branch Management** - Track all branches and their activity
7. **Repository Sync** - Keep your local repository up to date

### Key Capabilities

- **Time-based filtering** - Analyze any time period (last week, last month, custom ranges)
- **Developer-specific insights** - Track individual contributions and patterns
- **Code quality indicators** - Test coverage, commit sizes, collaboration patterns
- **Trend analysis** - Compare activity across different time periods
- **Natural language interface** - No Git commands needed, just ask Claude

## Installation

### Prerequisites

- Python 3.8 or higher
- Git installed and accessible in PATH
- Claude Desktop or compatible MCP client

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd gitMCP
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Claude Desktop**

   Add to your Claude Desktop configuration file:

   **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "git-mcp": {
         "command": "python",
         "args": ["C:\\path\\to\\gitMCP\\server.py"]
       }
     }
   }
   ```

4. **Restart Claude Desktop**

   The MCP server will automatically start when you launch Claude Desktop.

## Usage

### Quick Start

Once configured, simply start a conversation with Claude and provide your repository path:

```
Hello! I'm a development manager for the ONNX Runtime project
(C:\Projects\onnxruntime). I'd like to understand the team's activity
over the last 30 days.
```

Claude will use the MCP tools to analyze your repository and provide detailed insights.

### Example Questions

**Weekly Progress Reports:**
```
Give me a weekly progress report comparing last week vs. this week.
How many commits, developers, and lines of code changed?
```

**Team Performance:**
```
Who are the top 10 most active developers this month?
Show me their commit counts and code contributions.
```

**Individual Analysis:**
```
Give me a detailed report on developer@example.com:
- How many commits in the last 30 days?
- What files did they work on?
- What was her contribution, and how did it impact the project?
```

**Trend Analysis:**
```
Compare activity across the last 3 months. Is the team becoming
more or less productive? Show me the numbers.
```

**Branch Management:**
```
The developer adrianlizarraga – which branches has he worked on recently?
Show me his commits and the names of the branches he worked on.
```

**Developer Comparison:**
```
Compare these 3 developers and their work styles. Who focuses on
what areas? How do their contributions differ?
```

## Live Demo

See a real example of this tool in action: [Live Conversation Demo](https://claude.ai/share/23354fa9-8473-4cdf-a883-dede8b790d62)

This demo shows a complete conversation where a development manager analyzes the ONNX Runtime project, tracking team performance, identifying key contributors, and generating actionable insights.

## Available Tools

### 1. `get_project_dashboard`
**Purpose:** Comprehensive project overview
**Parameters:**
- `repo_path` (required): Absolute path to repository
- `since`: Start date (default: "30 days ago")
- `until`: End date (optional)

**Returns:** Complete dashboard with commit stats, top contributors, active areas, and summary metrics

---

### 2. `get_commit_history`
**Purpose:** Detailed commit history with file changes
**Parameters:**
- `repo_path` (required): Absolute path to repository
- `branch`: Specific branch (default: all branches)
- `max_count`: Maximum commits to return
- `since`: Commits since date
- `until`: Commits until date
- `author`: Filter by author name/email

**Returns:** List of commits with file changes, additions/deletions, and summary statistics

---

### 3. `get_developer_stats`
**Purpose:** Individual developer performance metrics
**Parameters:**
- `repo_path` (required): Absolute path to repository
- `author` (required): Developer name or email
- `since`: Start date
- `until`: End date

**Returns:** Developer's commit count, code contributions, files modified, and activity patterns

---

### 4. `compare_developer_stats`
**Purpose:** Side-by-side developer comparison
**Parameters:**
- `repo_path` (required): Absolute path to repository
- `authors` (required): List of developer names/emails
- `since`: Start date
- `until`: End date

**Returns:** Comparative analysis of multiple developers' contributions and work patterns

---

### 5. `get_file_changes`
**Purpose:** Track changes to specific files
**Parameters:**
- `repo_path` (required): Absolute path to repository
- `file_path` (required): Path to file relative to repo root
- `since`: Start date
- `until`: End date
- `max_count`: Maximum commits to show

**Returns:** Complete history of changes to a specific file, including who changed it and when

---

### 6. `get_branch_list`
**Purpose:** List all branches with activity
**Parameters:**
- `repo_path` (required): Absolute path to repository

**Returns:** All local and remote branches sorted by most recent activity

---

### 7. `git_sync`
**Purpose:** Sync repository with remote
**Parameters:**
- `repo_path` (required): Absolute path to repository

**Returns:** Status of fetch operation

## Technical Details

### Architecture

```
gitMCP/
├── server.py              # MCP server entry point
├── git_runner.py          # Git command execution
├── exceptions.py          # Custom error handling
├── requirements.txt       # Dependencies
├── tools/                 # MCP tool implementations
│   ├── git_dashboard.py
│   ├── git_commit_history.py
│   ├── git_developer_stats.py
│   ├── git_compare_developers.py
│   ├── git_file_changes.py
│   ├── git_branches.py
│   └── git_sync.py
└── tests/                 # Test suite
    ├── conftest.py
    └── test_*.py
```

### Error Handling

The server includes custom exception handling for common Git operations:

- **GitNotFoundError** - Git executable not found in PATH
- **GitRepositoryError** - Invalid or non-existent repository
- **GitCommandError** - Git command execution failure
- **GitTimeoutError** - Command timeout (default: 60 seconds)

### Type Safety

All functions include comprehensive type hints for better IDE support and code quality:
- Input validation
- Return type annotations
- Optional parameter handling

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_commit_history.py
```

### Configure Test Repository

Set your test repository via environment variable:

```bash
# Windows
set TEST_REPO_PATH=C:\path\to\your\test\repo

# Linux/Mac
export TEST_REPO_PATH=/path/to/your/test/repo
```

Or modify `tests/conftest.py` to set a default path.

## Use Cases

### For Development Managers

- **Weekly Standups** - Generate team activity summaries
- **Performance Reviews** - Track individual contributions over time
- **Project Planning** - Identify active areas and inform resource decisions
- **Team Health** - Detect inactive developers and potential issues
- **Sprint Reviews** - Compare velocity across sprints

### For Technical Leads

- **Code Review Prioritization** - Identify large changes needing review
- **Bus Factor Analysis** - Find single points of failure
- **Onboarding** - Track new developer integration
- **Quality Metrics** - Monitor code churn and commit patterns



## Author

Created by Naomi Ovadia (n0583267045@gmail.com)

Developed as a professional tool for development managers to gain insights into team performance and project health through natural language interactions with Claude.


---

**Built with:**
- [FastMCP](https://github.com/jlowin/fastmcp) - Model Context Protocol framework
- Python 3.8+
- Git

**Tested on:** ONNX Runtime (large-scale open-source project with 60+ active developers)
