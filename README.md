# MedGuard — Medicine Allergy Detection System

Prevent allergic reactions by checking prescribed drug ingredients against patient allergy profiles in real-time.

**100% Open-Source · MedGemma-Powered · Docker-Ready**

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed
- At least **8 GB RAM** available for Docker (MedGemma model needs ~4 GB)
- Ports `3000`, `8000`, `5432`, `6379`, `11434` available

### 1. Clone and Start

```bash
# Start all services (PostgreSQL, Valkey, Ollama, Backend, Frontend)
docker compose up --build -d

# Wait ~30 seconds for services to initialize, then seed the database
docker compose --profile seed run --rm seed
```

### 2. Pull MedGemma Model (first time only)

```bash
# Pull the MedGemma model into Ollama (~2.5 GB download)
docker compose exec ollama ollama pull medgemma:4b

# If medgemma is not available yet, use gemma2 as fallback:
# docker compose exec ollama ollama pull gemma2:2b
```

> **Note:** If `medgemma:4b` is not yet available on Ollama, update `OLLAMA_MODEL` in `docker-compose.yml` to `gemma2:2b` as a temporary fallback. The system works with any Ollama model, HuggingFace model, or HuggingFace Inference API. See [GUIDE.md](./GUIDE.md#4-ai-backend-configuration) for all AI backend options.

### 3. Open the App

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

### 4. Try It Out

1. Enter patient ID: `P-5678` (John Doe — Penicillin + Sulfonamide allergy, G6PD deficiency)
2. Search for "Amoxicillin" and add it
3. Click **Check for Allergies**
4. You should see a **RED** signal — Amoxicillin contains Penicillin-class ingredients

Other test scenarios:
- Patient `P-1234` (Jane Smith — Aspirin allergy) + search "Ibuprofen" → YELLOW (NSAID cross-reactivity)
- Patient `P-5678` + search "Azithromycin" → GREEN (safe Macrolide antibiotic)
- Patient `P-5678` + search "Sulfamethoxazole" → RED (Sulfonamide allergy + G6PD contraindication)

---

## Architecture

```
Frontend (Next.js :3000)
  → Backend API (FastAPI :8000)
    → MedGemma AI (Ollama :11434) — OCR, reasoning, alternatives
    → PostgreSQL (:5432) — drugs, patients, allergies, audit logs
    → Valkey (:6379) — caching layer
```

See [architecture/](./architecture/) for full system design documentation.

---

## Project Structure

```
Aller/
├── docker-compose.yml          # Full stack orchestration
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── config.py           # Environment config
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── prescription.py   # /api/v1/prescription/* (check + override)
│   │   │   │   ├── drugs.py          # /api/v1/drugs/* (search + ingredients)
│   │   │   │   └── patients.py       # /api/v1/patients/* (profile + allergies)
│   │   │   └── middleware/
│   │   │       └── auth.py           # Keycloak JWT (dev mode: no auth needed)
│   │   ├── core/
│   │   │   ├── allergy_engine.py     # Core 5-layer matching logic
│   │   │   ├── ai_service.py         # MedGemma integration (OCR + reasoning)
│   │   │   ├── drug_service.py       # Drug lookup + cross-reactivity
│   │   │   ├── patient_service.py    # Patient allergy profiles
│   │   │   └── audit_service.py      # Immutable audit logging
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   └── db/                       # Database + Redis session management
│   └── scripts/
│       └── seed_data.py              # Demo data seeder
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   └── page.tsx              # Main prescription check UI
│       └── lib/
│           └── api.ts                # API client
└── architecture/                     # Design documentation
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/prescription/check` | Check drugs against patient allergies (manual entry) |
| `POST` | `/api/v1/prescription/check/photo` | Check via prescription photo (MedGemma OCR) |
| `POST` | `/api/v1/prescription/override` | Override a RED warning with justification |
| `GET`  | `/api/v1/drugs/search?q=amox` | Search drugs by name (fuzzy) |
| `GET`  | `/api/v1/drugs/{rxcui}/ingredients` | Get drug ingredients |
| `GET`  | `/api/v1/patients/{id}/allergy-profile` | Get patient allergy profile |
| `POST` | `/api/v1/patients` | Create a new patient |
| `POST` | `/api/v1/patients/{id}/allergies` | Add allergy to patient |
| `POST` | `/api/v1/patients/{id}/lab-sensitivities` | Add lab sensitivity |
| `POST` | `/api/v1/patients/{id}/conditions` | Add condition |
| `GET`  | `/health` | Basic health check |
| `GET`  | `/health/ready` | Readiness check (DB + cache) |

---

## Allergy Check Logic (5 Layers)

1. **Direct Match** — Ingredient name matches known allergen → RED
2. **Cross-Reactivity (DB)** — Ingredient in same chemical family as allergen → RED/YELLOW
3. **Lab Sensitivity** — Elevated IgE or related lab markers → YELLOW
4. **Condition Contraindication** — Ingredient contraindicated for patient condition → RED
5. **AI Cross-Reactivity (MedGemma)** — AI-detected cross-reactivity for edge cases → YELLOW

---

## Development

### Backend only (without Docker)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env           # Edit as needed
uvicorn app.main:app --reload --port 8000
```

### Frontend only (without Docker)

```bash
cd frontend
npm install
npm run dev                    # http://localhost:3000
```

### Useful Commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f ollama

# Re-seed database
docker compose --profile seed run --rm seed

# Pull a different model
docker compose exec ollama ollama pull gemma2:2b

# Stop everything
docker compose down

# Stop and remove all data
docker compose down -v
```

---

## Tech Stack (100% Open-Source)

| Component | Technology | License |
|-----------|-----------|---------|
| Backend | Python FastAPI | MIT |
| Frontend | Next.js + TailwindCSS | MIT |
| AI/OCR | MedGemma via Ollama / HuggingFace | Apache 2.0 |
| Database | PostgreSQL + pg_trgm | PostgreSQL |
| Cache | Valkey (Redis fork) | BSD-3 |
| Orchestration | Docker Compose | Apache 2.0 |

---

## Documentation

- **[GUIDE.md](./GUIDE.md)** — Full developer & user guide: local setup, AI backend configuration, how to modify the codebase, add drugs, connect EHR, extend the API, and troubleshooting
- **[architecture/](./architecture/)** — System design docs, diagrams, API contracts, deployment strategy

---

## License

MIT