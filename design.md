# AllerSense - Design Document

## 1. System Architecture Overview

AllerSense is a full-stack web application built with a modern, scalable architecture.

### 1.1 High-Level Architecture

```
Frontend (Next.js) → Backend (FastAPI) → Database (PostgreSQL)
                                       → Cache (Redis)
                                       → AI (Gemini)
                                       → Storage (S3)
```

### 1.2 Architecture Principles

1. AI-First Approach: Gemini AI is the primary intelligence layer
2. Modular Monolith: Single deployable backend with clear service boundaries
3. Stateless Services: All state in database/cache for horizontal scaling
4. Graceful Degradation: System works even if AI or cache unavailable
5. Audit Everything: Immutable logs for compliance

## 2. Technology Stack

### 2.1 Frontend
- Framework: Next.js 16.1.6 (React 18.3.1)
- Language: TypeScript 5.7.2
- Styling: TailwindCSS 3.4.17
- Icons: Lucide React

### 2.2 Backend
- Framework: FastAPI (Python 3.11+)
- ORM: SQLAlchemy 2.0 (async)
- Validation: Pydantic v2
- Logging: structlog
- Server: Uvicorn

### 2.3 Data Layer
- Primary Database: PostgreSQL 16+
- Extensions: pg_trgm (fuzzy search)
- Cache: Redis/Valkey
- Object Storage: AWS S3

### 2.4 AI/ML
- Primary: Google Gemini 2.5 Flash / AWS bedrock
- Alternatives: Ollama, HuggingFace
- Capabilities: Vision (OCR), text analysis, reasoning

### 2.5 Infrastructure
- Deployment: AWS ECS Fargate
- Load Balancer: Application Load Balancer
- Database: RDS PostgreSQL with SSL
- Storage: S3 with encryption


## 3. Data Models

### 3.1 Patient Domain

**Patient Table:**
- id: UUID (primary key)
- external_id: String (unique, indexed) - e.g., "P-5678"
- name: String
- age: Integer
- gender: String
- weight_kg: Float
- created_at, updated_at: DateTime

**PatientAllergy Table:**
- id: UUID (primary key)
- patient_id: UUID (foreign key)
- allergen_code: String (SNOMED CT)
- allergen_name: String
- category: String (drug/food/environment/biologic)
- criticality: String (low/high/unable-to-assess)
- reaction_manifestations: Array[String]
- reaction_severity: String (mild/moderate/severe)
- verification_status: String
- recorded_date, created_at: DateTime

**LabSensitivity Table:**
- id: UUID (primary key)
- patient_id: UUID (foreign key)
- test_code: String (LOINC)
- test_name: String
- value: Float
- unit: String
- reference_range: String
- interpretation: String (normal/elevated/high)
- related_substances: Array[String]
- report_date, created_at: DateTime

**PatientCondition Table:**
- id: UUID (primary key)
- patient_id: UUID (foreign key)
- condition_code: String (ICD-10/SNOMED)
- condition_name: String
- contraindicated_ingredients: Array[String]
- created_at: DateTime

### 3.2 Drug Domain

**Drug Table:**
- id: UUID (primary key)
- rxcui: String (unique, indexed)
- name: String (pg_trgm indexed)
- generic_name: String (pg_trgm indexed)
- dosage_form: String
- route: String
- brand_names: Array[String]
- ndc_codes: Array[String]
- source: String
- last_synced_at, created_at: DateTime

**Ingredient Table:**
- id: UUID (primary key)
- name: String (unique)
- chemical_family: String
- allergen_codes: Array[String]
- created_at: DateTime

**DrugIngredient Table (junction):**
- id: UUID (primary key)
- drug_id: UUID (foreign key)
- ingredient_id: UUID (foreign key)
- type: String (active/inactive/excipient)
- strength: String

**CrossReactivityGroup Table:**
- id: UUID (primary key)
- group_name: String (unique)

**CrossReactivityMember Table:**
- id: UUID (primary key)
- group_id: UUID (foreign key)
- ingredient_id: UUID (foreign key)
- probability: String (high/moderate/low)

### 3.3 Report Domain

**PatientReport Table:**
- id: UUID (primary key)
- patient_id: UUID (foreign key)
- filename: String
- file_path: String
- file_size: Integer
- content_type: String
- extracted_text: Text
- structured_data: JSONB (medications, labs, diagnoses, etc.)
- status: String (pending/extracting/ready/failed)
- version: Integer
- superseded_by: UUID (foreign key, self-reference)
- is_latest: Boolean
- uploaded_at, extracted_at: DateTime

### 3.4 Audit Domain

**AuditLog Table:**
- id: UUID (primary key)
- timestamp: DateTime (indexed, partitioned by month)
- event_type: String
- doctor_id: String (indexed)
- patient_id: String (indexed)
- facility_id: String
- request_id: UUID
- overall_signal: String
- drug_results: JSONB
- processing_ms: Integer
- ip_address: INET
- user_agent: Text

**AuditOverride Table:**
- id: UUID (primary key)
- audit_id: UUID (foreign key)
- overridden_warnings: Array[String]
- justification: Text
- digital_signature: Text
- witness_id: String
- created_at: DateTime


## 4. API Design

### 4.1 Base URL Structure

Base URL: `http://api.allersense.com/api/v1`

All endpoints return JSON. Authentication via JWT in production.

### 4.2 Endpoint Catalog

**Patient Endpoints:**
- POST /patients - Create patient
- GET /patients/{id}/allergy-profile - Get full allergy profile
- POST /patients/{id}/allergies - Add allergy
- POST /patients/{id}/conditions - Add condition
- POST /patients/{id}/lab-sensitivities - Add lab sensitivity
- GET /patients/{id}/reports - List reports
- POST /patients/{id}/reports - Upload report
- PUT /patients/{id}/reports/{report_id} - Replace report

**Prescription Endpoints:**
- POST /prescription/check - Manual drug check
- POST /prescription/check/photo - Photo OCR + check
- POST /prescription/override - Override RED warning

**Drug Endpoints:**
- GET /drugs/search?q={query}&limit=10 - Fuzzy drug search
- GET /drugs/{rxcui}/ingredients - Get drug ingredients

**Chat Endpoint:**
- POST /chat - AI conversational query

**Health Endpoints:**
- GET /health - Basic liveness
- GET /health/ready - Readiness (DB + cache)

### 4.3 Key Request/Response Examples

**Prescription Check Request:**
```json
{
  "patient_id": "P-5678",
  "facility_id": "F-100",
  "drugs": [
    {"name": "Amoxicillin"},
    {"rxcui": "18631"}
  ]
}
```

**Prescription Check Response:**
```json
{
  "request_id": "uuid",
  "patient_id": "P-5678",
  "overall_signal": "RED",
  "drug_results": [
    {
      "drug": {"rxcui": "", "name": "Amoxicillin"},
      "signal": "RED",
      "reasoning": "Detailed clinical reasoning...",
      "warnings": [
        {
          "warning_id": "W-abc123",
          "severity": "CRITICAL",
          "type": "DIRECT_MATCH",
          "ingredient": "Amoxicillin Trihydrate",
          "allergen": "Penicillin",
          "message": "Direct allergen match detected",
          "reasoning": "Clinical explanation...",
          "evidence": {
            "source": "AI_ANALYSIS",
            "detail": "Gemini AI analysis"
          }
        }
      ],
      "alternatives": [
        {
          "rxcui": "18631",
          "name": "Azithromycin",
          "reason": "Macrolide antibiotic, no cross-reactivity",
          "signal": "GREEN"
        }
      ]
    }
  ],
  "processing_time_ms": 3200,
  "citations": [
    {
      "source": "OpenFDA",
      "url": "https://api.fda.gov/..."
    }
  ]
}
```


## 5. Core Services Architecture

### 5.1 Service Layer Organization

```
app/
├── api/routes/          # HTTP endpoint handlers
│   ├── prescription.py  # Prescription check endpoints
│   ├── drugs.py         # Drug search endpoints
│   ├── patients.py      # Patient CRUD endpoints
│   ├── reports.py       # Report upload/management
│   └── chat.py          # AI chat endpoint
├── core/                # Business logic (no HTTP concerns)
│   ├── allergy_engine.py      # Main allergy checking logic
│   ├── ai_service.py          # AI abstraction layer
│   ├── ai_backends/           # Pluggable AI providers
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── gemini_backend.py
│   │   ├── ollama_backend.py
│   │   ├── huggingface_local_backend.py
│   │   └── huggingface_api_backend.py
│   ├── drug_service.py        # Drug database queries
│   ├── patient_service.py     # Patient data queries
│   ├── report_service.py      # Report processing
│   ├── audit_service.py       # Audit logging
│   ├── chat_service.py        # AI chat logic
│   └── web_search.py          # OpenFDA/DailyMed integration
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response models
├── db/
│   ├── session.py      # Database connection
│   └── redis.py        # Redis client
├── config.py           # Environment configuration
└── main.py             # FastAPI app initialization
```

### 5.2 Allergy Engine Design

The allergy engine is the core business logic component.

**Workflow:**
1. Fetch patient profile (allergies, conditions, labs)
2. Fetch patient report text
3. Send everything to AI for comprehensive analysis
4. If AI needs verification, fetch from OpenFDA/DailyMed
5. Retry AI analysis with enhanced drug data
6. Parse AI results into structured warnings
7. Determine overall signal (RED/YELLOW/GREEN)
8. Return results with citations

**Key Design Decisions:**
- AI-first: Gemini analyzes everything in one call
- Verification loop: AI can request additional drug data
- Structured output: AI returns JSON with signals, warnings, alternatives
- Detailed reasoning: Every decision includes clinical explanation
- Citation tracking: All external data sources are cited

### 5.3 AI Service Architecture

Pluggable AI backend system using abstract base class:

**AIBackend Interface:**
- name: Property returning backend name
- supports_vision: Property indicating vision/OCR capability
- chat(messages, temperature, max_tokens): Text-only inference
- chat_with_image(prompt, image_b64, ...): Vision inference

**Supported Backends:**
1. Gemini (default): Google's multimodal AI, supports vision
2. Ollama: Local model server, supports vision with multimodal models
3. HuggingFace API: Cloud inference, limited vision support
4. HuggingFace Local: Run models locally, requires GPU

**Backend Selection:**
- Configured via AI_BACKEND environment variable
- Factory pattern for instantiation
- Graceful fallback if backend unavailable

### 5.4 Report Processing Pipeline

```
Upload → Store File → Extract Text → Structure Data → Update Status
   │         │            │              │              │
   S3      Database    Gemini AI     Gemini AI      Database
```

**Extraction Process:**
1. File uploaded to S3/MinIO
2. Metadata stored in database (status: pending)
3. AI extracts text from PDF/image
4. AI structures text into JSON (medications, labs, diagnoses)
5. Structured data stored in JSONB column
6. Status updated to "ready"

**Structured Data Schema:**
- document_type: String
- patient_info: Object (name, ID, age, gender, DOB)
- medications: Array[Object] (name, dosage, frequency, route)
- lab_results: Array[Object] (test_name, value, unit, reference_range)
- diagnoses: Array[Object] (condition, icd_code, status)
- allergies_mentioned: Array[String]
- vitals: Array[Object] (name, value, unit)
- clinical_notes: String

### 5.5 Caching Strategy

**Redis Cache Layers:**

L1: Patient Allergy Profiles (TTL: 15 min)
- Key: patient:{external_id}:profile
- Invalidated on allergy/condition/lab update

L2: Drug Search Results (TTL: 1 hour)
- Key: drug:search:{query}
- Time-based expiration only

L3: Drug Ingredients (TTL: 24 hours)
- Key: drug:{rxcui}:ingredients
- Invalidated on drug database sync

**Fallback Behavior:**
- If Redis unavailable, queries go directly to PostgreSQL
- System remains functional without cache
- Performance degrades but no data loss


## 6. AI Integration Design

### 6.1 Gemini AI Prompting Strategy

**System Prompt:**
```
You are a clinical pharmacology expert and allergy specialist.
Your job is to check prescribed medicines against a patient's 
allergy profile for safety. You must check ALL ingredients — 
both active AND inactive/excipients. You must also check for 
cross-reactivity between drug families. Be thorough but precise.
Only flag real clinical risks, not theoretical ones.

IMPORTANT: For each drug AND each warning, provide detailed 
'reasoning' that explains your clinical rationale step-by-step.
```

**User Prompt Structure:**
```
PATIENT ALLERGIES:
- Penicillin (criticality: high) — reactions: Anaphylaxis — severity: severe

PATIENT CONDITIONS:
- G6PD Deficiency (avoid: Dapsone, Primaquine)

PATIENT LAB VALUES:
- Specific IgE - Cephalosporin: 1.2 kU/L (elevated) [ref: < 0.35]

PATIENT REPORT EXCERPTS:
[Truncated report text...]

DRUG REFERENCE DATA (from FDA/DailyMed):
[Optional: fetched if AI requests verification]

PRESCRIBED MED image. Return ONLY a JSON object with this exact format: {\"drugs\": [{\"name\": \"...\", \"dosage\": \"...\", \"form\": \"...\"}], \"confidence\": 0.0 to 1.0}"

**Confidence Thresholds:**
- < 0.3: Reject, ask for clearer image
- 0.3 - 0.7: Accept with warning
- > 0.7: Accept confidently

### 6.3 Report Text Extraction

**PDF/Image → Structured Data:**

Prompt: "Extract structured medical information from this document. Return JSON with: document_type, patient_info, medications, lab_results, diagnoses, allergies_mentioned, vitals, clinical_notes. Be thorough but only extract information that is clearly stated."

### 6.4 Web-Enhanced Drug Information

**Verification Workflow:**
1. AI returns needs_verification list
2. System fetches drug info from OpenFDA/DailyMed
3. Extracts ingredient lists and contraindications
4. Builds enhanced context string
5. Retries AI analysis with additional data
6. Returns citations for all sources

**Citation Format:**
```json
{
  "source": "OpenFDA Drug Label",
  "url": "https://api.fda.gov/drug/label.json?..."
}
```


## 7. Database Design

### 7.1 Indexing Strategy

**Performance-Critical Indexes:**

```sql
-- Fuzzy search (pg_trgm extension)
CREATE INDEX idx_drugs_name_trgm ON drugs 
  USING gin (name gin_trgm_ops);
CREATE INDEX idx_drugs_generic_trgm ON drugs 
  USING gin (generic_name gin_trgm_ops);

-- Foreign key lookups
CREATE INDEX idx_patient_allergies_patient ON patient_allergies(patient_id);
CREATE INDEX idx_drug_ingredients_drug ON drug_ingredients(drug_id);
CREATE INDEX idx_drug_ingredients_ingredient ON drug_ingredients(ingredient_id);

-- Audit queries
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_doctor ON audit_logs(doctor_id);
CREATE INDEX idx_audit_patient ON audit_logs(patient_id);

-- Unique constraints
CREATE UNIQUE INDEX idx_patients_external_id ON patients(external_id);
CREATE UNIQUE INDEX idx_drugs_rxcui ON drugs(rxcui);
```

### 7.2 Data Partitioning

**Audit Logs:**
- Partitioned by month for performance
- Old partitions can be archived to cold storage
- Keeps active queries fast

### 7.3 JSONB Usage

**Structured Report Data:**
- Stored in structured_data JSONB column
- Allows flexible schema for different document types
- Queryable with PostgreSQL JSON operators
- Indexed with GIN for fast searches

**Audit Drug Results:**
- Full prescription check results stored as JSONB
- Preserves complete context for compliance
- No need for complex relational schema

### 7.4 Connection Pooling

**SQLAlchemy Configuration:**
- Pool size: 20 connections
- Max overflow: 10 connections
- Pool recycle: 3600 seconds
- Async engine with asyncpg driver

## 8. Security Design

### 8.1 Authentication & Authorization

**Development Mode:**
- No authentication required
- Doctor ID from X-Doctor-Id header (optional)

**Production Mode:**
- JWT tokens from Keycloak
- OAuth 2.0 / OIDC flow
- Role-based access control (RBAC)
- Scoped permissions per endpoint

### 8.2 Data Protection

**At Rest:**
- PostgreSQL encryption enabled
- S3 server-side encryption (SSE-S3)
- Encrypted EBS volumes

**In Transit:**
- TLS 1.3 for all connections
- HTTPS only in production
- Database SSL connections required

**Input Validation:**
- Pydantic models validate all inputs
- File type validation on uploads
- Size limits enforced (10MB images, 10MB PDFs)
- SQL injection prevention via SQLAlchemy

### 8.3 Audit Trail

**Immutable Logging:**
- All prescription checks logged
- All overrides logged with justification
- No UPDATE or DELETE on audit tables
- Append-only architecture

**Logged Information:**
- Timestamp, doctor ID, patient ID, facility ID
- Full request and response data
- IP address and user agent
- Processing time

### 8.4 CORS Configuration

**Allowed Origins:**
- Configured via CORS_ORIGINS environment variable
- Comma-separated list of frontend URLs
- Credentials allowed for authenticated requests
- All methods and headers allowed


## 9. Deployment Architecture

### 9.1 AWS ECS Fargate Deployment

```
Internet
  │
  ▼
Application Load Balancer (ALB)
  │
  ├─► Frontend Service (ECS Fargate)
  │   └─► Next.js container (port 3000)
  │       CPU: 256, Memory: 512 MB
  │
  └─► Backend Service (ECS Fargate)
      └─► FastAPI container (port 8000)
          CPU: 512, Memory: 1024 MB
          │
          ├─► RDS PostgreSQL (SSL)
          ├─► Redis Cloud
          ├─► S3 Bucket (reports)
          └─► Gemini API (external)
```

**Service Configuration:**
- Frontend: 256 CPU, 512 MB RAM, desired count: 1
- Backend: 512 CPU, 1024 MB RAM, desired count: 1
- Auto-scaling based on CPU/memory
- Health checks on /health endpoint
- Rolling updates for zero-downtime deployments

### 9.2 Environment Configuration

**Backend Environment Variables:**
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require
REDIS_URL=redis://:password@host:port
AI_BACKEND=gemini
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.0-flash
USE_S3=true
S3_BUCKET=allersense-reports
S3_REGION=us-east-1
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://frontend-url
```

**Frontend Build Args:**
```
NEXT_PUBLIC_API_URL=https://backend-url
```

### 9.3 Monitoring & Logging

**CloudWatch Integration:**
- Log groups: /ecs/allersense-backend, /ecs/allersense-frontend
- Metrics: CPU, memory, request count, error rate
- Alarms: High error rate, high latency, service down

**Structured Logging:**
- JSON format in production (structlog)
- Human-readable in development
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Correlation IDs for request tracing

**Health Checks:**
- Liveness: GET /health (returns {"status": "ok"})
- Readiness: GET /health/ready (checks DB + Redis)
- ALB health check interval: 30 seconds
- Unhealthy threshold: 3 consecutive failures

### 9.4 Networking

**Security Groups:**
- ALB: Inbound 80/443 from 0.0.0.0/0
- Backend: Inbound 8000 from ALB security group
- Frontend: Inbound 3000 from ALB security group
- RDS: Inbound 5432 from Backend security group

**VPC Configuration:**
- Public subnets for ALB
- Private subnets for ECS tasks
- NAT Gateway for outbound internet access
- VPC endpoints for S3 (optional, cost optimization)

## 10. Error Handling

### 10.1 Error Response Format

```json
{
  "detail": "Error message",
  "error_code": "PATIENT_NOT_FOUND",
  "status_code": 404
}
```

### 10.2 HTTP Status Codes

- 200: Success
- 201: Created
- 400: Bad Request (validation error)
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Unprocessable Entity (OCR failed, invalid input)
- 429: Too Many Requests
- 500: Internal Server Error
- 503: Service Unavailable

### 10.3 Graceful Degradation

**AI Backend Unavailable:**
- Return error message to user
- Log failure for investigation
- Suggest retry or manual review

**Redis Cache Unavailable:**
- Fall back to direct database queries
- Log warning
- System remains functional

**Database Connection Issues:**
- Retry with exponential backoff
- Return 503 Service Unavailable
- Health check fails

**S3 Upload Failures:**
- Retry up to 3 times
- Return error to user if all retries fail
- Log failure for investigation


## 11. Frontend Architecture

### 11.1 Application Structure

```
frontend/src/
├── app/
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Landing page
│   ├── doctor/
│   │   └── page.tsx         # Doctor portal
│   └── patient/
│       └── page.tsx         # Patient portal
└── lib/
    └── api.ts               # API client functions
```

### 11.2 Routing

Next.js file-based routing:
- / → Landing page with portal selection
- /doctor → Doctor portal (patient management, prescription checking)
- /patient → Patient portal (view-only access to profile)

### 11.3 API Client Design

**Centralized API Functions:**
- searchDrugs(query): Fuzzy drug search
- getPatientProfile(patientId): Fetch allergy profile
- checkPrescription(patientId, drugs): Manual check
- checkPrescriptionPhoto(patientId, imageFile): Photo check
- overridePrescription(requestId, warningIds, justification): Override
- uploadReport(patientId, file): Upload report
- getReports(patientId): List reports
- replaceReport(patientId, reportId, file): Replace report
- askAI(patientId, question, medicineName, history): Chat with AI
- createPatient(data): Create new patient
- addAllergy(patientId, data): Add allergy
- addCondition(patientId, data): Add condition

**Error Handling:**
- All functions throw errors on failure
- UI components catch and display errors
- Network errors show user-friendly messages

### 11.4 State Management

**Local Component State:**
- React useState for UI state
- No global state management library needed
- API calls trigger re-renders

**Data Flow:**
- User action → API call → Update local state → Re-render

### 11.5 Styling Approach

**TailwindCSS Utility Classes:**
- Responsive design with breakpoints (sm, md, lg)
- Color palette: blue (doctor), emerald (patient)
- Consistent spacing and typography
- Gradient backgrounds for visual appeal

**Component Patterns:**
- Card-based layouts
- Color-coded signals (green/yellow/red)
- Loading states with spinners
- Error states with messages

## 12. Performance Optimization

### 12.1 Backend Optimizations

**Database Query Optimization:**
- Eager loading of relationships with joinedload()
- Indexed columns for frequent queries
- Connection pooling to reduce overhead
- Query result caching in Redis

**API Response Optimization:**
- Pagination for list endpoints
- Field selection to reduce payload size
- Compression for large responses
- Async processing for long-running tasks

**Caching Strategy:**
- Patient profiles cached for 15 minutes
- Drug search results cached for 1 hour
- Drug ingredients cached for 24 hours
- Cache warming for frequently accessed data

### 12.2 Frontend Optimizations

**Next.js Features:**
- Server-side rendering for initial page load
- Static generation for landing page
- Image optimization with next/image
- Code splitting for smaller bundles

**Asset Optimization:**
- TailwindCSS purging unused styles
- Minification in production build
- Lazy loading of heavy components
- Debouncing for search inputs

### 12.3 AI Optimization

**Prompt Engineering:**
- Concise prompts to reduce token usage
- Structured output format for easy parsing
- Temperature 0.1 for consistent results
- Max tokens limit to prevent runaway costs

**Request Batching:**
- Single AI call for multiple drugs
- Verification loop only when needed
- Report text truncation to 3000 chars

## 13. Testing Strategy

### 13.1 Backend Testing

**Unit Tests:**
- Test individual service functions
- Mock external dependencies (AI, database)
- Test edge cases and error conditions
- Coverage target: 80%+

**Integration Tests:**
- Test API endpoints end-to-end
- Use test database
- Test AI integration with real API calls
- Test database transactions

**Load Tests:**
- Simulate 100+ concurrent users
- Test database connection pooling
- Verify caching effectiveness
- Identify bottlenecks

### 13.2 Frontend Testing

**Component Tests:**
- Test UI components in isolation
- Mock API calls
- Test user interactions
- Test error states

**E2E Tests:**
- Test complete user workflows
- Test doctor portal flows
- Test patient portal flows
- Test error handling

### 13.3 AI Testing

**Prompt Testing:**
- Test with various patient profiles
- Test with different drug combinations
- Verify JSON output format
- Test confidence thresholds

**OCR Testing:**
- Test with clear prescription images
- Test with blurry images
- Test with handwritten prescriptions
- Verify confidence scoring

## 14. Future Enhancements

### 14.1 Planned Features

**Phase 2:**
- FHIR R4 integration for EHR connectivity
- Real-time WebSocket notifications
- Advanced analytics dashboard
- Multi-language support
- Mobile native apps (React Native)

**Phase 3:**
- Fine-tuned AI models for medical domain
- Ensemble models for higher accuracy
- Drug interaction checking beyond allergies
- Dosage calculation based on patient weight
- Integration with pharmacy systems

### 14.2 Scalability Improvements

**Database:**
- Read replicas for PostgreSQL
- Database sharding for large datasets
- Query optimization and indexing
- Materialized views for complex queries

**Caching:**
- Redis Sentinel for high availability
- Redis Cluster for horizontal scaling
- CDN for static assets
- Edge caching for API responses

**Application:**
- Horizontal scaling with more ECS tasks
- Auto-scaling based on metrics
- Async task processing with queues (Celery)
- Microservices architecture (if needed)

### 14.3 AI Enhancements

**Model Improvements:**
- Fine-tuning on medical datasets
- Ensemble models for consensus
- Confidence scoring for AI decisions
- Explainable AI for transparency

**Feature Additions:**
- Drug-drug interaction checking
- Dosage recommendations
- Alternative therapy suggestions
- Predictive allergy risk scoring

## 15. Compliance & Regulations

### 15.1 HIPAA Compliance

**Technical Safeguards:**
- Encryption at rest and in transit
- Access controls and authentication
- Audit logging of all PHI access
- Automatic session timeout

**Administrative Safeguards:**
- Business Associate Agreements (BAAs)
- Security policies and procedures
- Workforce training
- Incident response plan

**Physical Safeguards:**
- AWS data center security
- Encrypted backups
- Disaster recovery plan

### 15.2 Data Retention

**Patient Data:**
- Retained indefinitely for medical records
- Soft delete with retention flag
- Archival to cold storage after 7 years

**Audit Logs:**
- Retained for 7 years minimum
- Partitioned by month
- Archived to S3 Glacier after 1 year

**Reports:**
- Retained for 7 years
- Versioning maintained
- Automatic deletion after retention period

### 15.3 Privacy Controls

**Data Minimization:**
- Only collect necessary data
- Anonymize data for analytics
- Pseudonymize patient identifiers

**Access Controls:**
- Role-based access (doctor, patient, admin)
- Audit all data access
- Principle of least privilege

**Patient Rights:**
- Right to access their data
- Right to correct inaccurate data
- Right to delete data (with exceptions)
- Right to export data

## 16. Disaster Recovery

### 16.1 Backup Strategy

**Database Backups:**
- RDS automated daily backups
- Retention: 7 days
- Point-in-time recovery enabled
- Manual snapshots before major changes

**File Storage Backups:**
- S3 versioning enabled
- Cross-region replication (optional)
- Lifecycle policies for cost optimization

### 16.2 Recovery Procedures

**Database Failure:**
- RTO: 15 minutes
- RPO: 5 minutes
- Restore from latest automated backup
- Failover to read replica if available

**Application Failure:**
- RTO: 5 minutes
- RPO: 0 (stateless)
- ECS auto-restart failed tasks
- Deploy new tasks if needed

**Region Failure:**
- RTO: 1 hour
- RPO: 5 minutes
- Failover to secondary region
- Restore database from backup

### 16.3 High Availability

**Multi-AZ Deployment:**
- RDS Multi-AZ for database
- ECS tasks in multiple availability zones
- ALB distributes traffic across zones

**Redundancy:**
- Multiple ECS tasks per service
- Database read replicas
- Redis Sentinel for cache HA

## 17. Cost Optimization

### 17.1 Current Costs (Monthly)

**AWS Infrastructure:**
- ECS Fargate: $30-40 (backend + frontend)
- RDS db.t3.micro: $15
- ALB: $20 (2 load balancers)
- S3: $1-5 (depending on usage)
- Data Transfer: $5-10
- CloudWatch Logs: $1-2
- **Total: ~$72-93/month**

**External Services:**
- Gemini API: Pay-per-use (varies)
- Redis Cloud: Free tier or $5-10/month
- **Total: $5-50/month depending on usage**

**Grand Total: ~$77-143/month**

### 17.2 Cost Optimization Strategies

**Compute:**
- Right-size ECS tasks based on metrics
- Use Fargate Spot for non-critical workloads
- Scale down during off-peak hours

**Storage:**
- S3 lifecycle policies to move old reports to Glacier
- Delete old CloudWatch logs
- Compress large files before upload

**Database:**
- Use smaller instance types for development
- Enable query caching
- Optimize slow queries

**AI:**
- Cache AI responses when possible
- Use smaller models for simple tasks
- Batch requests to reduce API calls

## 18. Glossary

**Terms:**
- **Allergen**: Substance causing allergic reaction
- **Cross-reactivity**: Similar proteins causing reactions to multiple substances
- **Criticality**: Potential severity of allergic reaction
- **Contraindication**: Factor making treatment inadvisable
- **Lab Sensitivity**: Elevated lab markers indicating potential allergic response
- **OCR**: Optical Character Recognition
- **Signal**: Risk classification (GREEN/YELLOW/RED)
- **Override**: Doctor's decision to proceed despite RED warning
- **Audit Trail**: Immutable log of all system actions

**Acronyms:**
- **API**: Application Programming Interface
- **AWS**: Amazon Web Services
- **ECS**: Elastic Container Service
- **RDS**: Relational Database Service
- **S3**: Simple Storage Service
- **ALB**: Application Load Balancer
- **HIPAA**: Health Insurance Portability and Accountability Act
- **FHIR**: Fast Healthcare Interoperability Resources
- **JWT**: JSON Web Token
- **RBAC**: Role-Based Access Control
- **TTL**: Time To Live
- **RTO**: Recovery Time Objective
- **RPO**: Recovery Point Objective
