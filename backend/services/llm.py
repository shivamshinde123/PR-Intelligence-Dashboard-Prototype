import os
import httpx
import json

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Truncate large diffs to avoid blowing through token limits
MAX_DIFF_CHARS = 12000
MAX_FILES_CHARS = 4000
MAX_COMMITS_CHARS = 2000
MAX_REVIEWS_CHARS = 2000
MAX_REVIEW_COMMENTS_CHARS = 3000
MAX_ISSUE_COMMENTS_CHARS = 2000


def _truncate(text: str, limit: int) -> str:
    if len(text) > limit:
        return text[:limit] + "\n... [truncated]"
    return text


SYSTEM_PROMPT = """You are an expert software engineer and code reviewer.
Analyze the GitHub Pull Request data provided and return ONLY a valid JSON object (no markdown, no explanation outside the JSON) with exactly these keys:

- "complexity_score": float 0-10 (how complex is this PR)
- "expert_hours": float (estimated hours for a senior engineer to produce this work)
- "work_type": one of "feature", "bug", "tech_debt", "maintenance"
- "ai_attribution_confidence": float 0-1 (probability the code was AI-generated. Use BOTH the stylistic analysis of the diff AND the git co-author / committer signals provided in the "AI Signals" section. If co-author trailers like "Co-authored-by: GitHub Copilot" are detected, weight that heavily.)
- "review_quality_score": float 0-10 (quality of review comments on specificity, actionability, and tone; 0 if no reviews)
- "linter_issues": list of strings (any issues found; empty list if none)
- "reasoning": string (2-4 sentence explanation of your scores. If AI co-author signals were detected, mention them explicitly.)

Return ONLY the JSON object. No markdown code fences. No extra text."""


async def analyze_pr(pr_data: dict) -> dict:
    """Send PR data to Claude Messages API and get structured analysis."""
    if not CLAUDE_API_KEY:
        raise RuntimeError("CLAUDE_API_KEY not set in environment")

    diff_text = _truncate(pr_data.get("diff", ""), MAX_DIFF_CHARS)
    commits_text = _truncate(json.dumps(pr_data.get("commits", []), indent=2), MAX_COMMITS_CHARS)
    files_text = _truncate(json.dumps(pr_data.get("files", []), indent=2), MAX_FILES_CHARS)
    reviews_text = _truncate(json.dumps(pr_data.get("reviews", []), indent=2), MAX_REVIEWS_CHARS)
    review_comments_text = _truncate(
        json.dumps(pr_data.get("review_comments", []), indent=2), MAX_REVIEW_COMMENTS_CHARS
    )
    issue_comments_text = _truncate(
        json.dumps(pr_data.get("issue_comments", []), indent=2), MAX_ISSUE_COMMENTS_CHARS
    )

    # Format AI co-author / committer signals for the LLM
    ai_signals = pr_data.get("ai_signals", {})
    if ai_signals.get("ai_coauthor_found"):
        signals_text = (
            f"AI CO-AUTHOR DETECTED: {ai_signals['ai_commits']}/{ai_signals['total_commits']} "
            f"commits have AI signals.\n"
            f"Signals found:\n" +
            "\n".join(f"  - {s}" for s in ai_signals.get("signals", []))
        )
    else:
        signals_text = (
            "No AI co-author trailers or known AI committer emails were detected in the git history. "
            "Rely on stylistic analysis of the diff for AI attribution."
        )

    user_message = (
        f"## PR Diff\n{diff_text}\n\n"
        f"## Commits\n{commits_text}\n\n"
        f"## Files Changed\n{files_text}\n\n"
        f"## Review Summaries\n{reviews_text}\n\n"
        f"## Inline Code Review Comments\n{review_comments_text}\n\n"
        f"## Discussion Comments\n{issue_comments_text}\n\n"
        f"## AI Signals (from git co-author detection)\n{signals_text}"
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "temperature": 0,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": user_message}
                ],
            },
        )
        response.raise_for_status()
        result = response.json()

        # Extract text from the response content blocks
        raw_text = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                raw_text += block["text"]

        # Strip any accidental markdown fences
        raw_text = raw_text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]  # remove first line
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        try:
            analysis = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse Claude response as JSON: {e}\nRaw response:\n{raw_text[:500]}"
            )

        # Boost AI attribution if git signals were found but LLM scored low
        if ai_signals.get("ai_coauthor_found"):
            llm_confidence = analysis.get("ai_attribution_confidence", 0)
            # Ensure at least 0.6 if co-author trailers are present
            if llm_confidence < 0.6:
                analysis["ai_attribution_confidence"] = max(llm_confidence, 0.6)

        return analysis
