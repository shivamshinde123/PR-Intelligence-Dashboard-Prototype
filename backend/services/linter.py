import os
import json

# Simple linter for AI rules files
# Checks for presence of .cursor/rules or CLAUDE.md and validates basic JSON/YAML structure

async def lint_ai_rules(files: list) -> list:
    """Lint AI rule files touched in the PR.
    Returns a list of issue strings.
    """
    issues = []
    for f in files:
        filename = f.get('filename') or f.get('raw_url')
        if not filename:
            continue
        lower = filename.lower()
        if lower.endswith('.cursor/rules') or lower.endswith('claude.md'):
            # Fetch file content (assuming raw_url is provided)
            raw_url = f.get('raw_url')
            if not raw_url:
                issues.append(f"Cannot fetch content for {filename}")
                continue
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.get(raw_url)
                    resp.raise_for_status()
                    content = resp.text
                # Very naive validation: check if JSON or YAML-like key-value
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    # Simple YAML check: look for ':' separator
                    if ':' not in content:
                        issues.append(f"{filename} does not appear to be valid JSON or YAML.")
            except Exception as e:
                issues.append(f"Error linting {filename}: {e}")
    return issues
