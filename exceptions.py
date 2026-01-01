"""Custom exceptions for git operations."""


class GitError(Exception):
    """Base class for all git-related errors."""
    pass


class GitNotFoundError(GitError):
    """Raised when git executable is not found in PATH."""

    def __init__(self, message: str = "Git not found in PATH. Please install git."):
        super().__init__(message)


class GitRepositoryError(GitError):
    """Raised when path is not a valid git repository."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        super().__init__(f"Not a valid git repository: {repo_path}")


class GitCommandError(GitError):
    """Raised when a git command fails."""

    def __init__(self, command: str, error: str):
        self.command = command
        self.error = error
        super().__init__(f"git {command} failed: {error}")


class GitTimeoutError(GitError):
    """Raised when a git command times out."""

    def __init__(self, command: str, timeout: int):
        self.command = command
        self.timeout = timeout
        super().__init__(f"git {command} timed out after {timeout} seconds")
