
# MedGuard — Developer & User Guide

This document explains how to use the MedGuard codebase, how to run it locally, and how to modify or extend it for your needs.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Running Locally (Without Docker)](#2-running-locally-without-docker)
3. [Running with Docker](#3-running-with-docker)
4. [AI Backend Configuration](#4-ai-backend-configuration)
5. [Using the Application](#5-using-the-application)
6. [API Reference & Examples](#6-api-reference--examples)
7. [How the Allergy Engine Works](#7-how-the-allergy-engine-works)
8. [Modifying the Codebase](#8-modifying-the-codebase)
9. [Adding New Drugs to the Database](#9-adding-new-drugs-to-the-database)
10. [Adding New Allergy Check Rules](#10-adding-new-allergy-check-rules)
11. [Connecting a Real EHR System](#11-connecting-a-real-ehr-system)
12. [Swapping or Adding AI Models](#12-swapping-or-adding-ai-models)
13. [Adding New API Endpoints](#13-adding-new-api-endpoints)
14. [Modifying the Frontend](#14-modifying-the-frontend)
15. [Database Schema Changes](#15-database-schema-changes)
16. [Environment Variables Reference](#16-environment-variables-reference)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. Prerequisites

| Tool | Version | Required For |
|------|---------|-------------|
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend |
| Docker + Docker Compose | Latest | Database, cache, Ollama (or full stack) |
| Git | Any | Version control |

**Optional (for HuggingFace local models):**
- NVIDIA GPU with CUDA (for fast inference)
- 16+ GB RAM (for loading 4B parameter models)

---

## 2. Running Locally (Without Docker)

This is the recommended approach for development. You run PostgreSQL + Valkey in Docker, but the backend and frontend run directly on your machine for fast iteration.

### Step 1: Start Database & Cache

```bash
# From the project root
docker compose up postgres valkey -d

# Verify they're running
docker compose ps
```

### Step 2: Set Up the Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Create your local .env file
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
```

Edit `.env` to point to localhost:

```env
DATABASE_URL=postgresql+asyncpg://medguard:medguard_secret@localhost:5432/medguard
DATABASE_URL_SYNC=postgresql://medguard:medguard_secret@localhost:5432/medguard
REDIS_URL=redis://localhost:6379/0
AI_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=medgemma:4b
APP_ENV=development
APP_DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Step 3: Start the Backend

```bash
uvicorn app.main:app --reload --port 8000
```

The backend will:
- Auto-create all database tables on first startup
- Enable the `pg_trgm` PostgreSQL extension for fuzzy search
- Be available at http://localhost:8000
- Swagger docs at http://localhost:8000/docs

### Step 4: Seed the Database

In a **new terminal** (same venv activated):

```bash
cd backend
venv\Scripts\activate
python -m scripts.seed_data
```

This populates:
- 12 common drugs with ingredients
- 3 cross-reactivity groups (Beta-Lactams, NSAIDs, Sulfonamides)
- 2 demo patients (John Doe with Penicillin allergy, Jane Smith with Aspirin allergy)

### Step 5: Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Step 6: (Optional) Start Ollama for AI Features

```bash
# Install Ollama from https://ollama.com
ollama serve                    # Starts on port 11434
ollama pull medgemma:4b         # Download MedGemma (~2.5 GB)
```

> **Without Ollama:** The app still works. Layers 1-4 of the allergy engine (deterministic rules) run without AI. Only Layer 5 (AI cross-reactivity) and photo OCR require a model.

---

## 3. Running with Docker

For a one-command full stack:

```bash
# Build and start everything
docker compose up --build -d

# Seed the database
docker compose --profile seed run --rm seed

# Pull the AI model
docker compose exec ollama ollama pull medgemma:4b
```

**Services:**
| Service | URL | Port |
|---------|-----|------|
| Frontend | http://localhost:3000 | 3000 |
| Backend API | http://localhost:8000 | 8000 |
| Swagger Docs | http://localhost:8000/docs | 8000 |
| PostgreSQL | localhost:5432 | 5432 |
| Valkey (Redis) | localhost:6379 | 6379 |
| Ollama | http://localhost:11434 | 11434 |

---

## 4. AI Backend Configuration

MedGuard supports **3 AI backends**. Switch between them by changing one env var: `AI_BACKEND`.

### Option A: Ollama (Default)

Best for: local development with a dedicated model server.

```env
AI_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=medgemma:4b
```

Supported models: `medgemma:4b`, `gemma2:2b`, `llama3.1:8b`, `mistral:7b`, or any Ollama model.

### Option B: HuggingFace Inference API (Free Cloud)

Best for: **zero GPU, zero setup**. Uses HuggingFace's free inference servers.

```env
AI_BACKEND=huggingface_api
HF_MODEL_ID=google/medgemma-4b-it
HF_TOKEN=hf_your_token_here
```

Get a free token at https://huggingface.co/settings/tokens

> **Rate limits:** Free tier has rate limits. For production, consider a paid Inference Endpoint or switch to Ollama/local.

### Option C: HuggingFace Local (Transformers)

Best for: running the model directly in your Python process (needs GPU or lots of RAM).

```env
AI_BACKEND=huggingface_local
HF_MODEL_ID=google/medgemma-4b-it
HF_TOKEN=hf_your_token_here
HF_DEVICE=auto
HF_TORCH_DTYPE=float16
```

Install extra dependencies first:

```bash
pip install transformers torch accelerate sentencepiece
```

**Device options:**
- `auto` — auto-detect GPU/CPU
- `cuda` — NVIDIA GPU
- `mps` — Apple Silicon GPU
- `cpu` — CPU only (slow for large models)

---

## 5. Using the Application

### Manual Drug Entry Flow

1. **Load a patient** — Enter patient ID (e.g., `P-5678`) and click Load
2. **Search drugs** — Type a drug name in the search box (fuzzy matching)
3. **Select drugs** — Click on results to add them to the prescription
4. **Check allergies** — Click "Check for Allergies"
5. **Review results** — GREEN (safe), YELLOW (review), RED (do not prescribe)
6. **Override** (if needed) — Click "Override & Prescribe Anyway" with clinical justification

### Photo Upload Flow

1. Load a patient
2. Switch to "Photo Upload" tab
3. Upload a prescription photo (JPEG, PNG, or WebP)
4. MedGemma extracts drug names via OCR
5. System checks extracted drugs against allergies

### Demo Patients

| Patient ID | Name | Allergies | Conditions |
|-----------|------|-----------|------------|
| `P-5678` | John Doe | Penicillin (severe), Sulfonamide (severe) | G6PD Deficiency |
| `P-1234` | Jane Smith | Aspirin (severe) | None |

### Test Scenarios

| Patient | Drug | Expected Signal | Why |
|---------|------|----------------|-----|
| P-5678 | Amoxicillin | RED | Direct Penicillin match |
| P-5678 | Cephalexin | YELLOW | Beta-Lactam cross-reactivity + elevated IgE |
| P-5678 | Sulfamethoxazole | RED | Sulfonamide allergy + G6PD contraindication |
| P-5678 | Azithromycin | GREEN | Safe Macrolide, no cross-reactivity |
| P-5678 | Cetirizine | GREEN | Antihistamine, no known issues |
| P-1234 | Ibuprofen | YELLOW | NSAID cross-reactivity with Aspirin |
| P-1234 | Omeprazole | GREEN | PPI, no cross-reactivity |

---

## 6. API Reference & Examples

### Check Prescription (Manual Entry)

```bash
curl -X POST http://localhost:8000/api/v1/prescription/check \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "P-5678",
    "drugs": [
      {"name": "Amoxicillin"},
      {"rxcui": "18631"}
    ]
  }'
```

### Check Prescription (Photo)

```bash
curl -X POST http://localhost:8000/api/v1/prescription/check/photo \
  -F "patient_id=P-5678" \
  -F "image=@prescription.jpg"
```

### Search Drugs

```bash
curl "http://localhost:8000/api/v1/drugs/search?q=amox&limit=5"
```

### Get Patient Allergy Profile

```bash
curl "http://localhost:8000/api/v1/patients/P-5678/allergy-profile"
```

### Create a New Patient

```bash
curl -X POST http://localhost:8000/api/v1/patients \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "P-9999",
    "name": "Alice Johnson",
    "age": 30,
    "gender": "Female"
  }'
```

### Add Allergy to Patient

```bash
curl -X POST http://localhost:8000/api/v1/patients/P-9999/allergies \
  -H "Content-Type: application/json" \
  -d '{
    "allergen_name": "Latex",
    "category": "environment",
    "criticality": "high",
    "reaction_manifestations": ["Urticaria", "Anaphylaxis"],
    "reaction_severity": "severe"
  }'
```

### Override a RED Warning

```bash
curl -X POST http://localhost:8000/api/v1/prescription/override \
  -H "Content-Type: application/json" \
  -H "X-Doctor-Id: DR-001" \
  -d '{
    "request_id": "uuid-from-check-response",
    "overridden_warnings": ["W-abc12345"],
    "clinical_justification": "Patient has tolerated this drug before under supervision",
    "digital_signature": "DR-001-signature"
  }'
```

---

## 7. How the Allergy Engine Works

The engine in `backend/app/core/allergy_engine.py` uses a **5-layer approach**, from most reliable to least:

```
Layer 1: DETERMINISTIC DIRECT MATCH
  Ingredient name ↔ known allergen name/chemical family
  → If match: RED (CRITICAL or HIGH severity)

Layer 2: CROSS-REACTIVITY DATABASE
  Check cross_reactivity_groups table
  → If ingredient shares a group with a known allergen: RED or YELLOW
  → Probability: high → RED, moderate → YELLOW, low → YELLOW

Layer 3: LAB-BASED SENSITIVITY
  Check patient's lab results (IgE levels, skin prick tests)
  → If elevated lab marker related to ingredient: YELLOW

Layer 4: CONDITION CONTRAINDICATION
  Check patient conditions (e.g., G6PD deficiency)
  → If ingredient is in contraindicated list: RED

Layer 5: AI CROSS-REACTIVITY (MedGemma)
  Only runs if Layers 1-4 returned GREEN and patient has known allergens
  → Asks AI to assess cross-reactivity risk for active ingredients
  → If AI detects risk: YELLOW (never RED — AI only augments, never overrides)
```

**Key safety principle:** Deterministic rules (Layers 1-4) are primary. AI (Layer 5) only adds YELLOW warnings, never RED. This ensures the system is safe even if the AI model is wrong.

---

## 8. Modifying the Codebase

### Project Layout

```
backend/app/
├── main.py              # App startup, middleware, route registration
├── config.py            # All environment variables / settings
├── api/
│   ├── routes/          # HTTP endpoint handlers
│   │   ├── prescription.py   # Core check + override endpoints
│   │   ├── drugs.py          # Drug search + ingredient lookup
│   │   └── patients.py       # Patient CRUD + allergy profile
│   └── middleware/
│       └── auth.py           # JWT authentication (Keycloak)
├── core/                # Business logic (no HTTP concerns)
│   ├── allergy_engine.py     # The 5-layer matching engine
│   ├── ai_service.py         # AI abstraction (OCR, alternatives, cross-reactivity)
│   ├── ai_backends/          # Pluggable AI providers
│   │   ├── base.py           # Abstract interface
│   │   ├── factory.py        # Backend selection
│   │   ├── ollama_backend.py
│   │   ├── huggingface_local_backend.py
│   │   └── huggingface_api_backend.py
│   ├── drug_service.py       # Drug DB queries + caching
│   ├── patient_service.py    # Patient profile queries + caching
│   └── audit_service.py      # Immutable audit logging
├── models/              # SQLAlchemy ORM (database tables)
│   ├── drug.py               # Drug, Ingredient, DrugIngredient, CrossReactivity
│   ├── patient.py            # Patient, PatientAllergy, LabSensitivity, Condition
│   └── audit.py              # AuditLog, AuditOverride
├── schemas/             # Pydantic models (API request/response shapes)
│   ├── drug.py
│   ├── patient.py
│   └── prescription.py
└── db/                  # Database connections
    ├── session.py            # SQLAlchemy async engine + session
    └── redis.py              # Valkey/Redis client
```

### General Modification Pattern

1. **Models** (`models/`) — Change database tables
2. **Schemas** (`schemas/`) — Change API request/response shapes
3. **Core services** (`core/`) — Change business logic
4. **Routes** (`api/routes/`) — Change HTTP endpoints
5. **Config** (`config.py`) — Add new environment variables

---

## 9. Adding New Drugs to the Database

### Option A: Add to Seed Script

Edit `backend/scripts/seed_data.py` and add to the `DRUGS_DATA` list:

```python
{
    "rxcui": "YOUR_RXCUI",
    "name": "Drug Name 500mg Tablet",
    "generic_name": "Generic Name",
    "dosage_form": "Tablet",
    "route": "Oral",
    "brand_names": ["Brand1", "Brand2"],
    "ingredients": [
        {
            "name": "Active Ingredient Name",
            "type": "active",
            "strength": "500 mg",
            "chemical_family": "Drug Class",
            "allergen_codes": ["SNOMED_CODE"],
        },
        {
            "name": "Excipient Name",
            "type": "excipient",
        },
    ],
},
```

Then re-run: `python -m scripts.seed_data`

### Option B: Via API

```bash
# There's no direct drug creation API yet, but you can add one.
# See "Adding New API Endpoints" section below.
```

### Option C: OpenFDA Sync (Future)

The architecture supports a drug sync worker that pulls from OpenFDA/RxNorm APIs. To implement:

1. Create `backend/scripts/sync_openfda.py`
2. Call `https://api.fda.gov/drug/label.json?search=...`
3. Parse ingredients and insert into the `drugs` / `ingredients` tables
4. Run on a cron schedule

---

## 10. Adding New Allergy Check Rules

### Add a New Check Layer

Edit `backend/app/core/allergy_engine.py`. The function `check_drug_against_profile()` runs layers sequentially. Add your new layer:

```python
# --- LAYER 6: Your custom check ---
for ing in ingredients:
    # Your custom logic here
    if your_condition:
        warnings.append(Warning(
            warning_id=f"W-{uuid.uuid4().hex[:8]}",
            severity="HIGH",
            type="YOUR_CUSTOM_TYPE",
            ingredient=ing["name"],
            allergen="relevant allergen",
            message="Your warning message",
            evidence={
                "source": "YOUR_SOURCE",
                "detail": "Details about why this was flagged",
            },
        ))
        if signal != "RED":
            signal = "YELLOW"
```

### Add a New Cross-Reactivity Group

Add to `CROSS_REACTIVITY_GROUPS` in `seed_data.py`:

```python
{
    "group_name": "Your Group Name",
    "members": [
        {"ingredient_name": "Ingredient A", "probability": "high"},
        {"ingredient_name": "Ingredient B", "probability": "moderate"},
    ],
},
```

---

## 11. Connecting a Real EHR System

Currently, patient data is stored locally. To connect to a real EHR:

### FHIR R4 Integration

Edit `backend/app/core/patient_service.py`:

```python
import httpx

FHIR_BASE = "https://your-fhir-server.com/fhir"

async def get_allergy_profile_from_ehr(patient_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        # Fetch allergies
        resp = await client.get(
            f"{FHIR_BASE}/AllergyIntolerance?patient={patient_id}",
            headers={"Authorization": "Bearer YOUR_TOKEN"},
        )
        allergies = resp.json().get("entry", [])

        # Fetch conditions
        resp = await client.get(
            f"{FHIR_BASE}/Condition?patient={patient_id}",
        )
        conditions = resp.json().get("entry", [])

        # Transform FHIR resources into our profile format
        return {
            "known_allergens": [transform_fhir_allergy(a) for a in allergies],
            "conditions": [transform_fhir_condition(c) for c in conditions],
            # ...
        }
```

Then update `get_allergy_profile()` to call the EHR first and fall back to local DB.

---

## 12. Swapping or Adding AI Models

### Use a Different Ollama Model

```env
OLLAMA_MODEL=gemma2:9b          # or llama3.1:8b, mistral:7b, etc.
```

Then pull it: `ollama pull gemma2:9b`

### Use a Different HuggingFace Model

```env
HF_MODEL_ID=mistralai/Mistral-7B-Instruct-v0.3
# or
HF_MODEL_ID=meta-llama/Llama-3.1-8B-Instruct
```

### Add a Completely New Backend (e.g., OpenAI, Anthropic, local vLLM)

1. Create `backend/app/core/ai_backends/your_backend.py`:

```python
from app.core.ai_backends.base import AIBackend

class YourBackend(AIBackend):
    @property
    def name(self) -> str:
        return "your_backend"

    @property
    def supports_vision(self) -> bool:
        return True  # or False

    async def chat(self, messages, temperature=0.1, max_tokens=1000) -> str:
        # Your implementation here
        ...

    async def chat_with_image(self, prompt, image_b64, temperature=0.1, max_tokens=1000) -> str:
        # Your implementation here
        ...
```

2. Register it in `backend/app/core/ai_backends/factory.py`:

```python
elif backend_name == "your_backend":
    from app.core.ai_backends.your_backend import YourBackend
    _backend_instance = YourBackend()
```

3. Set `AI_BACKEND=your_backend` in `.env`

---

## 13. Adding New API Endpoints

### Example: Add a Drug Creation Endpoint

1. **Add schema** in `backend/app/schemas/drug.py`:

```python
class DrugCreate(BaseModel):
    rxcui: str
    name: str
    generic_name: str | None = None
    dosage_form: str | None = None
    route: str | None = None
    brand_names: list[str] | None = None
```

2. **Add route** in `backend/app/api/routes/drugs.py`:

```python
@router.post("", response_model=DrugOut, status_code=201)
async def create_drug(
    data: DrugCreate,
    db: AsyncSession = Depends(get_db),
):
    drug = Drug(**data.model_dump())
    db.add(drug)
    await db.flush()
    return drug
```

3. The endpoint is automatically available at `POST /api/v1/drugs` and appears in Swagger docs.

---

## 14. Modifying the Frontend

### Key Files

| File | Purpose |
|------|---------|
| `frontend/src/app/page.tsx` | Main page — patient selector, drug search, results display |
| `frontend/src/app/layout.tsx` | HTML layout, metadata, global styles |
| `frontend/src/app/globals.css` | TailwindCSS imports + custom styles |
| `frontend/src/lib/api.ts` | API client — all backend calls |

### Change the API URL

Edit `frontend/src/lib/api.ts` line 1:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

Or set the env var: `NEXT_PUBLIC_API_URL=https://your-api.com`

### Add a New Page

Create `frontend/src/app/admin/page.tsx`:

```tsx
export default function AdminPage() {
  return <div>Admin Dashboard</div>;
}
```

It's automatically available at http://localhost:3000/admin (Next.js file-based routing).

### Modify the UI

The frontend uses **TailwindCSS** for styling. All styles are utility classes directly in the JSX. To change colors, spacing, or layout, edit the `className` props in `page.tsx`.

---

## 15. Database Schema Changes

### Add a New Column

1. Edit the model in `backend/app/models/`:

```python
class Drug(Base):
    __tablename__ = "drugs"
    # ... existing columns ...
    manufacturer: Mapped[str | None] = mapped_column(String(300))  # NEW
```

2. Restart the backend — tables are auto-created on startup via `Base.metadata.create_all`.

> **Note:** `create_all` only adds new tables/columns. It won't modify existing columns. For production migrations, use Alembic:

```bash
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "add manufacturer column"
alembic upgrade head
```

### Add a New Table

1. Create a new model file (e.g., `backend/app/models/pharmacy.py`)
2. Import it in `backend/app/main.py` so SQLAlchemy discovers it
3. Restart — the table is auto-created

---

## 16. Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...@postgres:5432/medguard` | Async PostgreSQL connection string |
| `REDIS_URL` | `redis://valkey:6379/0` | Valkey/Redis connection string |
| `AI_BACKEND` | `ollama` | AI provider: `ollama`, `huggingface_local`, `huggingface_api` |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `medgemma:4b` | Ollama model name |
| `HF_MODEL_ID` | `google/medgemma-4b-it` | HuggingFace model ID |
| `HF_TOKEN` | (empty) | HuggingFace API token |
| `HF_DEVICE` | `auto` | Device for local HF: `auto`, `cpu`, `cuda`, `mps` |
| `HF_TORCH_DTYPE` | `auto` | Precision: `auto`, `float16`, `bfloat16`, `float32` |
| `HF_MAX_NEW_TOKENS` | `1024` | Max tokens for HF generation |
| `APP_ENV` | `development` | Environment: `development`, `production` |
| `APP_DEBUG` | `true` | Enable debug logging |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed CORS origins (comma-separated) |
| `APP_SECRET_KEY` | `change-me-in-production` | Secret key for signing |
| `KEYCLOAK_URL` | `http://keycloak:8080` | Keycloak server URL |
| `KEYCLOAK_REALM` | `medguard` | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | `medguard-api` | Keycloak client ID |

---

## 17. Troubleshooting

### Backend won't start

```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Fix:** Make sure PostgreSQL is running: `docker compose up postgres -d`

### Redis connection refused

```
redis.exceptions.ConnectionError: Error connecting to localhost:6379
```
**Fix:** Make sure Valkey is running: `docker compose up valkey -d`

### Drug search returns empty results

**Fix:** Run the seed script: `python -m scripts.seed_data`

### AI features not working

```
ai_cross_reactivity_check_skipped
```
**This is normal** if Ollama isn't running. The allergy engine gracefully degrades — Layers 1-4 still work without AI. To enable AI:
- Start Ollama: `ollama serve` then `ollama pull medgemma:4b`
- Or switch to HuggingFace API: `AI_BACKEND=huggingface_api`

### Frontend can't reach backend

```
TypeError: Failed to fetch
```
**Fix:** Check that:
1. Backend is running on port 8000
2. CORS is configured: `CORS_ORIGINS=http://localhost:3000`
3. `NEXT_PUBLIC_API_URL` points to the correct backend URL

### pg_trgm extension error

```
ERROR: extension "pg_trgm" is not available
```
**Fix:** Use the official PostgreSQL image (`postgres:16-alpine`), which includes `pg_trgm`. Custom PostgreSQL builds may not include it.

### HuggingFace model access denied

```
401 Client Error: Unauthorized
```
**Fix:** MedGemma is a gated model. You need to:
1. Accept the license at https://huggingface.co/google/medgemma-4b-it
2. Set `HF_TOKEN` to your HuggingFace token

### Out of memory with HuggingFace local

```
torch.cuda.OutOfMemoryError
```
**Fix:** Use a smaller model or lower precision:
```env
HF_MODEL_ID=google/gemma-2-2b-it    # Smaller model
HF_TORCH_DTYPE=float16               # Half precision
```
Or switch to `AI_BACKEND=huggingface_api` to offload to HF's servers.