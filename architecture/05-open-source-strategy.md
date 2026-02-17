# MedGuard — Open-Source & Zero-Budget Strategy

> **Principle:** Every component must be open-source or free-tier. No vendor lock-in. Self-hostable on a single VPS to start, scalable to Kubernetes later.

---

## 1. Component-by-Component: Paid → Open-Source Mapping

| Concern | Previous (Paid) | Open-Source Replacement | License | Notes |
|---------|-----------------|----------------------|---------|-------|
| **Prescription OCR** | Azure AI Document Intelligence | **MedGemma (Google, open-weight)** + Tesseract OCR fallback | Apache 2.0 / Apache 2.0 | MedGemma understands medical text natively; Tesseract as lightweight fallback |
| **Lab Report Parsing** | Custom NLP | **MedGemma** | Apache 2.0 | Feed lab report images/text → extract IgE values, allergy markers |
| **Drug Name Resolution** | Paid NLP APIs | **MedGemma** + RxNorm free API | Apache 2.0 / Public Domain | MedGemma for fuzzy medical name understanding; RxNorm for canonical mapping |
| **Alternative Drug Suggestion** | Manual curation | **MedGemma** | Apache 2.0 | "Suggest alternatives to Amoxicillin for a Penicillin-allergic patient" |
| **API Gateway** | Kong Enterprise / AWS API GW | **Traefik** (or Caddy) | MIT / Apache 2.0 | Built-in Let's Encrypt, rate limiting, middleware |
| **Backend Framework** | Node.js / FastAPI | **FastAPI (Python)** | MIT | Python ecosystem aligns with ML model serving |
| **Frontend** | React (already OSS) | **Next.js** (React-based) | MIT | Free, SSR, great DX |
| **Mobile** | React Native | **Expo (React Native)** | MIT | Free builds via EAS for dev |
| **Database** | AWS RDS PostgreSQL | **PostgreSQL** (self-hosted) | PostgreSQL License | Free, battle-tested |
| **Cache** | AWS ElastiCache | **Redis** (self-hosted, OSS) or **Valkey** | BSD-3 / BSD-3 | Valkey is the Redis fork by Linux Foundation |
| **Search** | AWS OpenSearch | **Meilisearch** or **PostgreSQL pg_trgm** | MIT / PostgreSQL | Meilisearch is lighter than ElasticSearch; pg_trgm avoids a separate service entirely |
| **Graph DB** | Neo4j Enterprise | **Apache AGE** (PostgreSQL extension) | Apache 2.0 | Graph queries inside PostgreSQL — no separate DB needed |
| **Message Queue** | AWS SQS / RabbitMQ | **RabbitMQ** (self-hosted) or **PostgreSQL LISTEN/NOTIFY** | MPL 2.0 / PostgreSQL | For early stage, PG notify is enough; RabbitMQ when scaling |
| **Object Storage** | AWS S3 | **MinIO** (self-hosted) | AGPL-3.0 | S3-compatible API, self-hosted |
| **ML Model Serving** | SageMaker / Vertex AI | **Ollama** or **vLLM** | MIT / Apache 2.0 | Serve MedGemma locally; Ollama for simplicity, vLLM for production throughput |
| **EHR System** | Epic / Cerner (paid) | **OpenMRS** (self-hosted) or **HAPI FHIR Server** | MPL 2.0 / Apache 2.0 | Free FHIR R4 server for your own EHR if needed |
| **Auth / Identity** | Auth0 / Okta | **Keycloak** | Apache 2.0 | Full OAuth 2.0 / OIDC / RBAC, self-hosted |
| **CI/CD** | GitHub Actions (paid mins) | **Gitea** + **Woodpecker CI** or **GitHub Actions free tier** | MIT / Apache 2.0 | Gitea is self-hosted Git; 2000 free mins/month on GitHub |
| **Monitoring** | Datadog / New Relic | **Prometheus + Grafana** | Apache 2.0 | Already open-source in original design |
| **Logging** | ELK (Elastic license) | **Grafana Loki + Promtail** | AGPL-3.0 | Lighter than ELK, integrates with Grafana |
| **Tracing** | AWS X-Ray | **Jaeger** | Apache 2.0 | Already open-source in original design |
| **Secrets Management** | AWS Secrets Manager | **Infisical** or **SOPS** | MIT / MPL 2.0 | Infisical is a full Vault alternative; SOPS for encrypted files |
| **Container Orchestration** | EKS / AKS ($$$) | **K3s** (lightweight K8s) or **Docker Compose** (early stage) | Apache 2.0 | K3s runs on a single $5/month VPS |
| **Reverse Proxy + TLS** | AWS ALB + ACM | **Caddy** | Apache 2.0 | Automatic HTTPS, zero config |
| **WAF / DDoS** | AWS WAF / Cloudflare Pro | **Cloudflare Free Tier** + **ModSecurity** | Free / Apache 2.0 | Cloudflare free gives DNS + basic DDoS |

---

## 2. MedGemma — The AI Core

### 2.1 What is MedGemma?

MedGemma is Google's **open-weight medical AI model** built on Gemma, specifically fine-tuned for healthcare tasks:
- Medical text understanding (prescriptions, lab reports, clinical notes)
- Medical image analysis (prescription photos, lab report scans)
- Medical Q&A and reasoning
- Drug interaction and safety knowledge

### 2.2 How MedGemma Replaces Multiple Paid Services

```
┌─────────────────────────────────────────────────────────────────┐
│                    MedGemma REPLACES                            │
│                                                                 │
│  ┌─────────────────────┐                                       │
│  │ Azure AI Document   │──┐                                    │
│  │ Intelligence ($$$)  │  │                                    │
│  └─────────────────────┘  │                                    │
│  ┌─────────────────────┐  │    ┌──────────────────────────┐    │
│  │ Google Cloud Vision │──┼───▶│  MedGemma (self-hosted)  │    │
│  │ ($$$)               │  │    │                          │    │
│  └─────────────────────┘  │    │  • OCR + medical context │    │
│  ┌─────────────────────┐  │    │  • Drug name extraction  │    │
│  │ Medical NLP APIs    │──┤    │  • Lab report parsing    │    │
│  │ ($$$)               │  │    │  • Alternative drug      │    │
│  └─────────────────────┘  │    │    suggestions           │    │
│  ┌─────────────────────┐  │    │  • Cross-reactivity      │    │
│  │ Drug Interaction    │──┘    │    reasoning             │    │
│  │ APIs ($$$)          │       │                          │    │
│  └─────────────────────┘       │  Cost: $0 (self-hosted)  │    │
│                                └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 MedGemma Integration Points

| Use Case | Input | MedGemma Prompt Strategy | Output |
|----------|-------|-------------------------|--------|
| **Prescription OCR** | Prescription photo | `"Extract all medicine names, dosages, and forms from this prescription image."` | Structured list of drug names |
| **Drug Name Normalization** | Raw OCR text like "Amoxycillin 500" | `"Normalize this medicine name to its standard generic name and identify the RxNorm concept: Amoxycillin 500"` | `{generic: "Amoxicillin", rxcui: "723"}` |
| **Lab Report Extraction** | Lab report image/text | `"Extract allergy-related lab results from this report. Focus on IgE levels, skin prick test results, and any flagged sensitivities."` | Structured lab findings |
| **Cross-Reactivity Check** | Ingredient + allergy | `"Patient is allergic to Penicillin. Is Amoxicillin cross-reactive? Explain the chemical relationship and risk level."` | Risk assessment + explanation |
| **Alternative Suggestions** | Drug + allergy profile | `"Suggest safe antibiotic alternatives to Amoxicillin for a patient with confirmed Penicillin allergy and elevated IgE for Cephalosporins."` | Ranked alternatives with reasoning |
| **Warning Message Generation** | Check result data | `"Generate a clear clinical warning for a doctor: Patient has Penicillin allergy, prescribed drug contains Amoxicillin (Penicillin-class)."` | Human-readable warning text |

### 2.4 Model Serving Architecture

```
┌──────────────────────────────────────────────────────────┐
│                MedGemma Serving Stack                     │
│                                                          │
│  Option A: Ollama (Simple, dev-friendly)                 │
│  ┌────────────────────────────────────────────┐          │
│  │  $ ollama pull medgemma                    │          │
│  │  $ ollama serve                            │          │
│  │  API: http://localhost:11434/api/generate  │          │
│  │  Memory: ~8GB RAM (4-bit quantized)        │          │
│  └────────────────────────────────────────────┘          │
│                                                          │
│  Option B: vLLM (Production, high throughput)            │
│  ┌────────────────────────────────────────────┐          │
│  │  $ vllm serve google/medgemma-27b-text-it  │          │
│  │  API: OpenAI-compatible endpoint           │          │
│  │  Features: Batching, PagedAttention,       │          │
│  │            continuous batching              │          │
│  │  Memory: ~16GB VRAM (FP16) or 8GB (INT4)  │          │
│  └────────────────────────────────────────────┘          │
│                                                          │
│  Option C: llama.cpp / llama-cpp-python (CPU-only)       │
│  ┌────────────────────────────────────────────┐          │
│  │  GGUF quantized model, runs on CPU         │          │
│  │  Slower but works without GPU              │          │
│  │  Good for: dev machines, budget VPS        │          │
│  └────────────────────────────────────────────┘          │
│                                                          │
│  MedGemma Variants:                                      │
│  ├── medgemma-4b-it   → 4B params, fast, ~4GB RAM       │
│  ├── medgemma-27b-it  → 27B params, accurate, ~16GB RAM │
│  └── medgemma-4b-img  → Multimodal (image+text), OCR    │
│                                                          │
│  Recommended for MedGuard:                               │
│  • medgemma-4b-img  → Prescription photo OCR             │
│  • medgemma-27b-it  → Drug reasoning, alternatives       │
│  • (or just 4b-it for everything if RAM-constrained)     │
└──────────────────────────────────────────────────────────┘
```

### 2.5 MedGemma Safety Guardrails

MedGemma outputs should **NEVER** be the sole decision-maker. The system uses a **layered approach**:

```
Layer 1: Deterministic Rule Engine (primary)
  └── Direct allergen match from structured DB → always authoritative

Layer 2: MedGemma AI (augmentation)
  └── Cross-reactivity reasoning, alternative suggestions, warning text
  └── Always validated against structured drug DB before showing to doctor

Layer 3: Doctor's Clinical Judgment (final)
  └── Doctor can override any signal with documented justification
```

**Key safety rules:**
- MedGemma **never** overrides a RED signal from the rule engine
- MedGemma suggestions are always **labeled as AI-generated**
- All MedGemma outputs are **logged for audit**
- Structured DB match is always preferred over AI inference
- MedGemma is used for **enrichment**, not **decision-making**

---

## 3. Simplified Architecture (Open-Source Stack)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DOCTOR'S INTERFACE                            │
│  (Next.js Web App / Expo Mobile App)                                   │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────┐       │
│  │ Photo Capture │  │ Manual Drug Entry│  │ Patient Selector   │       │
│  └──────┬───────┘  └────────┬─────────┘  └─────────┬──────────┘       │
└─────────┼───────────────────┼───────────────────────┼──────────────────┘
          │                   │                       │
          ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    REVERSE PROXY (Caddy / Traefik)                     │
│         Auto-TLS (Let's Encrypt)  ·  Rate Limiting                    │
└─────────┬───────────────────┬───────────────────────┬──────────────────┘
          │                   │                       │
          ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (Python)                            │
│                                                                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ OCR Module  │  │ Drug Service │  │ Patient Svc  │  │ Allergy    │ │
│  │ (MedGemma   │  │ (RxNorm +   │  │ (FHIR R4 /   │  │ Engine     │ │
│  │  multimodal │  │  OpenFDA +   │  │  OpenMRS /    │  │ (Rules +   │ │
│  │  + Tesseract│  │  PostgreSQL) │  │  HAPI FHIR)  │  │  MedGemma) │ │
│  │  fallback)  │  │              │  │              │  │            │ │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                │                  │                │        │
│         └────────────────┴──────────────────┴────────────────┘        │
│                                    │                                   │
│                          ┌─────────┴─────────┐                        │
│                          │   Keycloak Auth    │                        │
│                          │   (OAuth 2.0)      │                        │
│                          └───────────────────┘                        │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
          ┌─────────▼────────┐    ┌──────────▼──────────┐
          │   PostgreSQL     │    │   MedGemma Server   │
          │   (with AGE +   │    │   (Ollama / vLLM)   │
          │    pg_trgm)     │    │                     │
          │                  │    │   Models:           │
          │  • Drug DB       │    │   • 4b-img (OCR)   │
          │  • Patient data  │    │   • 27b-it (reason)│
          │  • Audit logs    │    │                     │
          │  • Graph (AGE)   │    └─────────────────────┘
          │  • Search (trgm) │
          └──────┬───────────┘
                 │
          ┌──────▼───────────┐
          │   Valkey / Redis │
          │   (cache layer)  │
          └──────────────────┘
```

### Key Simplification: Modular Monolith (not Microservices)

For a first product with zero budget, **microservices are overkill**. Instead:

```
medguard/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── api/
│   │   ├── routes/
│   │   │   ├── prescription.py  # /api/v1/prescription/*
│   │   │   ├── drugs.py         # /api/v1/drugs/*
│   │   │   ├── patients.py      # /api/v1/patients/*
│   │   │   └── auth.py          # /api/v1/auth/*
│   │   └── middleware/
│   │       ├── auth.py          # Keycloak JWT validation
│   │       └── rate_limit.py    # In-memory rate limiting
│   ├── core/
│   │   ├── allergy_engine.py    # Core matching logic (deterministic)
│   │   ├── ocr_service.py       # MedGemma multimodal + Tesseract
│   │   ├── drug_service.py      # Drug lookup, ingredient resolution
│   │   ├── patient_service.py   # EHR/FHIR integration
│   │   └── ai_service.py        # MedGemma text inference wrapper
│   ├── models/                  # SQLAlchemy / Pydantic models
│   ├── db/                      # Database migrations (Alembic)
│   └── config.py                # Environment-based config
├── docker-compose.yml           # Full local stack
├── Dockerfile
├── requirements.txt
└── tests/
```

**Why modular monolith?**
- Single deployment = single VPS = ~$10-20/month
- No inter-service network latency
- Easy to debug, deploy, and maintain as a solo/small team
- Can be split into microservices later when you have revenue

---

## 4. Deployment: From $0 to Production

### Phase 1: Development (Cost: $0)

```
Your Laptop / Desktop
├── Docker Compose (all services)
├── Ollama + MedGemma 4b (runs on 8GB RAM)
├── PostgreSQL container
├── Valkey container
└── FastAPI dev server

Total cost: $0
```

### Phase 2: MVP / Beta (Cost: ~$20-50/month)

```
Single VPS (Hetzner CX32 or DigitalOcean $24/month)
├── 4 vCPU, 8GB RAM, 80GB SSD
├── Docker Compose
│   ├── Caddy (reverse proxy + auto-TLS)
│   ├── FastAPI app
│   ├── PostgreSQL
│   ├── Valkey
│   ├── Keycloak
│   └── Ollama + MedGemma 4b-it (quantized)
├── Cloudflare Free (DNS + DDoS protection)
└── GitHub Free (code + CI/CD 2000 mins/month)

Handles: ~50-100 concurrent doctors
Total cost: ~$20-30/month
```

### Phase 3: Growth (Cost: ~$100-200/month)

```
GPU VPS (Hetzner GPU or RunPod, ~$80-150/month)
├── For MedGemma 27b model serving (better accuracy)
└── vLLM for production throughput

App VPS (Hetzner CX42, ~$35/month)
├── K3s (lightweight Kubernetes)
├── 2-3 replicas of FastAPI
├── PostgreSQL with streaming replication
├── Valkey cluster
└── Keycloak

Cloudflare Free + Let's Encrypt
GitHub Actions Free Tier

Handles: ~500-1000 concurrent doctors
Total cost: ~$120-185/month
```

### Phase 4: Scale (Cost: ~$300-500/month)

```
Multiple VPS nodes with K3s cluster
├── Dedicated DB node (PostgreSQL + Valkey)
├── Dedicated GPU node (MedGemma via vLLM)
├── 2-3 App nodes (FastAPI replicas)
├── Meilisearch node (if pg_trgm isn't enough)
└── Monitoring (Prometheus + Grafana + Loki)

Handles: ~5000+ concurrent doctors
Total cost: ~$300-500/month
```

---

## 5. Cost Comparison: Paid vs Open-Source

| Component | Paid Stack (Monthly) | Open-Source Stack (Monthly) |
|-----------|--------------------:|---------------------------:|
| Cloud Kubernetes (EKS/AKS) | $450 | $0 (K3s on VPS) |
| Managed PostgreSQL | $400 | $0 (self-hosted) |
| Managed Redis | $600 | $0 (Valkey self-hosted) |
| ElasticSearch managed | $500 | $0 (pg_trgm / Meilisearch) |
| OCR API (Azure/AWS) | $150+ | $0 (MedGemma self-hosted) |
| Auth (Auth0/Okta) | $100+ | $0 (Keycloak) |
| API Gateway (Kong EE) | $200+ | $0 (Traefik/Caddy) |
| Monitoring (Datadog) | $200+ | $0 (Prometheus+Grafana) |
| **VPS hosting** | — | **$24-50** |
| **Total** | **~$2,600+/month** | **~$24-50/month** |

**Savings: ~98%**

---

## 6. Free External Data Sources (No API Keys Needed)

| Source | URL | What You Get | Cost |
|--------|-----|-------------|------|
| **OpenFDA Drug Labels** | api.fda.gov | Drug ingredients, adverse events, labels | Free (no key for basic) |
| **RxNorm REST API** | rxnav.nlm.nih.gov | Drug name normalization, ingredient mapping | Free (UMLS license, free registration) |
| **DailyMed** | dailymed.nlm.nih.gov | Full SPL drug labels with excipients | Free (bulk download) |
| **RxClass** | rxnav.nlm.nih.gov | Drug classification, chemical families | Free |
| **SNOMED CT** | snomed.org | Allergy/substance coding | Free (member countries) |
| **LOINC** | loinc.org | Lab test coding | Free (registration required) |
| **DrugBank Open** | go.drugbank.com | Basic drug-ingredient data | Free tier available |
| **PubChem** | pubchem.ncbi.nlm.nih.gov | Chemical compound data, cross-reactivity | Free |

---

## 7. Open-Source EHR Options

If you don't have an existing EHR to integrate with, you can run your own:

| EHR System | License | FHIR Support | Best For |
|-----------|---------|-------------|----------|
| **OpenMRS** | MPL 2.0 | Via FHIR2 module | Developing countries, clinics |
| **HAPI FHIR Server** | Apache 2.0 | Native FHIR R4 | Pure FHIR data store |
| **OpenEMR** | GPL-3.0 | Via API | Small practices, US-focused |
| **Bahmni** | AGPL-3.0 | Via OpenMRS | Hospital-scale, India-focused |
| **LibreHealth** | MPL 2.0 | Partial | Community clinics |

**Recommendation for MVP:** Use **HAPI FHIR Server** as your patient data store. It's the simplest way to have a FHIR-compliant backend without the complexity of a full EHR.

---

## 8. Hardware Requirements

### Minimum (Development / Small Clinic)

| Component | Requirement |
|-----------|------------|
| **CPU** | 4 cores (x86_64) |
| **RAM** | 8 GB (MedGemma 4b quantized + all services) |
| **Storage** | 40 GB SSD |
| **GPU** | Not required (CPU inference with llama.cpp) |

### Recommended (Production / 50-100 doctors)

| Component | Requirement |
|-----------|------------|
| **CPU** | 8 cores |
| **RAM** | 16 GB |
| **Storage** | 80 GB SSD |
| **GPU** | Optional: NVIDIA T4 (16GB VRAM) for faster MedGemma inference |

### Scaling (500+ doctors)

| Component | Requirement |
|-----------|------------|
| **App Server** | 8 vCPU, 16 GB RAM |
| **GPU Server** | NVIDIA A10/L4 (24GB VRAM) for MedGemma 27b |
| **DB Server** | 4 vCPU, 16 GB RAM, 200 GB SSD |

