# MedGuard — Medicine Allergy Detection System

## 1. Problem Statement

When doctors prescribe medicines, they may unknowingly prescribe drugs containing ingredients to which the patient is allergic. These medicines can be tablets, lotions, syrups, injectables, or any pharmaceutical product. Allergic reactions range from mild rashes to life-threatening anaphylaxis.

**Goal:** Build a scalable, real-time system that:
1. Ingests patient EHR data (including lab reports and known allergies).
2. Allows doctors to input prescriptions via **photo capture** (OCR) or **manual text entry**.
3. Resolves each medicine to its **full ingredient list** (active + inactive/excipient).
4. Cross-references ingredients against the patient's known allergies and lab-flagged sensitivities.
5. Returns a clear **GREEN / YELLOW / RED** signal with detailed warnings before the prescription is finalized.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DOCTOR'S INTERFACE                            │
│  (Web / Mobile App)                                                    │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────┐       │
│  │ Photo Capture │  │ Manual Drug Entry│  │ Patient Selector   │       │
│  └──────┬───────┘  └────────┬─────────┘  └─────────┬──────────┘       │
│         │                   │                       │                  │
└─────────┼───────────────────┼───────────────────────┼──────────────────┘
          │                   │                       │
          ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    REVERSE PROXY (Caddy / Traefik — OSS)              │
│         Auth (Keycloak OAuth 2.0)  ·  Rate Limiting                   │
└─────────┬───────────────────┬───────────────────────┬──────────────────┘
          │                   │                       │
          ▼                   ▼                       ▼
  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────────┐
  │  OCR Service  │  │ Prescription  │  │   Patient Context       │
  │  (MedGemma    │  │   Service     │  │      Service            │
  │  multimodal + │  │               │  │  (EHR + Lab Reports)    │
  │  Tesseract    │  │  Drug name    │  │                         │
  │  fallback)    │  │  resolution   │  │  Fetches allergies,     │
  │               │  │  + fuzzy      │  │  lab flags, conditions  │
  │  Extracts     │  │  matching     │  │  via FHIR R4            │
  │  drug names   │  │               │  │                         │
  └───────┬───────┘  └───────┬───────┘  └────────────┬────────────┘
          │                   │                       │
          └─────────┬─────────┘                       │
                    ▼                                 │
          ┌─────────────────┐                         │
          │  Drug Ingredient│                         │
          │    Service      │                         │
          │                 │                         │
          │  Resolves drug  │                         │
          │  → ingredients  │                         │
          │  (OpenFDA /     │                         │
          │   RxNorm /      │                         │
          │   local DB)     │                         │
          └────────┬────────┘                         │
                   │                                  │
                   ▼                                  ▼
          ┌──────────────────────────────────────────────┐
          │          ALLERGY CHECK ENGINE                 │
          │                                              │
          │  Ingredient list  ×  Patient allergy profile │
          │                                              │
          │  Output:                                     │
          │    GREEN  — No known conflicts               │
          │    YELLOW — Possible cross-reactivity        │
          │    RED    — Direct allergen match detected    │
          │                                              │
          │  + Detailed warning messages                 │
          └──────────────────┬───────────────────────────┘
                             │
                             ▼
          ┌──────────────────────────────────────────────┐
          │           RESPONSE TO DOCTOR UI              │
          │                                              │
          │  ✅ GREEN  — Safe to prescribe               │
          │  ⚠️ YELLOW — Review recommended              │
          │  🔴 RED    — DO NOT PRESCRIBE (with reason)  │
          │                                              │
          │  + Alternative drug suggestions (optional)   │
          └──────────────────────────────────────────────┘
```

---

## 3. Core Services Breakdown

### 3.1 Prescription Ingestion Layer

| Component | Responsibility | Tech Options |
|-----------|---------------|--------------|
| **OCR Service** | Extract medicine names from prescription slip photos | **MedGemma 4b-img** (multimodal, self-hosted via Ollama/vLLM) + Tesseract fallback |
| **Drug Name Resolver** | Fuzzy-match extracted text to canonical drug names | **MedGemma** for fuzzy medical understanding + RxNorm free API + PostgreSQL pg_trgm |
| **Manual Entry Autocomplete** | Typeahead search against drug database | **PostgreSQL pg_trgm** (or Meilisearch if needed) with RxNorm data |

### 3.2 Drug Knowledge Layer

| Component | Responsibility | Tech Options |
|-----------|---------------|--------------|
| **Drug Ingredient Database** | Store and serve drug → ingredient mappings (active + excipients) | **PostgreSQL** + **Valkey/Redis** cache, seeded from OpenFDA / DailyMed / RxNorm (all free) |
| **Ingredient Taxonomy** | Map ingredient synonyms, chemical families, cross-reactivity groups | **Apache AGE** (graph extension for PostgreSQL — no separate DB needed) |
| **Drug DB Sync Worker** | Periodically sync latest drug data from FDA / regulatory sources | Python cron script / **Ofelia** (Docker cron) |

### 3.3 Patient Data Layer

| Component | Responsibility | Tech Options |
|-----------|---------------|--------------|
| **EHR Integration Service** | Pull patient allergies, conditions, lab results | FHIR R4 API via **HAPI FHIR Server** (OSS) or **OpenMRS** (OSS) |
| **Patient Allergy Profile Cache** | Pre-computed allergy profile for fast lookup | **Valkey/Redis** (self-hosted) with TTL |
| **Lab Report Parser** | Extract allergy-related markers from lab reports (IgE levels, skin prick results) | **MedGemma** for unstructured lab notes + rule engine for structured data |

### 3.4 Allergy Check Engine (Core Business Logic)

This is the **heart of the system**:

```
INPUT:
  - List<Ingredient> from prescribed drug(s)
  - PatientAllergyProfile {
      knownAllergens: List<Allergen>,
      crossReactivityGroups: List<Group>,
      labFlaggedSensitivities: List<Sensitivity>,
      conditions: List<Condition>  // e.g., G6PD deficiency
    }

ALGORITHM:
  1. DIRECT MATCH — ingredient ∈ knownAllergens → RED
  2. CROSS-REACTIVITY — ingredient.chemicalFamily ∈ crossReactivityGroups → YELLOW/RED
  3. LAB-BASED — ingredient triggers known sensitivity from lab data → YELLOW
  4. CONDITION CONTRAINDICATION — ingredient contraindicated for patient condition → RED
  5. NO MATCH → GREEN

OUTPUT:
  - Signal: GREEN | YELLOW | RED
  - Warnings: List<Warning { ingredient, reason, severity, source }>
  - Alternatives: List<AlternativeDrug> (optional)
```

### 3.5 Audit & Compliance Layer

| Component | Responsibility |
|-----------|---------------|
| **Audit Log Service** | Log every prescription check (who, when, what, result) — immutable append-only |
| **Override Tracking** | If doctor overrides a RED warning, capture reason + digital signature |
| **Compliance Reporter** | Generate reports for regulatory bodies (HIPAA, NABH, etc.) |

---

## 4. Data Flow — End to End

```
Doctor selects patient
        │
        ▼
Doctor captures prescription photo  ──OR──  Types drug name
        │                                        │
        ▼                                        │
   OCR Service extracts text                     │
        │                                        │
        ▼                                        ▼
   Drug Name Resolver (fuzzy match to canonical names)
        │
        ▼
   Drug Ingredient Service → returns full ingredient list
        │
        ├──────────────────────────────────────────┐
        │                                          │
        ▼                                          ▼
   Patient Context Service              Ingredient Taxonomy
   (allergies, labs, conditions)        (cross-reactivity map)
        │                                          │
        └──────────────┬───────────────────────────┘
                       ▼
              Allergy Check Engine
                       │
                       ▼
              Signal + Warnings
                       │
                       ▼
              Doctor UI (Green / Yellow / Red)
                       │
                       ▼
              Audit Log (immutable record)
```

---

## 5. Non-Functional Requirements

| Requirement | Target | Approach |
|-------------|--------|----------|
| **Latency** | < 2 seconds end-to-end (manual entry), < 5 seconds (OCR) | Redis caching, pre-computed allergy profiles, async OCR |
| **Availability** | 99.9% uptime | Multi-AZ deployment, health checks, circuit breakers |
| **Scalability** | 10K+ concurrent doctors, 1M+ patients | Horizontal scaling via K8s, stateless services, DB read replicas |
| **Security** | HIPAA / GDPR compliant | Encryption at rest + transit, RBAC, audit logs, PHI tokenization |
| **Accuracy** | < 0.1% false negatives (missed allergies) | Conservative matching, cross-reactivity awareness, human override |
| **Interoperability** | Works with major EHR systems | FHIR R4, HL7v2 adapters, SMART on FHIR for auth |

---

## 6. Technology Stack (100% Open-Source)

| Layer | Technology | License | Cost |
|-------|-----------|---------|------|
| **Frontend** | Next.js (web) + Expo/React Native (mobile) | MIT | Free |
| **Reverse Proxy** | Caddy (auto-TLS) or Traefik | Apache 2.0 / MIT | Free |
| **Backend** | Python FastAPI — modular monolith | MIT | Free |
| **AI / OCR** | **MedGemma** (multimodal + text) via Ollama/vLLM + Tesseract fallback | Apache 2.0 | Free (self-hosted) |
| **Database** | PostgreSQL (primary) + Apache AGE (graph) + pg_trgm (search) | PostgreSQL / Apache 2.0 | Free |
| **Cache** | Valkey (Redis fork by Linux Foundation) | BSD-3 | Free |
| **Search** | PostgreSQL pg_trgm (or Meilisearch if needed) | PostgreSQL / MIT | Free |
| **EHR** | HAPI FHIR Server or OpenMRS | Apache 2.0 / MPL 2.0 | Free |
| **Auth** | Keycloak (OAuth 2.0 / OIDC / RBAC) | Apache 2.0 | Free |
| **Message Queue** | PostgreSQL LISTEN/NOTIFY (early) → RabbitMQ (scale) | PostgreSQL / MPL 2.0 | Free |
| **Orchestration** | Docker Compose (early) → K3s (scale) | Apache 2.0 | Free |
| **CI/CD** | GitHub Actions free tier (2000 mins/month) | — | Free |
| **Monitoring** | Prometheus + Grafana + Loki | Apache 2.0 / AGPL-3.0 | Free |
| **Secrets** | Infisical or SOPS | MIT / MPL 2.0 | Free |
| **Object Storage** | MinIO (S3-compatible, self-hosted) | AGPL-3.0 | Free |
| **Audit Storage** | Append-only PostgreSQL table | PostgreSQL | Free |

---

## 7. External Data Sources

| Source | What It Provides | Update Frequency |
|--------|-----------------|-----------------|
| **OpenFDA** | Drug labels, ingredients, adverse events | Weekly sync |
| **RxNorm (NLM)** | Drug name normalization, ingredient mappings | Monthly |
| **DailyMed** | SPL drug labels with full excipient lists | Weekly |
| **SNOMED CT** | Allergy/substance coding | Biannual |
| **LOINC** | Lab test coding (IgE panels, etc.) | Biannual |