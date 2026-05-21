---
name: frontend-to-fullstack
description: "Transform a pure frontend project into a production-ready full-stack product. This skill orchestrates the end-to-end pipeline: C4 architecture analysis → project restructuring → backend API implementation → E2E testing. Use when the user wants to turn a frontend-only codebase (React, Vue, or plain HTML/JS) into a complete product with backend, database, APIs, tests, and documentation."
---

# Frontend-to-Fullstack Skill

## Purpose

Take a pure frontend project and transform it into a production-grade full-stack product through a standardized pipeline. This skill is the orchestrator — it delegates actual implementation to specialized skills at each phase.

## When To Use

Use this skill when:
- The user says "把这个前端项目做成完整项目" (turn this frontend project into a complete project)
- A pure frontend codebase needs backend APIs, database, and tests
- The user wants to "productize" a prototype or demo
- A frontend-only repo needs to become production-ready

## ⚡ The Standard Pipeline

```
Phase 0: Pre-Flight  →  Phase 1: C4 Architecture Analysis  →  Phase 2: Project Restructuring  →  Phase 3: Backend APIs  →  Phase 4: Integration  →  Phase 5: E2E Testing
```

Each phase has a clear input, output, and validation checkpoint. Phases must run in order — each depends on the prior phase's output.

---

## Phase 0: Pre-Flight Analysis

**Goal**: Understand the starting point — what kind of project are we transforming?

### Step 1: Detect Project Type

Check for these patterns and classify the project:

| Pattern | Classification | Action |
|---------|---------------|--------|
| `frontend/` only, no API calls | Pure frontend | Standard pipeline |
| `frontend/` only, calls `fetch` to remote URLs | Frontend + external API | Keep external API, add own backend for new features |
| Lightweight `server.js` / `api/` with Express/Next.js routes | Frontend + lightweight Node.js backend | **Abandon the Node.js backend**, migrate all capabilities to new Clojure backend |
| Full backend already exists | Full-stack project | This skill may not apply — project is already full-stack |

### Step 2: Handle Lightweight Node.js Backends (CRITICAL)

**Rule: If the project has a lightweight Node.js backend (Express, Next.js API routes, Fastify, Koa, etc.), it MUST be abandoned.** Do not try to extend or keep it. All its capabilities must be migrated to the new Clojure backend.

Why:
- Lightweight Node.js backends lack database migrations, proper layering, and type safety
- Maintaining two backends creates split-brain architecture
- The Clojure backend will provide a clean, testable, production-grade alternative

What to extract from the Node.js backend before discarding:
1. All API route handlers → map to Clojure backend API endpoints in Phase 3
2. All database queries or data access → convert to SQL migrations + HugSQL queries
3. All business logic → migrate to Clojure service layer
4. All middleware (auth, CORS, logging) → implement in Clojure Integrant + Ring middleware
5. Environment variables and configuration → map to Aero config profiles

**After Phase 0, the Node.js backend is removed from the repo.**

### Step 3: Extract Embedded Data from Frontend Code

Pure frontend projects often have data hardcoded in JavaScript/TypeScript files or stored in browser localStorage. Extract ALL of it:

**Data sources to scan:**
- `.ts` / `.tsx` / `.js` / `.jsx` files with hardcoded arrays, objects, or mock data
- `constants/` or `data/` directories with JSON/JS data files
- `mockService.ts` or similar mock API files
- `localStorage.setItem()` or IndexedDB usage
- `sessionStorage` usage
- Inline mock data in React components (e.g., `const products = [...]`)

**For each data source found:**
1. Document the data schema (field names, types, relationships)
2. Record the data as JSON for seed data creation
3. Note where the data was used (which page, which component)
4. Plan the corresponding SQL table + API endpoint

**Special: Static assets (images, files)**
If the frontend references local image files or hardcoded URLs:
1. Collect all referenced static assets
2. Plan for file upload/download endpoints in the backend
3. Files will be stored in `uploads/` directory next to the JAR, not in the database

### Output
- Project type classification
- List of Node.js backend capabilities to migrate (if applicable)
- Complete inventory of embedded frontend data with schemas
- List of static assets to handle

### Validation
- [ ] Project type classified
- [ ] Node.js backend analyzed and migration plan ready (if applicable)
- [ ] All hardcoded data identified with schemas
- [ ] Static assets cataloged

---

## Phase 1: C4 Architecture Analysis

**Goal**: Understand what the frontend does, identify business domains and data entities, and produce architecture documentation.

**How**: Use the `c4-architecture-c4-architecture` skill.

### Input
- The existing frontend codebase (any framework: React, Vue, plain HTML/JS)

### Steps
1. **Load the skill**: Read and apply `c4-architecture-c4-architecture` SKILL.md
2. **Analyze frontend pages**: Identify all pages/views, their user flows, and the data they display
3. **Identify business domains**: Group pages into business domains (e.g., catalog, orders, customers)
4. **Extract data entities**: From the frontend code, extract all data types, forms, and API calls (even if mocked)
5. **Generate C4 diagrams**: Produce Context, Container, and Component level diagrams
6. **Define API surface**: From frontend data needs, derive the required REST API endpoints

### Output
- `docs/C4-ARCHITECTURE.md` — full C4 documentation
- A clear picture of: business domains, data entities, API endpoints needed, database tables needed

### Validation
- [ ] C4 diagrams exist and cover all frontend pages
- [ ] Data entities are identified and named
- [ ] API endpoints are listed and grouped by domain
- [ ] Frontend/backend boundary is clearly defined

---

## Phase 2: Project Restructuring

**Goal**: Reorganize the repo, set up the backend skeleton, create project documentation, and add file upload infrastructure.

### Steps

1. **Remove Node.js backend** (if any): Delete `server.js`, `api/`, Express/Next.js route files, and `package.json` entries for backend deps. Keep only frontend `package.json`.

2. **Split directories**: Ensure frontend code lives in `frontend/`, create empty `backend/`

3. **Set up backend skeleton**: Create Clojure backend with `deps.edn`, Integrant config, basic handler, static resource serving, AND file upload infrastructure. The Ring handler MUST serve both API routes and static assets from `resources/public/` so the frontend is accessible after the backend JAR starts.

4. **Create `scripts/` directory**: Add local startup and packaging scripts to the project root.
   - `scripts/start-dev.sh` (or `.bat`/`.ps1` equivalents) — starts both backend (`cd backend && clojure -M:run`) and frontend (`cd frontend && npm run dev`) concurrently, with clear console output
   - `scripts/build.sh` (or `.bat`/`.ps1` equivalents) — **build order matters**:
     1. Build the frontend for production (`cd frontend && npm run build`)
     2. Copy the frontend build output (e.g., `frontend/dist/` or `frontend/build/`) into `backend/resources/public/`
     3. Build the Clojure backend UberJAR (`cd backend && clojure -T:build uberjar`)
   - Both scripts should be executable (`chmod +x`) and documented in README.md

5. **Create AGENTS.md**: Write project-level AGENTS.md with conventions, commands, and rules

6. **Create README.md**: Brief project overview with setup instructions

### Backend Skeleton Pattern (with File Upload Support)

The backend skeleton should include:
```
backend/
  deps.edn
  resources/
    system.edn          # Integrant system config
    config.edn          # Aero config with profiles
    public/             # Frontend build output copied here before JAR packaging
    migrations/         # SQL migration files (Phase 3)
    sql/                # HugSQL query files (Phase 3)
  src/<project>/backend/
    core.clj            # System init + main
    handler.clj         # Ring handler (with multipart support + static resource fallback)
    routes.clj          # Reitit route tree
    upload.clj          # File upload/download handler
  test/<project>/backend/
    core_test.clj
    upload_test.clj     # File upload tests
uploads/                # Created at runtime next to JAR, gitignored
```

### File Upload/Download Infrastructure (REQUIRED)

**Every project MUST include file upload/download endpoints.** This is required because:
- Frontend pages often reference local images or hardcoded URLs
- During Phase 1 data extraction, static assets were identified
- These assets need a proper serving mechanism, not hardcoded paths

**Implementation requirements:**
- `POST /api/upload` — accept multipart file upload, save to `uploads/` directory
- `GET /uploads/:filename` — serve uploaded files as static resources
- `GET /` (and all non-API paths) — serve the SPA / frontend from `resources/public/` (packaged into the JAR). The Ring handler must fall back to `index.html` for client-side routing (SPA catch-all)
- `uploads/` directory is at the same level as the JAR (not inside it)
- `uploads/` must be in `.gitignore`
- `backend/resources/public/` must be in `.gitignore` (it is a build artifact copied from the frontend build output)
- Image files from the original frontend should be seeded into `uploads/` at startup
- Backend serves `uploads/` as a Ring static resource route AND serves `resources/public/` as classpath/static resources

### Output
- Clean `frontend/` and `backend/` directory structure (Node.js backend removed if present)
- `scripts/` with local startup (`start-dev`) and packaging (`build`) scripts
- `backend/resources/public/` serves as the destination for frontend build artifacts
- `AGENTS.md` with project conventions
- `README.md` with setup and run instructions
- Backend starts and serves `/api/health`
- File upload/download endpoints operational
- Backend serves the frontend SPA from `resources/public/` when running as a JAR

### Validation
- [ ] `cd backend && clojure -M:run` starts successfully
- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] `POST /api/upload` accepts and stores files
- [ ] `GET /uploads/:filename` serves uploaded files
- [ ] `cd frontend && npm run dev` starts successfully
- [ ] `scripts/start-dev.sh` starts both frontend and backend concurrently
- [ ] `scripts/build.sh` builds frontend, copies output to `backend/resources/public/`, and produces the backend UberJAR
- [ ] Running the produced UberJAR (`java -jar backend/target/...jar`) serves both API endpoints and the frontend SPA (verify by opening `http://localhost:3000/` in browser)
- [ ] AGENTS.md covers frontend and backend conventions

---

## Phase 3: Backend API Implementation

**Goal**: Implement all backend APIs identified in Phase 1, organized by business domain.

**How**: Use the `clojure-fullstack-development` skill.

### Approach: Epic-Driven with Child Beads

Create one epic bead for the API implementation plan, then child beads per domain:

```
Epic: Backend API implementation plan
├── Child 1: Database foundation + seed data
├── Child 2: Domain A APIs (e.g., Catalog)
├── Child 3: Domain B APIs (e.g., Customers)
├── Child 4: Domain C APIs (e.g., Orders)
└── Child 5: Integration docs + browser validation
```

Each child bead is slung to a polecat for autonomous implementation.

### Data Migration: JS/TS → SQL Seed Data

**CRITICAL: All hardcoded data found in Phase 0/1 MUST be migrated to database migrations.**

For each data source identified:

1. **Design table schema** from the JS/TS data structure
2. **Create migration file**: `resources/migrations/001_init.up.sql` with CREATE TABLE statements
3. **Create seed migration**: `resources/migrations/002_seed.up.sql` with INSERT statements for all extracted data
4. **Remove hardcoded data from frontend**: Replace with API calls to the new backend
5. **Update frontend mock services**: If `mockService.ts` exists, replace mock data with actual `fetch` calls

Example data transformation:
```javascript
// Before (frontend constants/designData.ts)
export const products = [
  { id: 'p1', name: 'Havana Fit Suit', category: 'suit', price: 8999, image: '/images/havana.jpg' }
];
```
↓ becomes ↓
```sql
-- 002_seed.up.sql
INSERT INTO products (id, name, category, price, image_url)
VALUES ('p1', 'Havana Fit Suit', 'suit', 8999, '/uploads/havana.jpg');
```

And the image file `images/havana.jpg` is moved to `uploads/havana.jpg` at backend startup.

### Per-Domain Implementation Pattern

For each business domain identified in Phase 1:

1. **Database**: Migration files + SQL query files + seed data (from extracted JS data)
2. **Repository layer**: HugSQL queries or direct DB access
3. **Service layer**: Business logic, validation, data transformation
4. **Controller/Route layer**: HTTP handlers, request parsing, response formatting
5. **Unit tests**: Every service function MUST have unit tests (see below)

### Technology Stack

- **Language**: Clojure (JVM)
- **Framework**: Kit-style with Integrant + Aero + Reitit + Ring
- **Database**: SQLite (default for new projects), PostgreSQL (if specified)
- **Migrations**: Migratus
- **Queries**: HugSQL or next.jdbc
- **Testing**: `clojure -M:test`

### Output
- All backend API endpoints operational
- Database with schema, migrations, and seed data
- Per-domain test coverage
- All child beads closed

### Unit Test Mandate

**Every backend API endpoint MUST have corresponding unit tests.** This is non-negotiable.

Minimum test coverage per domain:
- **Repository tests**: Test each query function with test database
- **Service tests**: Test business logic, validation, edge cases, error paths
- **Route tests**: Test HTTP status codes, response bodies, error responses
- **Upload tests**: Test file upload and download endpoints

Test structure:
```
backend/test/<project>/backend/
  routes_test.clj           # API endpoint integration tests
  service/<domain>_test.clj # Business logic unit tests
  upload_test.clj           # File upload tests
```

Run with: `cd backend && clojure -M:test`

### Validation
- [ ] `clojure -M:test` passes (ALL tests green)
- [ ] All API endpoints return correct responses
- [ ] Seed data from original JS is loadable and queryable
- [ ] Frontend dev server can connect to backend APIs
- [ ] All hardcoded data removed from frontend, replaced with API calls

---

## Phase 4: Integration & Validation

**Goal**: Verify the full stack works end-to-end, update documentation.

### Steps
1. **Start backend + frontend**: Run both services locally
2. **Browser validation**: Click through all frontend pages, verify API data renders
3. **Update API docs**: If `docs/apis/` exists, update OpenAPI/contract docs
4. **Update C4 docs**: If routes or architecture changed, update C4 diagrams
5. **Quality gates**: `npm run build` + `clojure -M:test` must pass

### Output
- Verified full-stack application running locally
- Updated documentation
- All quality gates passing

### Validation
- [ ] All frontend pages load without errors in browser
- [ ] API data renders correctly on all pages
- [ ] `npm run build` succeeds
- [ ] `clojure -M:test` passes

---

## Phase 5: E2E Testing

**Goal**: Add comprehensive Playwright end-to-end tests covering all features.

### Steps
1. **Create `test/` directory** in project root
2. **Set up Playwright**: `package.json`, `playwright.config.ts`, `README.md`
3. **Write spec files**: One spec per frontend page + one API spec
4. **Document in AGENTS.md**: Add test run instructions
5. **Install and verify**: `npm install && npx playwright install && npm test`

### Test Structure
```
test/
  playwright.config.ts
  package.json
  README.md
  specs/
    home.spec.ts
    feature-a.spec.ts
    feature-b.spec.ts
    ...
    api.spec.ts
```

### Spec Coverage Per Page
Each page spec should cover:
- Page renders without errors
- Key UI elements are visible
- User interactions work (clicks, inputs, navigation)
- Error and edge cases where applicable

### API Spec Coverage
The API spec should cover:
- Health check endpoint
- All GET endpoints (list + detail)
- All POST/PUT/PATCH endpoints
- Validation error responses (4xx)
- Catalog/read-only endpoints

### Output
- `test/` directory with full Playwright setup
- One spec file per frontend page + one API spec
- Updated AGENTS.md with test run instructions
- All dependencies installed, browsers downloaded

### Validation
- [ ] `cd test && npm test` runs successfully
- [ ] All specs pass (no timeouts, no flaky tests)
- [ ] Test coverage covers all pages identified in Phase 1
- [ ] AGENTS.md contains test run instructions

---

## Orchestration Rules

### Skill Delegation

This skill orchestrates — it does NOT implement:

| Phase | Delegates To |
|-------|-------------|
| Pre-Flight Analysis | Direct implementation (project scanning, no architecture work) |
| Architecture Analysis | `c4-architecture-c4-architecture` |
| Backend Implementation | `clojure-fullstack-development` |
| Project Restructuring | Direct implementation (structural, not coding) |
| E2E Testing | Direct implementation (Playwright setup) |

When delegating, load the referenced skill file fully and follow its instructions.

### Beads Workflow

Use beads (issue tracker) for all work tracking:
- Create an EPIC bead for the overall transformation
- Create child beads per phase/domain
- Sling child beads to polecats for implementation
- Close beads as phases complete

### AGENTS.md

Every phase that touches project structure or conventions MUST update AGENTS.md. The AGENTS.md is the source of truth for future developers (human and AI).

### Validation At Every Phase

Never skip validation. If a phase's validation fails, stop and fix before proceeding. Broken assumptions compound.

## Quick Reference

```bash
# Phase 1: Architecture
# Use c4-architecture-c4-architecture skill

# Phase 2: Restructuring
mkdir backend frontend
# ... set up skeleton, AGENTS.md, README.md

# Phase 3: Backend APIs
bd create --title="Backend API implementation plan" --type=epic
bd create --title="Database foundation" --type=task
# ... create child beads, sling to polecats

# Phase 4: Integration
cd backend && clojure -M:run
cd frontend && npm run dev
# ... browser validation

# Phase 5: E2E Tests
mkdir test && cd test
npm init -y && npm install @playwright/test
npx playwright install
# ... write spec files
```

## Anti-Patterns

- ❌ Skipping C4 analysis — leads to missed domains and rework
- ❌ Implementing backend without understanding frontend data needs
- ❌ Keeping the lightweight Node.js backend — abandon it, migrate everything to Clojure
- ❌ Leaving hardcoded data in JS/TS files — all data MUST go into SQL migrations
- ❌ Skipping file upload endpoints — static assets need proper serving
- ❌ Writing backend APIs without unit tests — every endpoint needs test coverage
- ❌ Writing monolithic backend — always split by business domain
- ❌ Skipping E2E tests — they are the safety net for the whole transformation
- ❌ Not updating AGENTS.md — leaves the project without conventions
- ❌ Doing everything yourself — delegate to specialized skills and polecats
