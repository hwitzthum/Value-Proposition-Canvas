# Value Proposition Canvas — AI-Powered Coaching Application

A professional, AI-assisted application for creating high-quality Value Proposition Canvases with real-time validation, collaborative sharing, and multi-format export.

## ✨ Key Highlights

- **Guided workflow** with proactive AI coaching at each step
- **Multi-format export**: Word, PDF, CSV, and JSON
- **Shareable links** with password protection and expiry
- **Smart nudges** that highlight gaps in your canvas before publishing
- **Real-time validation** with immediate quality feedback
- **Accessible interface** with themes, high contrast, low motion, and large text options
- **Role-based authentication** with admin dashboard for user management
- **Enterprise-ready** with rate limiting, XSS protection, and secure session management

---

## 🎯 Features Overview

### 1. **Guided Workflow with AI Coaching**

The application walks you through a structured 5-step process:

1. **Define Your Job** — Describe your work objective or role in one clear statement
2. **List Pain Points** — Identify 7+ specific obstacles, frustrations, or friction points
3. **List Gain Points** — Define 8+ outcomes, benefits, or goals you want to achieve
4. **Review Canvas** — See your complete canvas before exporting
5. **Export & Share** — Download, export data, or share via secure links

**Example:**
```
Job: Improve productivity for software engineers during code reviews
Pain Point: Waiting 2-3 days for feedback from busy senior developers
Gain Point: Have code quality feedback available within 4 hours
```

### 2. **Real-Time Validation & Quality Feedback**

Every section validates automatically as you type:
- **Job description** must be clear, specific, and measurable
- **Pain/gain points** are checked for specificity, independence, and relevance to the job
- **Duplicate detection** flags similar items and suggests merging
- **Smart suggestions** from AI coaching improve weak items

**Example Output:**
```json
{
  "valid": false,
  "message": "Need 7 pain points (you have 5)",
  "issues": [
    "Pain point 'Things are hard' is too vague. Add specifics.",
    "Pain points #2 and #3 are 85% similar. Consider merging."
  ],
  "positive_feedback": "Great specificity on pain point #1!"
}
```

### 3. **Proactive AI Nudges** ⭐ *New*

While building your canvas, the app automatically detects and nudges you on:

- **Dimension Imbalance** — "80% of your pain points are functional. Consider emotional pain (stress, frustration)."
- **Low Specificity** — "Your pain points average 55% specificity. Add measurable details."
- **Coverage Gaps** — "You have 8 gain points but only 3 pain points. Balance your canvas."
- **Near Threshold** — "You have 6 pain points. Add 1-2 more to reach the recommended 7."
- **Weak Job Description** — "Your job description lacks clarity. Make it more specific."

Nudges appear as dismissible cards and update in real-time.

### 4. **Shareable Read-Only Links** ⭐ *New*

Share your completed canvas with stakeholders without granting edit access:

- **Generate a share link** with one click
- **Optional password protection** (min. 8 characters)
- **Optional expiry** (set exact expiration date/time)
- **Revoke anytime** — immediately disables the link
- **Read-only view** — viewers can read but not edit your canvas

**Example Share Flow:**
```
1. Click "Share Canvas" button
2. Set optional password: "Secure123!"
3. Set expiry: "7 days from now"
4. Copy link: https://app.example.com/shared/abc123def456
5. Send to stakeholders
6. They access with read-only view (no editing, no downloads)
```

### 5. **Multi-Format Export** ⭐ *New*

Download your canvas in your choice of formats:

- **Word (DOCX)** — Professional document with formatting, timestamps, and numbering
- **PDF** — Print-ready format with styled sections and quality summary
- **CSV** — Spreadsheet-friendly format for data analysis or further processing
- **JSON** — Machine-readable format for programmatic use or round-trip importing

**Example JSON Export:**
```json
{
  "version": "1.0",
  "exported_at": "2026-03-16T14:30:00Z",
  "title": "Engineering Productivity Canvas",
  "job_description": "Improve code review throughput",
  "pain_points": [
    "2-3 day review cycles",
    "Async feedback loses context",
    "Junior devs blocked waiting for approval"
  ],
  "gain_points": [
    "4-hour max review time",
    "Real-time feedback chat",
    "Unblock junior developers"
  ]
}
```

### 6. **Import & Backup Your Data** ⭐ *New*

Never lose your work:

- **Export JSON** to create backups or version control
- **Import JSON** to restore previous versions or templates
- **Round-trip safe** — export and re-import preserves all data
- **Validation on import** — rejects invalid or oversized submissions
- **XSS protection** — sanitizes all imported data

### 7. **Accessibility & Theming**

Customize the interface to your needs:
- **Themes**: Light, Dark, Sepia, Ocean
- **High Contrast Mode** for visual impairments
- **Low Motion Mode** for motion sensitivity
- **Large Text** for better readability
- **Keyboard shortcuts** for power users

### 8. **AI-Powered Suggestions** (Optional)

With OpenAI API key configured:
- Get concrete alternatives for vague job descriptions
- Discover overlooked pain/gain points for your context
- Improve individual items with AI coaching
- Merge similar items with AI-suggested consolidations

**Example:**
```
Your job: "Be better at work"
AI suggestions:
  → "Reduce context switching in daily development cycle"
  → "Speed up deployment pipeline to production"
  → "Improve team communication during code reviews"
```

### 9. **Admin Dashboard**

For team deployments:
- User approval workflow (pending → active)
- Block/unblock users
- View user activity and canvas counts
- Reset passwords
- Manage system configuration

### 10. **Session Auto-Save**

Your canvas is automatically saved as you work:
- All changes persisted to backend
- Automatic recovery if browser crashes
- No manual "save" button needed

---

## 📊 How This Compares to Market Leaders

| Feature | This App | Miro | Figma | Notion | Lucidchart |
|---------|----------|------|-------|--------|-----------|
| **Guided Workflow** | ✅ 5-step coaching | ❌ Blank canvas | ❌ Blank canvas | ❌ Blank canvas | ❌ Blank canvas |
| **AI Validation** | ✅ Real-time quality checks | ❌ No validation | ❌ No validation | ⚠️ Manual only | ❌ No validation |
| **Proactive Nudges** | ✅ Smart context-aware hints | ❌ None | ❌ None | ❌ None | ❌ None |
| **Multi-Format Export** | ✅ Word, PDF, CSV, JSON | ❌ Image/PDF only | ❌ Image only | ✅ PDF, CSV | ✅ PDF, PNG, CSV |
| **Shareable Links** | ✅ Secure, password-protected | ✅ Basic sharing | ✅ Basic sharing | ✅ Basic sharing | ✅ Basic sharing |
| **JSON Import/Export** | ✅ Full round-trip backup | ❌ No JSON | ❌ No JSON | ✅ Database export | ❌ No JSON |
| **Accessibility** | ✅ High contrast, large text, low motion | ⚠️ Basic WCAG | ⚠️ Basic WCAG | ⚠️ Basic WCAG | ⚠️ Basic WCAG |
| **Authentication** | ✅ Email + role-based access | ❌ OAuth only | ❌ OAuth only | ❌ OAuth only | ❌ OAuth only |
| **Lean/Fast** | ✅ ~2s load time, no bloat | ❌ Heavy JS bundle | ❌ Heavy JS bundle | ⚠️ Moderate | ❌ Heavy |
| **Self-Hostable** | ✅ Docker Compose ready | ❌ SaaS only | ❌ SaaS only | ❌ SaaS only | ❌ SaaS only |
| **Price** | ✅ Open source | ❌ $120+/mo | ❌ $120+/mo | ❌ $10+/mo | ❌ $99+/mo |

**Unique Strengths:**
1. **Best-in-class AI coaching** — Not just a blank canvas; the app teaches you how to build a quality canvas
2. **Validation + guidance** — Tells you *why* something is weak and *how* to fix it
3. **Smartly targeted nudges** — Hints appear exactly when you need them, not overwhelming
4. **Open-source + self-hostable** — Deploy on your infrastructure with full control
5. **Lean and fast** — No unnecessary features; focused on the core job

---

## 🚀 Quick Start

### Option 1: Local Development (2 minutes)

**Prerequisites:** Python 3.11+, `uv` package manager

```bash
# Clone and navigate to project
git clone <repo>
cd value-proposition-canvas

# Install dependencies (handles venv + all packages)
uv sync

# Activate virtual environment
source .venv/bin/activate

# Copy example environment file
cp .env.example .env
# (Optional) Add OpenAI API key for AI suggestions

# Terminal 1: Start backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start frontend
streamlit run ui/streamlit_app.py

# Open http://localhost:8501
```

### Option 2: Docker Compose (1 minute)

**Prerequisites:** Docker & Docker Compose

```bash
git clone <repo>
cd value-proposition-canvas
docker compose up
# Open http://localhost:8501
```

### Option 3: Cloud Deployment (Render.com)

See [DEPLOYMENT.md](./DEPLOYMENT.md) for Render.com setup with PostgreSQL.

---

## 🎮 First Canvas: Step-by-Step Tutorial

### Step 1: Theme & Accessibility (30 seconds)

1. Open the app at http://localhost:8501
2. Click **Appearance** (top-right)
3. Pick a theme: Light, Dark, Sepia, or Ocean
4. (Optional) Enable High Contrast, Low Motion, or Large Text

### Step 2: Define Your Job (2 minutes)

1. In the **Job Description** box, write one clear objective:
   ```
   Reduce code review cycle time from 3 days to 4 hours
   ```

2. Click **Validate Now** to check quality
3. If feedback appears, refine until validation passes
4. Click **Continue** to proceed

### Step 3: Add Pain Points (3 minutes)

1. Add 7+ specific pain points. You can:
   - Type in the text box and press `Enter` to add
   - Click **Suggest from AI** to get context-specific ideas
   - Click **Validate Now** to check quality

   **Example pain points:**
   ```
   1. Senior developers are bottleneck for approvals
   2. Waiting 2-3 days blocks junior developers
   3. Async feedback loses context and requires clarification
   4. Reviewers context-switch between multiple PRs
   5. No real-time discussion during review
   6. Configuration changes not documented
   7. Difficult to track review history for learnings
   8. Inconsistent coding standards across teams
   ```

2. Watch for **nudges** that appear as you type (new feature!)
3. When validation passes, click **Continue**

### Step 4: Add Gain Points (3 minutes)

1. Add 8+ specific gain points (expected outcomes):

   **Example gain points:**
   ```
   1. Reviews completed within 4 hours
   2. Junior developers unblocked within same day
   3. Real-time feedback with context
   4. Senior developers focus time protected
   5. Instant code quality feedback
   6. Configuration changes documented inline
   7. Searchable review history for learning
   8. Consistent standards enforced automatically
   ```

2. Click **Validate Now** and refine as needed
3. When validation passes, click **Continue**

### Step 5: Review & Export (2 minutes)

1. **Review Step** shows your complete canvas
2. **Export Options** (new features!):
   - **Download Word** — Professional DOCX format
   - **Generate PDF** — Print-ready format
   - **Export CSV** — Spreadsheet format
   - **Export JSON** — Data format (backup/import)
   - **Share Canvas** — Generate secure link
3. Choose your format and download/share

---

## 📋 Usage Examples

### Example 1: SaaS Product Manager

**Job:** Increase user retention from 40% to 60%

**Pain Points:**
- Users don't discover advanced features
- Onboarding takes 30 minutes; most abandon
- No in-app guidance when users get stuck
- Churn spike after first month
- Support team overloaded with "how-to" tickets

**Gain Points:**
- Users discover 3+ advanced features in first week
- Onboarding takes <5 minutes
- Contextual help reduces support tickets by 50%
- Churn rate <10% after month 1
- Support team focuses on complex issues

→ **Export as PDF** to share with stakeholders
→ **Share link** with product team for feedback
→ **Validate** catches missing pain point (missing technical pain)

### Example 2: Engineering Manager

**Job:** Improve team velocity from 45 to 65 story points per sprint

**Pain Points:**
- Unclear acceptance criteria block developers
- Build times exceed 20 minutes
- Insufficient test coverage (35%)
- Knowledge silos slow onboarding
- Code reviews take 4+ days

**Gain Points:**
- Clear acceptance criteria before sprint start
- Build times <5 minutes
- Test coverage >80%
- Cross-trained team members
- Code reviews <24 hours

→ **Export as JSON** to version control this canvas
→ Use **AI nudges** to strengthen vague pain points
→ **Share link** with executive team for support request

### Example 3: Consultant

Build templates for your clients:

1. Create a template canvas (e.g., "SaaS Product-Market Fit")
2. **Export as JSON** → save as template
3. Clients **import JSON** to start with your template
4. They customize and validate
5. You **import their canvas** to review and coach

---

## 🔐 Security Features

- **XSS Protection** — All user input sanitized via HTML escaping
- **Rate Limiting** — Prevents API abuse (10 requests/min for AI, 60 for validation)
- **Secure Passwords** — Min 8 chars, uppercase, lowercase, digit, special char
- **Session Management** — Max 10 concurrent sessions per user; old sessions evicted
- **Share Link Security** — Password protection optional, timing-safe token resolution
- **Constant-time Token Verification** — Prevents timing oracle attacks
- **HTTPS Ready** — Security headers (HSTS, CSP, X-Frame-Options) configured
- **Request Size Limits** — Max 10MB requests to prevent DoS

---

## 📡 API Endpoints

### Validation
- `POST /api/validate/job-description` — Validate job clarity and specificity
- `POST /api/validate/pain-points` — Validate pain points for independence
- `POST /api/validate/gain-points` — Validate gain points for specificity
- `POST /api/validate/canvas` — Validate complete canvas + proactive nudges
- `POST /api/validate/relevance` — Check item relevance to job

### AI Coaching
- `POST /api/suggestions` — Get AI suggestions for job/pains/gains
- `POST /api/suggestions/job-statement` — Get clickable job alternatives
- `POST /api/improve-item` — Improve single pain/gain item with AI
- `POST /api/merge-items` — Merge similar items intelligently
- `GET /api/coaching-tip/{step}` — Get contextual tip for step

### Export
- `POST /api/generate-document` — Generate Word (.docx)
- `POST /api/generate-pdf` — Generate PDF
- `POST /api/generate-csv` — Generate CSV
- `POST /api/canvases/export/json` — Export canvas as JSON
- `POST /api/canvases/import/json` — Import canvas from JSON

### Sharing
- `POST /api/canvases/{id}/share` — Create shareable link
- `DELETE /api/canvases/{id}/share/{link_id}` — Revoke share link
- `GET /api/shared/{token}` — Access shared canvas (public)

### Authentication
- `POST /api/auth/register` — Register new user
- `POST /api/auth/login` — Log in (returns auth token)
- `POST /api/auth/logout` — Log out
- `POST /api/auth/change-password` — Change password

### Admin
- `GET /api/admin/users` — List all users
- `PATCH /api/admin/users/{id}` — Approve/block users
- `POST /api/admin/reset-password` — Admin password reset

---

## 🛠️ Project Structure

```
value-proposition-canvas/
├── app/
│   ├── main.py                    # FastAPI backend + endpoints
│   ├── models.py                  # SQLAlchemy models (Canvas, User, ShareLink, etc.)
│   ├── schemas.py                 # Pydantic request/response models
│   ├── validation.py              # Quality validator + nudge computation
│   ├── coaching.py                # AI coaching engine (OpenAI)
│   ├── document_generator.py      # Word document generation
│   ├── pdf_generator.py           # PDF generation (NEW)
│   ├── sanitization.py            # XSS/injection protection
│   ├── security.py                # Rate limiting, security headers
│   ├── auth.py                    # JWT auth, password hashing
│   ├── database.py                # SQLAlchemy setup
│   └── routes/
│       ├── auth_routes.py         # User registration/login
│       ├── canvas_routes.py       # Canvas CRUD + JSON import/export
│       ├── share_routes.py        # Shareable links (NEW)
│       └── admin_routes.py        # Admin user management
├── ui/
│   ├── streamlit_app.py           # Main Streamlit UI
│   ├── auth_ui.py                 # Login/register UI
│   ├── canvas_api.py              # API client for canvas operations
│   ├── admin_ui.py                # Admin dashboard
│   └── assets/
│       ├── style.css              # Streamlit custom CSS
│       └── admin.css              # Admin dashboard styles
├── tests/
│   ├── test_*.py                  # Unit tests (194 tests)
│   └── e2e/
│       ├── conftest.py            # E2E test fixtures
│       └── test_*_e2e.py          # Playwright E2E tests (25 tests)
├── alembic/
│   └── versions/                  # Database migrations
├── pyproject.toml                 # Dependencies
├── .env.example                   # Environment template
└── README.md                       # This file
```

---

## 🧪 Testing

```bash
# Run all unit tests
pytest tests/ -v

# Run E2E tests (requires Playwright + Chromium)
pytest tests/e2e/ -v

# Run specific test
pytest tests/test_validation.py::test_nudge_dimension_imbalance -v

# Generate coverage report
pytest tests/ --cov=app --cov-report=html
```

**Test Coverage:**
- **194 unit tests** covering validation, coaching, export, sharing, auth
- **25 E2E tests** using Playwright to test full workflows

---

## ⚙️ Configuration

### Environment Variables

```bash
# Backend
API_SECRET_KEY=your-secret-key          # Optional API key for internal auth
PYTHON_ENV=production                   # Set to "production" in prod
DATABASE_URL=postgresql://user:pass@... # Default: SQLite in-memory
ALLOWED_ORIGINS=http://localhost:8501   # CORS allowed origins
OPENAI_API_KEY=sk-...                   # Optional for AI suggestions

# Rate Limiting
RATE_LIMIT_AI=10/minute                 # AI endpoint limit
RATE_LIMIT_VALIDATION=60/minute         # Validation limit
RATE_LIMIT_AUTH=5/minute                # Auth endpoint limit

# Frontend
API_BASE_URL=http://localhost:8000      # Backend URL
API_SECRET_KEY=your-secret-key          # Must match backend
STREAMLIT_SERVER_PORT=8501              # Port for UI
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Backend won't start** | Check Python 3.11+, run `uv sync`, verify port 8000 free |
| **Frontend can't reach API** | Verify backend running, check `API_BASE_URL` in `.env` |
| **Port 8501 busy** | `streamlit run ui/streamlit_app.py --server.port 8502` |
| **AI suggestions not working** | Add `OPENAI_API_KEY` to `.env`, validate key is valid |
| **Database locked (SQLite)** | Ensure only one backend instance running |
| **Share link returns 404** | Verify link not expired, check password if protected |

---

## 📚 Further Reading

- [API Documentation](./API.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Architecture & Design](./ARCHITECTURE.md)
- [Contributing Guidelines](./CONTRIBUTING.md)

---

## 📄 License

MIT License — See [LICENSE](./LICENSE) for details.

---

## 🙋 Support

- **Issues & Features**: [GitHub Issues](https://github.com/yourusername/value-proposition-canvas/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/value-proposition-canvas/discussions)
- **Email**: support@example.com

---

**Happy canvas building! 🎨**
