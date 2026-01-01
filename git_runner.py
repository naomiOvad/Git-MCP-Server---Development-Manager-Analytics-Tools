import asyncio
import os
import shutil
from typing import List

from exceptions import GitNotFoundError, GitRepositoryError, GitCommandError, GitTimeoutError


async def ensure_is_git_repo(repo_path: str) -> None:
    """Verify that the given path is a valid git repository."""
    if not repo_path or not isinstance(repo_path, str):
        raise ValueError("repo_path must be a non-empty string")

    if not os.path.isdir(repo_path):
        raise GitRepositoryError(repo_path)

    await run_git(repo_path, ["rev-parse", "--git-dir"])


def git_exe() -> str:
    """Find git executable in PATH."""
    git = shutil.which("git")
    if not git:
        raise GitNotFoundError()
    return git


async def run_git(repo_path: str, args: List[str], timeout_s: int = 60) -> str:
    """
    Execute git command and return stdout.

    Args:
        repo_path: Repository directory path
        args: Git command arguments (e.g., ["status", "--short"])
        timeout_s: Command timeout in seconds

    Returns:
        Command stdout as string

    Raises:
        RuntimeError: If git not found, command fails, or times out
    """
    git = git_exe()

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_PAGER"] = ""
    env["PAGER"] = ""

    proc = await asyncio.create_subprocess_exec(
        git,
        "--no-pager",
        *args,
        cwd=repo_path,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        proc.kill()
        raise GitTimeoutError(' '.join(args), timeout_s)

    out = out_b.decode("utf-8", errors="replace")
    err = err_b.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        raise GitCommandError(' '.join(args), err.strip())

    return out
