# PR Intelligence Dashboard - Code Flow Documentation

## **Overview**

This is a full-stack web application that analyzes GitHub Pull Requests using Claude (Anthropic's LLM) to provide intelligent metrics and insights. Here's how the whole system works:

---

## **Architecture Overview**

The application has three main layers:

1. **Frontend** (React + Vite + Tailwind CSS) - User interface
2. **Backend** (FastAPI + Python) - API server
3. **External APIs** - GitHub API + Anthropic Claude API

---

## **How It Works - Complete Workflow**

### **Step 1: User Input**
The user pastes a GitHub PR URL (like `https://github.com/owner/repo/pull/123`) into the frontend. When they click "Analyze PR", the frontend sends a POST request to `/api/analyze-pr`.

### **Step 2: Backend Processing (`main.py`)**
The backend receives the request and follows this pipeline:

1. **Parse the URL** - Extracts owner, repo, and PR number
2. **Check cache** - Looks in an in-memory dictionary to see if this PR was already analyzed (avoids redundant API calls)
3. **Fetch PR data from GitHub** - Calls `github.py`
4. **Run LLM analysis** - Sends data to Claude via `llm.py`
5. **Run linter** - Checks AI rules files via `linter.py`
6. **Cache and return** - Stores result and sends back to frontend

### **Step 3: GitHub Data Collection (`github.py`)**
The `get_pr_details()` function makes multiple GitHub API calls to collect:

- **PR metadata** - Title, description, author
- **Diff** - The actual code changes (unified diff format)
- **Commits** - All commits in the PR with messages
- **Files changed** - List of modified files with additions/deletions
- **Review comments** - Both inline code comments and discussion comments
- **Reviews** - Approval/rejection statuses

**AI Signal Detection**: Before sending to Claude, it scans commit messages and git metadata for evidence of AI-generated code:
- Looks for `Co-authored-by: GitHub Copilot` trailers
- Checks for known AI committer emails like `copilot@github.com`
- Scans for bot names in committer/author fields

### **Step 4: LLM Analysis (`llm.py`)**
The `analyze_pr()` function:

1. **Truncates large data** - Keeps diff under 12,000 chars, commits under 2,000, etc. (to fit within Claude's token limits)
2. **Formats a prompt** - Combines all PR data into sections:
   ```
   ## PR Diff
   [code changes]
   
   ## Commits
   [commit history]
   
   ## Files Changed
   [file metadata]
   
   ## Review Summaries
   [review feedback]
   
   ## AI Signals
   [git co-author detection results]
   ```

3. **Sends to Claude API** - Uses `claude-sonnet-4-20250514` model with:
   - **System prompt** - Instructs Claude to return JSON with specific fields
   - **Temperature 0** - Ensures consistent scoring
   - **Max tokens 1024** - Limits response length

4. **Receives structured JSON** from Claude:
   ```json
   {
     "complexity_score": 5.0,
     "expert_hours": 3.5,
     "work_type": "feature",
     "ai_attribution_confidence": 0.25,
     "review_quality_score": 7.0,
     "reasoning": "This PR adds..."
   }
   ```

5. **Boosts AI confidence if git signals found** - If co-author trailers were detected but Claude scored low, it raises the AI attribution to at least 0.6 (because git metadata is hard evidence)

### **Step 5: AI Rules Linter (`linter.py`)**
The `lint_ai_rules()` function:

1. **Scans changed files** - Looks for `.cursor/rules`, `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`
2. **Fetches file content** - Downloads the raw file from GitHub
3. **Validates format**:
   - For JSON files → tries to parse as JSON
   - For Markdown files → counts words, warns if too short
   - Checks for empty files
4. **Also checks the repository** - Even if files weren't changed in the PR, it checks if they exist in the repo and reports their size

This is useful because teams using AI coding assistants (Cursor, Copilot, Claude Code) configure these files, and a malformed file silently breaks AI behavior.

### **Step 6: Frontend Display (`Dashboard.jsx`)**
The React dashboard displays:

- **Score tiles** - Complexity, Expert Hours, Review Quality, Work Type (with color coding)
- **Bar charts** - Visual representation of scores with animations
- **Linter results** - List of issues/info about AI rules files
- **Reasoning** - Claude's 2-4 sentence explanation
- **Export button** - Downloads a `.txt` report

---

## **Key Features**

### **1. Complexity Score (0-10)**
Claude evaluates:
- Size of diff (lines/files changed)
- Nature of changes (new feature vs. typo fix)
- Semantic complexity (algorithms vs. config tweaks)
- Cross-cutting concerns (changes affecting multiple files)

### **2. Expert Hours**
Estimated wall-clock time a senior engineer would need to produce the same work. Claude considers:
- Amount of non-trivial code
- Implied setup work (research, design, testing)
- Cognitive load of the domain
- Visible iteration in commits/reviews

### **3. AI Attribution Confidence (0.0-1.0)**
**Two-layer approach**:
1. **Git metadata detection** (hard evidence) - co-author trailers, bot emails, bot names
2. **LLM stylistic analysis** (soft signals) - uniform formatting, verbose comments, cookie-cutter patterns

The two layers combine: git signals provide an evidence floor (minimum 0.6), and LLM analysis can push higher.

### **4. Review Quality Score (0-10)**
Claude evaluates review comments on:
- Specificity (exact lines + explanations)
- Actionability (clear suggestions vs. vague "LGTM")
- Tone (constructive vs. hostile)
- Coverage (critical parts vs. cosmetic issues)
- Depth (discussion vs. rubber-stamp approval)

### **5. Work Type Classification**
- `feature` - New functionality
- `bug` - Bug fixes
- `tech_debt` - Refactoring, cleanup
- `maintenance` - Dependencies, configs

---

## **Technical Implementation Highlights**

**Caching**: In-memory Python dictionary (`_cache`) keyed by `owner/repo/number` to avoid redundant API calls. Cache persists only during server runtime.

**Error handling**: 
- 400 for invalid PR URLs
- 502 for GitHub/Claude API failures
- 500 for missing API keys or parse errors

**CORS**: Allows frontend to call backend from different origin

**Async operations**: Uses `httpx.AsyncClient` for non-blocking GitHub/Claude API calls

**Truncation strategy**: Truncates from the end with `[truncated]` marker to fit token limits

**Markdown fence stripping**: Removes accidental ` ```json` fences from Claude's response before parsing

---

## **Why LLM-Based Scoring?**

Traditional approaches use formulas like "lines changed × 0.1 = hours". This project uses Claude instead because:

1. **Context-aware** - Understands semantic meaning ("add async endpoint" vs. "bump version")
2. **Human-like judgment** - Trained on vast code review data
3. **Easily tunable** - Adjust by editing the system prompt, no code changes
4. **Transparent** - Includes reasoning field explaining the scores

---

## **Example Flow**

```
User pastes: https://github.com/fastapi/fastapi/pull/13500
                            ↓
Backend parses → owner: fastapi, repo: fastapi, number: 13500
                            ↓
Checks cache (miss) → Fetches from GitHub API:
   - Diff: 2,341 lines changed
   - Commits: 5 commits
   - Files: 8 files changed
   - Reviews: 2 approvals
   - AI signals: No co-author trailers found
                            ↓
Sends to Claude API with system prompt
                            ↓
Claude returns JSON:
   {
     "complexity_score": 6.5,
     "expert_hours": 4.0,
     "work_type": "feature",
     "ai_attribution_confidence": 0.15,
     "review_quality_score": 8.0,
     "reasoning": "This PR introduces async support..."
   }
                            ↓
Runs linter → finds .cursor/rules file (valid JSON, 234 bytes)
                            ↓
Caches result → Returns to frontend
                            ↓
Dashboard displays with animations and color coding
```

---

## **Detailed Component Breakdown**

### **Backend Components**

#### **`main.py` - FastAPI Application**
- **Responsibilities**: 
  - Route handling (`/api/analyze-pr`)
  - Request/response validation with Pydantic
  - Cache management
  - CORS middleware configuration
  - Orchestration of all services

- **Key Functions**:
  - `analyze_pr_endpoint()` - Main endpoint handler
  - `_cache_key()` - Generates cache keys from PR identifiers

#### **`services/github.py` - GitHub API Client**
- **Responsibilities**:
  - GitHub API authentication (with optional token)
  - PR data fetching (diff, commits, files, reviews)
  - AI signal detection from git metadata

- **Key Functions**:
  - `parse_pr_url()` - Extracts owner/repo/number from URL
  - `get_pr_details()` - Fetches comprehensive PR data
  - `detect_ai_signals()` - Scans commits for AI co-author patterns
  - `_build_headers()` - Constructs GitHub API headers

- **AI Detection Patterns**:
  ```python
  AI_EMAILS = {
      "noreply@github.com",
      "copilot@github.com",
      "github-actions[bot]@users.noreply.github.com",
  }
  
  AI_COAUTHOR_PATTERNS = [
      r"Co-authored-by:.*GitHub\s*Copilot",
      r"Co-authored-by:.*Cursor",
      r"Co-authored-by:.*\bAI\b",
      r"Co-authored-by:.*\bbot\b",
  ]
  ```

#### **`services/llm.py` - Claude API Client**
- **Responsibilities**:
  - Data truncation for token limits
  - Prompt formatting
  - Claude API communication
  - Response parsing and validation
  - AI attribution confidence boosting

- **Key Functions**:
  - `analyze_pr()` - Sends PR data to Claude, returns analysis
  - `_truncate()` - Truncates text to character limits

- **Truncation Limits**:
  ```python
  MAX_DIFF_CHARS = 12000
  MAX_FILES_CHARS = 4000
  MAX_COMMITS_CHARS = 2000
  MAX_REVIEWS_CHARS = 2000
  MAX_REVIEW_COMMENTS_CHARS = 3000
  MAX_ISSUE_COMMENTS_CHARS = 2000
  ```

- **System Prompt Strategy**: 
  - Instructs Claude to return ONLY JSON
  - Specifies exact schema with field types and ranges
  - Emphasizes using both stylistic analysis AND git signals
  - Requests 2-4 sentence reasoning

#### **`services/linter.py` - AI Rules File Validator**
- **Responsibilities**:
  - Scanning PR changes for AI rule files
  - Fetching and validating file content
  - Checking repository for existing rule files
  - Format validation (JSON/YAML/Markdown)

- **Key Functions**:
  - `lint_ai_rules()` - Main linter orchestrator
  - `_build_headers()` - Constructs GitHub API headers

- **Checked Files**:
  ```python
  AI_RULE_PATHS = [
      ".cursor/rules",
      "CLAUDE.md",
      ".github/copilot-instructions.md",
      ".cursorrules",
  ]
  ```

---

### **Frontend Components**

#### **`App.jsx` - Main Application Component**
- **Responsibilities**:
  - State management (URL, loading, result, error)
  - Form submission handling
  - Conditional rendering of loading/error/success states

- **State Flow**:
  ```
  Initial → User enters URL → Loading → (Success | Error)
  ```

#### **`Dashboard.jsx` - Results Display Component**
- **Responsibilities**:
  - Visualizing analysis results
  - Color-coded score displays
  - Bar chart rendering with animations
  - Export functionality

- **Sub-Components**:
  - `ScoreTile` - Individual metric display
  - `Bar` - Animated progress bar
  - `WorkBadge` - Categorized work type badge
  - `exportSummary()` - Generates downloadable text report

- **Color Coding Logic**:
  ```javascript
  Complexity/Review Quality:
  - 0-4: Green (low complexity / poor review)
  - 4-7: Amber (moderate)
  - 7-10: Red (high complexity / excellent review)
  ```

#### **`api.js` - API Client**
- **Responsibilities**:
  - Fetch wrapper for backend communication
  - Error handling and response parsing

---

## **Data Flow Diagram**

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                     (React Frontend - App.jsx)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ POST /api/analyze-pr
                             │ { pr_url: "..." }
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│                        (main.py)                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. Parse URL → owner/repo/number                          │  │
│  │ 2. Check cache (dict lookup)                              │  │
│  │ 3. If miss → fetch from GitHub                            │  │
│  │ 4. Run LLM analysis                                       │  │
│  │ 5. Run linter                                             │  │
│  │ 6. Cache result                                           │  │
│  │ 7. Return JSON                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└────┬──────────────────────┬──────────────────────┬──────────────┘
     │                      │                      │
     │ github.py            │ llm.py               │ linter.py
     ▼                      ▼                      ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  GitHub API  │   │  Claude API      │   │  GitHub API      │
│              │   │                  │   │  (file content)  │
│ - PR data    │   │ - Analysis       │   │                  │
│ - Diff       │   │ - Scoring        │   │ - Rule files     │
│ - Commits    │   │ - Reasoning      │   │ - Validation     │
│ - Reviews    │   │                  │   │                  │
└──────────────┘   └──────────────────┘   └──────────────────┘
```

---

## **API Contract**

### **Request**
```http
POST /api/analyze-pr
Content-Type: application/json

{
  "pr_url": "https://github.com/owner/repo/pull/123"
}
```

### **Response (Success - 200)**
```json
{
  "complexity_score": 5.0,
  "expert_hours": 3.5,
  "work_type": "feature",
  "ai_attribution_confidence": 0.25,
  "review_quality_score": 7.0,
  "linter_issues": [
    "✅ .cursor/rules — valid JSON, 234 bytes.",
    "ℹ️ No CLAUDE.md found in repository."
  ],
  "reasoning": "This PR adds a new authentication module with JWT support. The changes span 8 files with moderate complexity. No AI co-author signals detected in git history."
}
```

### **Response (Error - 400/500/502)**
```json
{
  "detail": "Invalid PR URL: Expected format: https://github.com/owner/repo/pull/123"
}
```

---

## **Environment Configuration**

### **Required**
- `CLAUDE_API_KEY` - Anthropic API key for LLM analysis

### **Optional**
- `GITHUB_TOKEN` - GitHub personal access token
  - **Without token**: 60 requests/hour rate limit
  - **With token**: 5,000 requests/hour rate limit

### **`.env` File Format**
```env
CLAUDE_API_KEY=sk-ant-api03-your-key-here
GITHUB_TOKEN=ghp_your-token-here
```

---

## **Security Considerations**

1. **API Key Protection**: 
   - `.env` file excluded via `.gitignore`
   - Keys loaded via `python-dotenv`
   - Never exposed to frontend

2. **Public PRs Only**: 
   - Default GitHub token scope only accesses public repos
   - Private repo access requires `repo` scope (not recommended for public deployment)

3. **CORS Configuration**: 
   - Currently allows all origins (`allow_origins=["*"]`)
   - Production deployment should restrict to specific frontend domain

4. **Rate Limiting**: 
   - In-memory cache reduces API calls
   - Consider adding Redis for distributed caching in production

---

## **Performance Optimizations**

1. **Caching Strategy**: 
   - In-memory dictionary prevents redundant GitHub/Claude API calls
   - Cache persists for server lifetime
   - Cache key: normalized `owner/repo/number`

2. **Truncation**: 
   - Large diffs truncated to 12,000 characters
   - Prevents token limit errors
   - Preserves most informative content from start of diff

3. **Async Operations**: 
   - All GitHub API calls use `httpx.AsyncClient`
   - Non-blocking I/O for concurrent requests
   - Timeout: 30 seconds for GitHub, 120 seconds for Claude

4. **Frontend Optimizations**: 
   - CSS animations use `transform` and `opacity` (GPU-accelerated)
   - Lazy loading of dashboard component
   - Single API call per analysis

---

## **Future Enhancement Opportunities**

1. **Persistence Layer**: 
   - Replace in-memory cache with Redis
   - Add database for historical tracking
   - Enable trend analysis across PRs

2. **Batch Processing**: 
   - Analyze all open PRs in a repository
   - Compare scores across team members
   - Identify patterns in PR quality

3. **OAuth Flow**: 
   - Support private repositories
   - User authentication via GitHub OAuth
   - Personalized API rate limits

4. **Extended Linting**: 
   - Support more AI rule file formats
   - Validate ESLint AI configs
   - Check for deprecated rule patterns

5. **Deployment**: 
   - Frontend on Vercel
   - Backend on Railway/Render
   - Environment-specific configurations

---

## **Testing the Application**

### **Quick Manual Test**
```bash
# Test backend endpoint directly
curl -X POST http://127.0.0.1:8000/api/analyze-pr \
  -H "Content-Type: application/json" \
  -d '{"pr_url":"https://github.com/fastapi/fastapi/pull/13500"}'
```

### **Expected Response Time**
- **Small PRs** (< 100 lines): 5-10 seconds
- **Medium PRs** (100-1000 lines): 15-20 seconds
- **Large PRs** (> 1000 lines): 20-30 seconds

*Time includes GitHub API calls + Claude analysis + linting*

---

## **Error Handling Flow**

```
Request → Parse URL
           ├─ Invalid format → 400 Bad Request
           │
           └─ Valid → Check cache
                       │
                       └─ Fetch GitHub data
                           ├─ API error → 502 Bad Gateway
                           │
                           └─ Success → Call Claude API
                                         ├─ Missing API key → 500 Internal Server Error
                                         ├─ API error → 502 Bad Gateway
                                         ├─ Parse error → 500 Internal Server Error
                                         │
                                         └─ Success → Run linter
                                                       ├─ Linter error → Continue (non-critical)
                                                       │
                                                       └─ Cache result → 200 OK
```

---

## **Key Design Decisions**

### **Why FastAPI?**
- Native async support for I/O-bound operations
- Automatic request/response validation with Pydantic
- Built-in OpenAPI documentation
- High performance (comparable to Node.js/Go)

### **Why React + Vite?**
- Fast development with hot module replacement
- Modern build tooling with minimal configuration
- Tree-shaking for smaller bundle sizes
- Native ES modules support

### **Why In-Memory Caching?**
- Simple implementation for prototype/demo
- No external dependencies (Redis, Memcached)
- Sufficient for low-to-medium traffic
- Easy to replace with distributed cache later

### **Why Two-Layer AI Detection?**
- **Git signals** provide hard evidence (co-author trailers)
- **LLM analysis** catches stylistic patterns git misses
- Combined approach reduces false negatives/positives
- Transparency: users see both git and stylistic reasoning

---

This documentation provides a complete understanding of how the PR Intelligence Dashboard works, from user interaction to API responses, including all technical implementation details and design rationale.