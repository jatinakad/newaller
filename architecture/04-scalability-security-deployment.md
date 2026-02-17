# MedGuard — Scalability, Security & Deployment Strategy

## 1. Scalability Strategy

### 1.1 Horizontal Scaling by Service

**Early Stage (Docker Compose on single VPS):** No horizontal scaling needed. Single FastAPI process with Uvicorn workers handles ~50-100 concurrent doctors.

**Growth Stage (K3s cluster):**

| Service | Scaling Trigger | Min Pods | Max Pods | Notes |
|---------|----------------|----------|----------|-------|
| FastAPI App | CPU > 60% or RPS > 300/pod | 2 | 6 | Modular monolith, stateless |
| MedGemma (Ollama/vLLM) | Queue depth > 10 | 1 | 3 | GPU-backed if available, CPU fallback |
| Keycloak | CPU > 70% | 1 | 3 | Auth server |
| Drug Sync Worker | Scheduled | 1 | 1 | Cron job, not always running |

### 1.2 Caching Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    CACHE LAYERS                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  L1: In-Memory (per pod)                                   │
│  ├── Drug ingredient lookups (LRU, 10K entries, 5 min TTL) │
│  └── Cross-reactivity groups (full set, 1 hour TTL)        │
│                                                             │
│  L2: Valkey (OSS Redis fork)                                │
│  ├── Patient allergy profiles (TTL: 15 min)                │
│  ├── Drug → ingredient mappings (TTL: 24 hours)            │
│  ├── Drug search results (TTL: 1 hour)                     │
│  └── OCR result cache by image hash (TTL: 7 days)          │
│                                                             │
│  L3: PostgreSQL (single instance, read replicas at scale)   │
│  └── Full drug database, audit logs, pg_trgm search        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Cache Invalidation:**
- Drug data: Invalidate on sync worker completion (event-driven via PG LISTEN/NOTIFY)
- Patient profiles: Short TTL (15 min) + explicit invalidation on EHR webhook updates
- Cross-reactivity: Invalidate on admin updates

### 1.3 Database Scaling

| Database | Read Strategy | Write Strategy | Partitioning |
|----------|--------------|----------------|--------------|
| PostgreSQL + AGE | Single instance (early) → 1 read replica (scale) + PgBouncer | Single primary | Audit logs partitioned by month |
| Valkey | Single instance (early) → Sentinel (scale) | Same instance | Key-prefix based |
| pg_trgm (in PostgreSQL) | Same as PostgreSQL | Same as PostgreSQL | GIN indexes |

### 1.4 Async Processing

```
Photo Upload Flow (async):
  Doctor uploads photo
    → API returns requestId immediately (202 Accepted)
    → Image stored in MinIO (self-hosted S3)
    → OCR job published via PG LISTEN/NOTIFY (RabbitMQ at scale)
    → OCR worker processes image
    → Result published to "ocr.complete" exchange
    → Prescription Service picks up, runs allergy check
    → Result pushed to Doctor UI via WebSocket / SSE

Manual Entry Flow (sync):
  Doctor submits drug list
    → Synchronous processing (< 2 sec target)
    → Direct response with allergy check result
```

---

## 2. Security & Compliance

### 2.1 Authentication & Authorization

```
┌──────────────────────────────────────────────────┐
│              AUTH FLOW                            │
│                                                  │
│  Doctor → Keycloak Login (OSS)                    │
│    → OAuth 2.0 Authorization Code + PKCE         │
│    → JWT Access Token (short-lived: 15 min)      │
│    → Refresh Token (long-lived: 8 hours)         │
│                                                  │
│  Token Claims:                                   │
│    - sub: doctor ID                              │
│    - facility: facility ID                       │
│    - scope: patient/*.read, prescription.check   │
│    - patient: current patient context (SMART)    │
│                                                  │
│  RBAC Roles:                                     │
│    - DOCTOR: check prescriptions, view profiles  │
│    - PHARMACIST: view checks, flag issues        │
│    - ADMIN: manage drug DB, view audit logs      │
│    - SUPER_ADMIN: manage users, system config    │
└──────────────────────────────────────────────────┘
```

### 2.2 Data Protection

| Layer | Protection | Implementation |
|-------|-----------|----------------|
| **In Transit** | TLS 1.3 everywhere | Caddy auto-TLS (Let's Encrypt) |
| **At Rest** | AES-256 encryption | PostgreSQL pgcrypto + LUKS disk encryption |
| **PHI Fields** | Tokenization | Patient name, DOB tokenized; de-tokenize only at display |
| **Prescription Images** | Encrypted + auto-expiry | MinIO with server-side encryption + lifecycle policy (delete after 90 days) |
| **Audit Logs** | Immutable, encrypted | Append-only table, no UPDATE/DELETE permissions |
| **API Keys** | Vault-managed | **Infisical** (OSS) or **SOPS** (encrypted files) |

### 2.3 HIPAA Compliance Checklist

- [x] **Access Controls** — RBAC + SMART on FHIR scoping
- [x] **Audit Trail** — Every access and check logged immutably
- [x] **Encryption** — At rest (AES-256) and in transit (TLS 1.3)
- [x] **Minimum Necessary** — Only allergy-relevant data fetched from EHR
- [x] **BAA** — Business Associate Agreements with cloud provider + EHR vendor
- [x] **Breach Notification** — Automated alerting on anomalous access patterns
- [x] **Data Retention** — Configurable retention policies, auto-purge of images
- [x] **De-identification** — PHI tokenized in non-production environments

### 2.4 Network Security

```
┌─────────────────────────────────────────────────────────┐
│                  NETWORK TOPOLOGY                       │
│                                                         │
│  Internet                                               │
│    │                                                    │
│    ▼                                                    │
│  Cloudflare Free Tier — DNS + basic DDoS protection    │
│    │                                                    │
│    ▼                                                    │
│  Caddy Reverse Proxy (auto-TLS via Let's Encrypt)       │
│    │                                                    │
│  VPS (single server or K3s cluster)                     │
│    ├── FastAPI app (Docker container)                   │
│    ├── Keycloak (Docker container)                      │
│    ├── MedGemma / Ollama (Docker container)             │
│    ├── UFW firewall: only 80/443 exposed               │
│    │                                                    │
│  Data (Docker volumes, same VPS or dedicated)           │
│    ├── PostgreSQL (port 5432, localhost only)            │
│    ├── Valkey (port 6379, localhost only)                │
│    └── MinIO (port 9000, localhost only)                 │
│                                                         │
│  EHR Connection                                         │
│    └── HAPI FHIR Server (same VPS or WireGuard VPN)     │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Deployment Strategy

### 3.1 CI/CD Pipeline

```
Code Push (GitHub)
    │
    ▼
GitHub Actions (free tier: 2000 mins/month)
    │
    ├── 1. Lint + Type Check (ruff, mypy)
    ├── 2. Unit Tests (pytest)
    ├── 3. Integration Tests (Testcontainers)
    ├── 4. SAST Scan (Semgrep — OSS)
    ├── 5. Container Build (Docker)
    ├── 6. Container Scan (Trivy — OSS)
    ├── 7. Push to GitHub Container Registry (free for public)
    ├── 8. Deploy to VPS via SSH (or K3s via kubectl)
    ├── 9. Smoke Tests on Staging
    └── 10. Promote to Production (manual approval gate)
```

### 3.2 Deployment Model

```
Blue-Green Deployment:
  ┌─────────────┐     ┌─────────────┐
  │  BLUE (v1)  │     │ GREEN (v2)  │
  │  (current)  │     │  (new)      │
  └──────┬──────┘     └──────┬──────┘
         │                    │
         └────────┬───────────┘
                  │
            Load Balancer
            (traffic shift: 0% → 10% → 50% → 100%)

  Rollback: Instant switch back to Blue
```

### 3.3 Environment Strategy

| Environment | Purpose | Data |
|-------------|---------|------|
| **Local** | Developer machines | Mock EHR, sample drug DB |
| **Dev** | Integration testing | Shared dev EHR sandbox |
| **Staging** | Pre-production validation | Anonymized production data |
| **Production** | Live system | Real EHR, real drug data |

### 3.4 Infrastructure as Code

```
Repository Structure (simplified for OSS stack):
  medguard/
  ├── app/                          # FastAPI modular monolith
  │   ├── main.py
  │   ├── api/
  │   ├── core/
  │   ├── models/
  │   └── db/
  ├── docker/
  │   ├── Dockerfile                    # FastAPI app
  │   ├── docker-compose.yml            # Full local stack
  │   ├── docker-compose.prod.yml       # Production overrides
  │   ├── Caddyfile                     # Reverse proxy config
  │   └── keycloak/
  │       └── realm-export.json         # Pre-configured realm
  ├── k3s/                              # K3s manifests (growth stage)
  │   ├── app-deployment.yaml
  │   ├── medgemma-deployment.yaml
  │   ├── postgres-statefulset.yaml
  │   ├── valkey-deployment.yaml
  │   └── monitoring/
  │       ├── prometheus.yaml
  │       ├── grafana.yaml
  │       └── loki.yaml
  ├── scripts/
  │   ├── seed_drug_db.py               # OpenFDA / RxNorm data import
  │   ├── sync_drugs.py                 # Periodic drug data sync
  │   └── setup_vps.sh                  # One-command VPS setup
  ├── tests/
  ├── requirements.txt
  └── README.md
```

---

## 4. Monitoring & Observability

### 4.1 Key Metrics (Prometheus + Grafana)

| Metric | Alert Threshold | Severity |
|--------|----------------|----------|
| `allergy_check_latency_p99` | > 3 seconds | WARNING |
| `allergy_check_latency_p99` | > 5 seconds | CRITICAL |
| `ocr_extraction_failure_rate` | > 10% over 5 min | WARNING |
| `ehr_connection_errors` | > 5 in 1 min | CRITICAL |
| `false_negative_reports` | Any | CRITICAL (manual review) |
| `red_signal_override_rate` | > 20% over 1 hour | WARNING |
| `drug_db_sync_age` | > 48 hours | WARNING |
| `cache_hit_ratio` | < 70% | WARNING |

### 4.2 Distributed Tracing

```
Every request gets a correlation ID (X-Request-Id) that flows through:
  API Gateway → OCR → Prescription → Drug → Patient → Engine → Audit

Tracing: OpenTelemetry → Jaeger (OSS)
Logging: Structured JSON → Promtail → Grafana Loki (OSS)
```

### 4.3 Health Checks

```
GET /health          → Basic liveness (K8s liveness probe)
GET /health/ready    → Readiness (DB + cache + EHR connectivity)
GET /health/detailed → Full dependency check (admin only)
```

---

## 5. Disaster Recovery

| Scenario | RTO | RPO | Strategy |
|----------|-----|-----|----------|
| Single pod failure | 0 sec | 0 | K8s auto-restart, multiple replicas |
| VPS failure | < 15 min | < 5 min | DNS failover to standby VPS, PG streaming replication |
| Provider failure | < 30 min | < 5 min | Backup VPS on different provider (Hetzner ↔ DigitalOcean) |
| EHR system down | 0 sec | 15 min | Serve from cached allergy profiles + stale warning |
| Drug DB corruption | < 1 hour | 24 hours | Daily automated backups, point-in-time recovery |

---

## 6. Cost Estimation (100% Open-Source)

### Phase 1: MVP (~$0/month)
| Component | Spec | Monthly Cost |
|-----------|------|-------------|
| Development | Your laptop / desktop | $0 |
| GitHub | Free tier (public or private repo) | $0 |
| Cloudflare | Free tier (DNS + basic DDoS) | $0 |
| **Total** | | **$0** |

### Phase 2: Beta (~$24-50/month)
| Component | Spec | Monthly Cost |
|-----------|------|-------------|
| VPS (Hetzner CX32) | 4 vCPU, 8 GB RAM, 80 GB SSD | $7-24 |
| Domain name | .com or .health | ~$1/month amortized |
| Cloudflare Free | DNS + CDN + basic DDoS | $0 |
| GitHub Actions | 2000 free mins/month | $0 |
| All software | OSS (PostgreSQL, Valkey, Caddy, Keycloak, Ollama, MedGemma) | $0 |
| **Total** | | **~$8-25/month** |

### Phase 3: Growth (~$100-200/month)
| Component | Spec | Monthly Cost |
|-----------|------|-------------|
| App VPS (Hetzner CX42) | 8 vCPU, 16 GB RAM | ~$35 |
| GPU VPS (Hetzner/RunPod) | For MedGemma 27b | ~$80-150 |
| Backup storage | Hetzner Storage Box 100GB | ~$4 |
| **Total** | | **~$120-190/month** |

*Compare to paid cloud stack: ~$2,600+/month. **Savings: 92-99%***
