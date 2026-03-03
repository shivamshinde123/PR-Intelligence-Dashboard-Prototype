import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

# Import service functions (after dotenv so env vars are available)
from services.github import parse_pr_url, get_pr_details
from services.linter import lint_ai_rules
from services.llm import analyze_pr

app = FastAPI()

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    pr_url: HttpUrl

class AnalysisResponse(BaseModel):
    complexity_score: float
    expert_hours: float
    work_type: str
    ai_attribution_confidence: float
    review_quality_score: float
    linter_issues: list
    reasoning: str

@app.post("/api/analyze-pr", response_model=AnalysisResponse)
async def analyze_pr_endpoint(request: AnalysisRequest):
    # 1. Parse owner, repo, number from URL
    try:
        owner, repo, number = parse_pr_url(str(request.pr_url))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PR URL: {e}")

    # 2. Fetch PR data from GitHub
    try:
        pr_data = await get_pr_details(owner, repo, number)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch PR data from GitHub: {e}",
        )

    # 3. Run LLM analysis
    try:
        result = await analyze_pr(pr_data)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM analysis failed: {e}",
        )

    # 4. Run AI rules linter on changed files
    try:
        linter_issues = await lint_ai_rules(pr_data.get("files", []))
    except Exception:
        linter_issues = []

    # 5. Merge linter results into the analysis dict
    if isinstance(result, dict):
        result["linter_issues"] = linter_issues
    else:
        result = result.dict()
        result["linter_issues"] = linter_issues

    return result
