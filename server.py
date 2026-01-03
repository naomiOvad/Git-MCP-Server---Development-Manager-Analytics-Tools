from mcp.server.fastmcp import FastMCP

from tools.git_branches import register as register_git_branches
from tools.git_commit_history import register as register_git_commit_history
from tools.git_developer_stats import register as register_git_developer_stats
from tools.git_compare_developers import register as register_git_compare_developers
from tools.git_file_changes import register as register_git_file_changes
from tools.git_sync import register as register_git_sync
from tools.git_dashboard import register as register_git_dashboard
from prompts import register_prompts

mcp = FastMCP("git-mcp")

register_git_branches(mcp)
register_git_commit_history(mcp)
register_git_developer_stats(mcp)
register_git_compare_developers(mcp)
register_git_file_changes(mcp)
register_git_sync(mcp)
register_git_dashboard(mcp)
register_prompts(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
