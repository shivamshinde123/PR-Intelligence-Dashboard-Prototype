import os
import json
import httpx

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# AI rule file paths to check in the repository
AI_RULE_PATHS = [
    ".cursor/rules",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
    ".cursorrules",
]


def _build_headers():
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


async def lint_ai_rules(files: list, owner: str = "", repo: str = "") -> list:
    """Lint AI rule files — both those changed in the PR and those present in the repo.

    Returns a list of issue/info strings.
    """
    issues = []
    headers = _build_headers()

    # --- Layer 1: Check files CHANGED in this PR ---
    changed_ai_files = set()
    for f in files:
        filename = f.get("filename", "")
        if not filename:
            continue
        lower = filename.lower()
        for rule_path in AI_RULE_PATHS:
            if lower.endswith(rule_path.lower()):
                changed_ai_files.add(filename)
                raw_url = f.get("raw_url")
                if not raw_url:
                    issues.append(f"⚠️ Cannot fetch content for changed file: {filename}")
                    continue
                try:
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        resp = await client.get(raw_url, headers=headers)
                        resp.raise_for_status()
                        content = resp.text

                    # Validate content
                    if len(content.strip()) == 0:
                        issues.append(f"⚠️ {filename} is empty — AI rules will have no effect.")
                    elif filename.lower().endswith(".json") or filename.lower().endswith("rules"):
                        try:
                            json.loads(content)
                            issues.append(f"✅ {filename} — valid JSON, {len(content)} bytes.")
                        except json.JSONDecodeError:
                            if ":" not in content and "=" not in content:
                                issues.append(
                                    f"⚠️ {filename} — does not appear to be valid JSON or key-value format."
                                )
                            else:
                                issues.append(f"✅ {filename} — key-value format detected, {len(content)} bytes.")
                    else:
                        # Markdown files (CLAUDE.md, copilot-instructions.md)
                        word_count = len(content.split())
                        if word_count < 10:
                            issues.append(
                                f"⚠️ {filename} — only {word_count} words. Consider adding more detailed rules."
                            )
                        else:
                            issues.append(f"✅ {filename} — {word_count} words of AI instructions found.")
                except Exception as e:
                    issues.append(f"⚠️ Error linting {filename}: {e}")

    # --- Layer 2: Check if the REPO has AI rule files (even if not changed in this PR) ---
    if owner and repo:
        for rule_path in AI_RULE_PATHS:
            if rule_path in changed_ai_files:
                continue  # Already checked above
            try:
                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{rule_path}"
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        file_info = resp.json()
                        size = file_info.get("size", 0)
                        issues.append(
                            f"📄 Repo has `{rule_path}` ({size} bytes) — not modified in this PR."
                        )
                    # 404 = file doesn't exist, which is fine — skip silently
            except Exception:
                pass  # Network error checking repo contents — non-critical

    # If nothing was found at all, add a helpful note
    if not issues:
        issues.append(
            "ℹ️ No AI rules files (`.cursor/rules`, `CLAUDE.md`, `.cursorrules`, "
            "`.github/copilot-instructions.md`) found in this PR or repository."
        )

    return issues
