import os
import httpx
from urllib.parse import urlparse

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def _build_headers():
    """Build GitHub API headers, only including Authorization if token exists."""
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def parse_pr_url(pr_url: str):
    """Extract owner, repo, and pull number from a GitHub PR URL.
    Example: https://github.com/owner/repo/pull/123 -> ('owner', 'repo', 123)
    """
    parsed = urlparse(pr_url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 4 or parts[2] != "pull":
        raise ValueError(
            f"Invalid GitHub PR URL. Expected format: https://github.com/owner/repo/pull/123  Got: {pr_url}"
        )
    owner, repo, number = parts[0], parts[1], parts[3]
    return owner, repo, int(number)


async def get_pr_details(owner: str, repo: str, number: int):
    """Fetch PR diff, commits, files changed, and review comments.
    Returns a dict with keys: diff, commits, files, reviews.
    """
    headers = _build_headers()
    base = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # PR metadata
        pr_resp = await client.get(base, headers=headers)
        pr_resp.raise_for_status()
        pr_json = pr_resp.json()

        # Diff (use the .diff URL directly)
        diff_headers = {**headers, "Accept": "application/vnd.github.v3.diff"}
        diff_resp = await client.get(base, headers=diff_headers)
        diff_resp.raise_for_status()
        diff_text = diff_resp.text

        # Commits
        commits_resp = await client.get(f"{base}/commits", headers=headers)
        commits_resp.raise_for_status()
        commits = commits_resp.json()

        # Files changed
        files_resp = await client.get(f"{base}/files", headers=headers)
        files_resp.raise_for_status()
        files = files_resp.json()

        # Reviews
        reviews_resp = await client.get(f"{base}/reviews", headers=headers)
        reviews_resp.raise_for_status()
        reviews = reviews_resp.json()

        return {
            "pr": pr_json,
            "diff": diff_text,
            "commits": commits,
            "files": files,
            "reviews": reviews,
        }
