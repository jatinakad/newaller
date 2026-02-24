# MedGuard — Architecture Documentation

> **Medicine Allergy Detection System** — Preventing allergic reactions by cross-referencing prescribed drug ingredients against patient allergy profiles in real-time.
>
> **100% Open-Source Stack · MedGemma-Powered · $0 to start · ~$24/month in production**

## Documents

| # | Document | Description |
|---|----------|-------------|
| 1 | [System Overview](./01-system-overview.md) | Problem statement, high-level architecture, core services, data flow, tech stack, external data sources |
| 2 | [Architecture Diagrams](./02-architecture-diagrams.md) | C4 context & container diagrams, sequence diagrams (photo + manual flows), deployment topology, override flow — all in Mermaid |
| 3 | [API Contracts & Data Models](./03-api-contracts-and-data-models.md) | TypeScript interfaces, REST API specs, FHIR integration queries, PostgreSQL schema |
| 4 | [Scalability, Security & Deployment](./04-scalability-security-deployment.md) | Scaling strategy, caching layers, HIPAA compliance, CI/CD pipeline, monitoring, disaster recovery, cost estimation |
| 5 | [Open-Source Strategy](./05-open-source-strategy.md) | **MedGemma integration, paid→OSS mapping, deployment phases ($0→$24→$200), hardware requirements, free data sources** |

## Quick Architecture Summary

```
Doctor (Photo / Text)
  → Caddy Reverse Proxy (auto-TLS)
    → FastAPI Backend (modular monolith)
      → MedGemma (OCR from photo, via Ollama/vLLM — self-hosted)
      → Drug Ingredient Service (OpenFDA / RxNorm — free APIs)
      → Patient Context Service (HAPI FHIR / OpenMRS — OSS)
        → Allergy Check Engine (deterministic rules + MedGemma reasoning)
          → GREEN / YELLOW / RED signal + warnings
            → Audit Log (PostgreSQL, immutable)
```

## Key Design Decisions

1. **100% open-source** — Every component is OSS or free-tier; no vendor lock-in, $0 to start
2. **MedGemma as AI core** — Replaces 4+ paid APIs (OCR, NLP, drug reasoning, alternatives) with one self-hosted model
3. **Modular monolith over microservices** — Single deployment, single VPS, easy to maintain as a solo/small team; split later when revenue comes
4. **PostgreSQL as Swiss Army knife** — Primary DB + graph (Apache AGE) + search (pg_trgm) + queue (LISTEN/NOTIFY) — fewer moving parts
5. **FHIR R4 for EHR integration** — Industry standard, works with HAPI FHIR Server, OpenMRS (both OSS)
6. **Conservative matching** — Deterministic rule engine is primary; MedGemma augments but never overrides safety signals
7. **Immutable audit trail** — Every check and override is permanently recorded for compliance
8. **Phased scaling** — Docker Compose ($0) → single VPS ($24) → K3s cluster ($200) as you grow

