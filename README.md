# AI TAM/SAM/SOM Market Analysis Platform

[![Backend Tests](https://img.shields.io/badge/Backend%20Pytest-221%20Passed-brightgreen)](file:///d:/Coirei-projects/tam-sam-som-analyzer/tests)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Vitest-18%20Passed-brightgreen)](file:///d:/Coirei-projects/tam-sam-som-analyzer/frontend)
[![Vite Build](https://img.shields.io/badge/Production%20Build-Passing-brightgreen)](file:///d:/Coirei-projects/tam-sam-som-analyzer/frontend)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3+-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-3178c6.svg)](https://www.typescriptlang.org/)

---

## 1. Overview & Purpose

The **AI TAM/SAM/SOM Market Analysis Platform** is an enterprise-grade market sizing and intelligence system. It takes any raw business idea, extracts its key economic parameters using local open-source LLMs (via Ollama), builds multi-intent search queries, discovers and fetches empirical evidence safely, extracts and validates market metrics, and computes **deterministic Top-Down and Bottom-Up market sizing estimates**:

- **TAM (Total Addressable Market)**: Total global or national potential revenue opportunity.
- **SAM (Serviceable Addressable Market)**: Segment of TAM targeted by the business model, geography, and channels.
- **SOM (Serviceable Obtainable Market)**: Realistic capture potential in the initial 1–3 years based on validated capacity and conversion constraints.

### Core Non-Negotiable Evidentiary Invariants
1. **Zero Numerical Hallucination**: LLMs are never permitted to generate market sizing numbers, customer counts, pricing, or market shares directly.
2. **Evidence Gate**: Calculations require strictly `VALIDATED` or `VERIFIED` empirical evidence.
3. **SOM Safety Constraint**: System never applies arbitrary 1%, 3%, or 5% capture guesses. In the absence of validated obtainable capacity or customer conversion evidence, SOM safely outputs **"Insufficient Evidence"**.
4. **Mock Isolation**: Local mock discovery runs purely in-memory with zero external HTTP or DNS requests, accompanied by a transparent badge.
5. **No Provider Drift**: Live discovery failures never silently fall back to mock data.
6. **SSRF Guard**: Fetch service blocks internal loopback (`127.0.0.1`), private RFC1918 subnets, cloud metadata endpoints (`169.254.169.254`), and non-standard ports.

---

## 2. Architecture & Pipeline Lifecycle

```text
User Business Idea (Text)
          ↓
[Stage 1: Business Analysis]
  • Ollama LLM / Rule-based extractor
  • Extracts Industry, Product, Target Customer, Geography, Business Model
          ↓
[Stage 2: Research Query Generation]
  • Population / Demographics Query
  • Macro Market Size / Revenue Query
  • Per-unit Pricing / ARPU Query
          ↓
[Stage 3: Evidence Discovery]
  • Mock Provider (Offline Local Fixtures) OR Live Search (SearXNG / Serper)
  • Domain Authority Scoring & Pre-fetch Relevance Filtering
          ↓
[Stage 4: Safe Source Fetching]
  • SSRF-guarded HTTP Fetcher
  • Payload limits (5MB max), Content-Type checks, Timeout controls (15s)
          ↓
[Stage 5: Evidence Extraction]
  • Semantic Parsing of Numerical Candidates (Values, Units, Years, Context)
  • Metric Types: population, market_size, pricing, growth_rate
          ↓
[Stage 6: Evidence Validation]
  • Schema bounds, unit verification, context checking, negative/zero rejection
          ↓
[Stage 7: Triangulation & Deduplication]
  • Fuzzy match deduplication
  • Multi-domain corroboration (2+ distinct domain hostnames → VERIFIED)
  • Conflict detection & discrepancy recording
          ↓
[Stage 8: Deterministic Market Calculation]
  • Top-Down Engine (Macro Industry × Segment Filters)
  • Bottom-Up Engine (Target Population × Annual ARPU)
  • Divergence Severity (NONE, ACCEPTABLE, WARNING, SEVERE_DIVERGENCE)
          ↓
[Stage 9: Final Report & Provenance Assembly]
  • React Dashboard + SSE Real-time Streaming
```

---

## 3. Evidence Lifecycle

```text
DISCOVERED ──► FETCHED ──► EXTRACTED ──► VALIDATED ──► VERIFIED
```

- **DISCOVERED**: Candidate URLs discovered via search or mock provider. Cannot enter calculation engine directly.
- **FETCHED**: Document retrieved, sanitized, and stored with fetch status and timestamp.
- **EXTRACTED**: Raw metric values, units, context snippets, and metadata parsed from text.
- **VALIDATED**: Passed range, schema, currency, and unit consistency rules.
- **VERIFIED**: Corroborated by 2 or more independent domain hostnames with no active conflicting values.

---

## 4. Project Structure

```text
tam-sam-som-analyzer/
├── app/
│   ├── api/                     # FastAPI route controllers
│   │   ├── business.py          # Business extraction API
│   │   ├── calculation.py       # Deterministic TAM/SAM/SOM API
│   │   ├── evidence.py          # Discovery, fetch & validation API
│   │   ├── orchestration.py     # Orchestrator API
│   ├── discovery/               # Discovery providers (mock & live)
│   ├── fetching/                # SSRF-guarded HTTP fetcher & HTML sanitizer
│   ├── orchestration/           # 9-stage pipeline coordinator & SSE events
│   ├── schemas/                 # Pydantic models & validation schemas
│   ├── services/                # Authoritative calculation, LLM, extraction & validation services
│   ├── storage/                 # SQLite persistence & audit repository
│   ├── taxonomy/                # Canonical 25 B2B SaaS taxonomy & 120+ subcategories
│   ├── config.py                # Environment-based application settings
│   └── main.py                  # FastAPI application entrypoint & middleware
├── data/                        # SQLite storage directory
├── frontend/
│   ├── src/
│   │   ├── components/          # React components (Market Funnel, Cards, Sources, etc.)
│   │   ├── services/            # API client and SSE stream consumer
│   │   ├── types/               # TypeScript interfaces matching backend models
│   │   └── App.tsx              # Main application dashboard
│   ├── package.json
│   └── vite.config.ts
├── tests/                       # Pytest test suite (221 test cases)
├── Dockerfile                   # Multi-stage production container build
├── docker-compose.yml           # Compose file for app + Ollama
├── requirements.txt             # Python backend dependencies
└── README.md                    # Project documentation
```

---

## 5. Getting Started & Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- (Optional) [Ollama](https://ollama.ai/) with `qwen3:8b` for local AI analysis

### 1. Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env

# Run FastAPI backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend API will be running at `http://localhost:8000`. Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```

Frontend application will be accessible at `http://localhost:5173`.

---

## 6. Running Tests

### Backend Test Suite
```bash
pytest -v
```
*Current result*: **221 passed, 0 failed, 0 errors**

### Frontend Test Suite
```bash
cd frontend
npm test -- --run
```
*Current result*: **18 passed, 0 failed**

### Production Build Verification
```bash
cd frontend
npm run build
```
*Output*: TypeScript checking and Vite asset bundling succeed with 0 errors.

---

## 7. Configuration & Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `AI TAM SAM SOM Market Analyzer` | Application title |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `DEBUG` | `true` | Enable/disable debug exceptions |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `HOST` | `0.0.0.0` | API server bind address |
| `PORT` | `8000` | API server bind port |
| `CORS_ALLOW_ORIGINS` | `*` | Allowed CORS origins (comma-separated or `*`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama LLM endpoint |
| `OLLAMA_MODEL` | `qwen3:8b` | Ollama model identifier |
| `SEARCH_PROVIDER` | `mock` | Discovery provider (`mock`, `live`, `searxng`) |
| `SEARCH_API_KEY` | `""` | Optional API key for search providers |
| `DATABASE_PATH` | `data/market_analyses.db` | SQLite persistence path |

---

## 8. Docker Deployment

To launch the full production application alongside Ollama via Docker Compose:

```bash
docker-compose up --build -d
```

Access the health check endpoint at `http://localhost:8000/health`.

---

## 9. Security Model

- **SSRF Protection**: `HttpSourceFetcher` verifies every destination IP against standard loopback (`127.0.0.0/8`, `::1`), private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and AWS/GCP metadata (`169.254.169.254`).
- **Input Sanitization**: Business idea inputs and search queries are stripped of injection vectors and Swagger placeholders.
- **Safe HTML Parsing**: Web documents are parsed using standard BeautifulSoup text extraction with scripts, styles, and executable attributes stripped.
- **Rate & Size Limits**: Fetches are capped at 5MB and enforced with a 15-second socket timeout.

---

## 10. License

MIT License. Designed and hardened for enterprise TAM/SAM/SOM market intelligence.
