# MedGuard — Architecture Diagrams

## 1. System Context Diagram (C4 Level 1)

```mermaid
C4Context
    title System Context — MedGuard

    Person(doctor, "Doctor", "Prescribes medicine to patients")
    Person(admin, "System Admin", "Manages drug DB, monitors system")

    System(medguard, "MedGuard", "Medicine Allergy Detection System")

    System_Ext(ehr, "EHR System", "HAPI FHIR Server / OpenMRS (OSS) — Patient records")
    System_Ext(openfda, "OpenFDA / RxNorm", "Drug ingredient data (free APIs)")
    System_Ext(lab, "Lab Information System", "Patient lab reports (IgE, skin prick)")
    System_Ext(medgemma, "MedGemma (self-hosted)", "Medical AI — OCR, reasoning, suggestions")

    Rel(doctor, medguard, "Submits prescription (photo/text), views allergy signals")
    Rel(admin, medguard, "Configures rules, monitors dashboards")
    Rel(medguard, ehr, "Fetches patient allergies & conditions via FHIR R4")
    Rel(medguard, openfda, "Resolves drug → ingredients")
    Rel(medguard, lab, "Pulls allergy-related lab markers")
    Rel(medguard, medgemma, "OCR, drug reasoning, alternative suggestions")
```

---

## 2. Container Diagram (C4 Level 2)

```mermaid
C4Container
    title Container Diagram — MedGuard

    Person(doctor, "Doctor")

    Container_Boundary(frontend, "Frontend") {
        Container(webapp, "Web Application", "React", "Prescription entry, patient selection, allergy signals")
        Container(mobileapp, "Mobile App", "React Native", "Camera capture, on-the-go prescribing")
    }

    Container_Boundary(backend, "Backend Services") {
        Container(gateway, "Reverse Proxy", "Caddy (OSS)", "Auto-TLS, rate limiting, routing")
        Container(auth, "Auth Server", "Keycloak (OSS)", "OAuth 2.0, OIDC, RBAC")
        Container(ocr_svc, "OCR Module", "Python / FastAPI", "MedGemma multimodal + Tesseract fallback")
        Container(rx_svc, "Prescription Module", "Python / FastAPI", "Drug name resolution, autocomplete")
        Container(drug_svc, "Drug Ingredient Module", "Python / FastAPI", "Drug → ingredient lookup")
        Container(patient_svc, "Patient Context Module", "Python / FastAPI", "EHR integration, allergy profile")
        Container(engine, "Allergy Check Engine", "Python / FastAPI", "Rules + MedGemma reasoning")
        Container(audit_svc, "Audit Module", "Python / FastAPI", "Immutable logging")
        Container(notify_svc, "Notification Module", "Python / FastAPI", "Alerts for critical overrides")
        Container(medgemma_svc, "MedGemma Server", "Ollama / vLLM (OSS)", "Medical AI model serving")
    }

    Container_Boundary(data, "Data Stores") {
        ContainerDb(pg, "PostgreSQL + AGE", "Primary DB + Graph", "Drugs, ingredients, audit logs, cross-reactivity graph")
        ContainerDb(redis, "Valkey", "Cache (OSS Redis fork)", "Allergy profiles, drug lookups")
        ContainerDb(s3, "MinIO", "Object Storage (OSS)", "Prescription images")
    }

    Container_Boundary(async, "Async Processing") {
        Container(queue, "Task Queue", "PG LISTEN/NOTIFY", "OCR job queue (RabbitMQ at scale)")
        Container(sync_worker, "Drug DB Sync", "Python cron", "Periodic FDA data sync")
    }

    Rel(doctor, webapp, "Uses")
    Rel(doctor, mobileapp, "Uses")
    Rel(webapp, gateway, "HTTPS")
    Rel(mobileapp, gateway, "HTTPS")
    Rel(gateway, ocr_svc, "Routes")
    Rel(gateway, rx_svc, "Routes")
    Rel(gateway, patient_svc, "Routes")
    Rel(ocr_svc, queue, "Publishes OCR jobs")
    Rel(ocr_svc, s3, "Stores images")
    Rel(rx_svc, pg, "Fuzzy search via pg_trgm")
    Rel(rx_svc, drug_svc, "Resolves ingredients")
    Rel(drug_svc, pg, "Reads + graph queries via AGE")
    Rel(drug_svc, redis, "Cache")
    Rel(patient_svc, pg, "Reads")
    Rel(patient_svc, redis, "Cache")
    Rel(ocr_svc, medgemma_svc, "Medical OCR inference")
    Rel(engine, medgemma_svc, "Cross-reactivity reasoning + alternatives")
    Rel(engine, drug_svc, "Gets ingredients")
    Rel(engine, patient_svc, "Gets allergy profile")
    Rel(engine, audit_svc, "Logs result")
    Rel(sync_worker, pg, "Writes drug data")
```

---

## 3. Sequence Diagram — Prescription Check (Photo Flow)

```mermaid
sequenceDiagram
    actor Doctor
    participant UI as Doctor UI
    participant GW as API Gateway
    participant OCR as OCR Service
    participant S3 as Object Storage
    participant RX as Prescription Service
    participant DRUG as Drug Ingredient Service
    participant PAT as Patient Context Service
    participant EHR as External EHR (HAPI FHIR / OpenMRS)
    participant ENGINE as Allergy Check Engine
    participant GEMMA as MedGemma (self-hosted)
    participant AUDIT as Audit Service

    Doctor->>UI: Select patient + capture prescription photo
    UI->>GW: POST /api/v1/prescription/check {patientId, image}
    GW->>GW: Authenticate (OAuth 2.0 / SMART on FHIR)

    par Upload image & Start OCR
        GW->>S3: Store prescription image
        GW->>OCR: Extract drug names from image
        OCR->>OCR: MedGemma multimodal + Tesseract fallback
        OCR-->>GW: Extracted text: ["Amoxicillin 500mg", "Cetrizine 10mg"]
    and Fetch Patient Data
        GW->>PAT: GET /patient/{id}/allergy-profile
        PAT->>EHR: FHIR GET /AllergyIntolerance?patient={id}
        EHR-->>PAT: Known allergies: [Penicillin, Sulfa]
        PAT->>EHR: FHIR GET /Observation?patient={id}&category=laboratory
        EHR-->>PAT: Lab flags: [elevated IgE for Cephalosporins]
        PAT-->>GW: AllergyProfile { allergens, labFlags, conditions }
    end

    GW->>RX: Resolve drug names
    RX->>RX: pg_trgm fuzzy match "Amoxicillin 500mg"
    RX->>RX: Canonical: {rxcui: 723, name: "Amoxicillin"}
    RX->>DRUG: GET /drug/723/ingredients
    DRUG-->>RX: Ingredients: [Amoxicillin (Penicillin-class), Magnesium Stearate, ...]

    RX->>ENGINE: Check allergies
    ENGINE->>ENGINE: Direct match: Amoxicillin → Penicillin-class
    ENGINE->>ENGINE: Apache AGE graph query: cross-reactivity(Penicillin)
    ENGINE->>GEMMA: Verify cross-reactivity + suggest alternatives
    GEMMA-->>ENGINE: Cross-reactive with: [Ampicillin, Cephalosporins (partial)], Alternatives: [Azithromycin]

    ENGINE->>ENGINE: RESULT = RED for Amoxicillin
    ENGINE->>ENGINE: Cetrizine → No matches → GREEN

    ENGINE->>AUDIT: Log check result
    ENGINE-->>GW: Response

    GW-->>UI: {signal: RED, warnings: [{drug: "Amoxicillin", reason: "Contains Penicillin-class ingredient. Patient allergic to Penicillin.", severity: "CRITICAL", alternatives: ["Azithromycin", "Levofloxacin"]}], safe: [{drug: "Cetrizine", signal: GREEN}]}

    UI->>Doctor: 🔴 RED — Amoxicillin blocked (Penicillin allergy) + alternatives shown
    UI->>Doctor: ✅ GREEN — Cetrizine safe
```

---

## 4. Sequence Diagram — Manual Entry Flow

```mermaid
sequenceDiagram
    actor Doctor
    participant UI as Doctor UI
    participant GW as API Gateway
    participant RX as Prescription Service
    participant DRUG as Drug Ingredient Service
    participant PAT as Patient Context Service
    participant ENGINE as Allergy Check Engine
    participant AUDIT as Audit Service

    Doctor->>UI: Select patient
    Doctor->>UI: Start typing "Amox..."
    UI->>GW: GET /api/v1/drugs/search?q=Amox
    GW->>RX: Autocomplete search
    RX->>RX: PostgreSQL pg_trgm search "Amox%"
    RX-->>RX: [Amoxicillin 250mg, Amoxicillin 500mg, Amoxicillin-Clavulanate]
    RX-->>UI: Drug suggestions

    Doctor->>UI: Select "Amoxicillin 500mg"
    UI->>GW: POST /api/v1/prescription/check {patientId, drugs: [{rxcui: 723}]}

    par Fetch Ingredients & Patient Data
        GW->>DRUG: GET /drug/723/ingredients
        DRUG-->>GW: Ingredients list
    and
        GW->>PAT: GET /patient/{id}/allergy-profile
        PAT-->>GW: Allergy profile
    end

    GW->>ENGINE: Check allergies (ingredients × profile)
    ENGINE-->>GW: Signal + Warnings
    ENGINE->>AUDIT: Log result

    GW-->>UI: Result with signal + warnings
    UI->>Doctor: Display RED/YELLOW/GREEN signal
```

---

## 5. Deployment Architecture

```mermaid
graph TB
    subgraph "CDN / Edge"
        CF[Cloudflare Free Tier]
    end

    subgraph "Reverse Proxy"
        CADDY[Caddy - Auto TLS]
    end

    subgraph "K3s Cluster or Docker Compose"
        subgraph "App Services"
            APP[FastAPI App - modular monolith]
            KC[Keycloak - Auth]
        end
        subgraph "AI Services"
            GEMMA[MedGemma via Ollama/vLLM]
        end
    end

    subgraph "Data Layer - all OSS"
        PG[(PostgreSQL + AGE + pg_trgm)]
        VALKEY[(Valkey - cache)]
        MINIO[(MinIO - images)]
    end

    subgraph "Async"
        PGNOTIFY[PG LISTEN/NOTIFY]
        SYNC[Drug Sync CronJob]
    end

    subgraph "Observability - all OSS"
        PROM[Prometheus]
        GRAF[Grafana]
        LOKI[Grafana Loki]
    end

    CF --> CADDY
    CADDY --> APP
    CADDY --> KC
    APP --> GEMMA
    APP --> PG
    APP --> VALKEY
    APP --> MINIO
    APP --> PGNOTIFY
    SYNC --> PG

    APP --> PROM
    GEMMA --> PROM
    PROM --> GRAF
    APP --> LOKI
```

---

## 6. Doctor Override Flow

```mermaid
sequenceDiagram
    actor Doctor
    participant UI as Doctor UI
    participant GW as API Gateway
    participant AUDIT as Audit Service
    participant NOTIFY as Notification Service

    Note over Doctor, UI: Doctor sees RED signal but wants to proceed

    Doctor->>UI: Click "Override & Prescribe Anyway"
    UI->>UI: Show mandatory override form
    Doctor->>UI: Enter clinical justification + digital signature
    UI->>GW: POST /api/v1/prescription/override {prescriptionId, reason, signature}
    GW->>AUDIT: Log override with full context (immutable)
    GW->>NOTIFY: Alert pharmacy + supervising physician
    NOTIFY-->>Doctor: Confirmation: Override recorded
    GW-->>UI: Prescription finalized with override flag

    Note over AUDIT: Override record is immutable and auditable
```