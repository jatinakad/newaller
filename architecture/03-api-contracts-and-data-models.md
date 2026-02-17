
# MedGuard — API Contracts & Data Models

## 1. Core Data Models

### 1.1 Patient Allergy Profile

```typescript
interface PatientAllergyProfile {
  patientId: string;
  demographics: {
    name: string;
    age: number;
    gender: string;
    weight?: number;  // kg — relevant for dosage contraindications
  };
  knownAllergens: Allergen[];
  labFlaggedSensitivities: LabSensitivity[];
  conditions: PatientCondition[];
  lastUpdated: string;  // ISO 8601
  source: "EHR" | "MANUAL" | "LAB_IMPORT";
}

interface Allergen {
  code: string;           // SNOMED CT code
  display: string;        // e.g., "Penicillin"
  category: "drug" | "food" | "environment" | "biologic";
  criticality: "low" | "high" | "unable-to-assess";
  reaction?: {
    substance: string;
    manifestation: string[];  // e.g., ["Anaphylaxis", "Urticaria"]
    severity: "mild" | "moderate" | "severe";
  };
  verificationStatus: "confirmed" | "unconfirmed" | "refuted";
  recordedDate: string;
}

interface LabSensitivity {
  testCode: string;       // LOINC code
  testName: string;       // e.g., "Specific IgE - Penicillin"
  value: number;
  unit: string;           // e.g., "kU/L"
  referenceRange: string; // e.g., "< 0.35"
  interpretation: "normal" | "elevated" | "high";
  relatedSubstances: string[];  // Substances this sensitivity implies
  reportDate: string;
}

interface PatientCondition {
  code: string;           // ICD-10 / SNOMED
  display: string;        // e.g., "G6PD Deficiency"
  contraindicatedIngredients: string[];  // Ingredients to avoid
}
```

### 1.2 Drug & Ingredient Models

```typescript
interface Drug {
  rxcui: string;              // RxNorm Concept Unique Identifier
  name: string;               // e.g., "Amoxicillin 500mg Capsule"
  brandNames: string[];       // e.g., ["Amoxil", "Trimox"]
  genericName: string;        // e.g., "Amoxicillin"
  dosageForm: string;         // e.g., "Capsule", "Lotion", "Syrup"
  route: string;              // e.g., "Oral", "Topical", "Injectable"
  ingredients: DrugIngredient[];
  ndc: string[];              // National Drug Codes
  splId?: string;             // DailyMed SPL identifier
}

interface DrugIngredient {
  ingredientId: string;
  name: string;               // e.g., "Amoxicillin Trihydrate"
  type: "active" | "inactive" | "excipient";
  strength?: string;          // e.g., "500 mg"
  chemicalFamily?: string;    // e.g., "Penicillin-class Beta-Lactam"
  allergenCodes: string[];    // SNOMED codes for related allergens
}

interface CrossReactivityGroup {
  groupId: string;
  groupName: string;          // e.g., "Beta-Lactam Antibiotics"
  members: {
    ingredientId: string;
    name: string;
    crossReactivityProbability: "high" | "moderate" | "low";
  }[];
}
```

### 1.3 Allergy Check Result

```typescript
interface AllergyCheckResult {
  requestId: string;          // Unique request ID for audit trail
  patientId: string;
  timestamp: string;
  overallSignal: "GREEN" | "YELLOW" | "RED";
  drugResults: DrugCheckResult[];
  processingTimeMs: number;
}

interface DrugCheckResult {
  drug: {
    rxcui: string;
    name: string;
  };
  signal: "GREEN" | "YELLOW" | "RED";
  warnings: Warning[];
  alternatives: AlternativeDrug[];
}

interface Warning {
  warningId: string;
  severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  type: "DIRECT_ALLERGEN_MATCH"
      | "CROSS_REACTIVITY"
      | "LAB_SENSITIVITY"
      | "CONDITION_CONTRAINDICATION"
      | "EXCIPIENT_ALLERGY";
  ingredient: string;
  allergen: string;
  message: string;            // Human-readable warning
  evidence: {
    source: "EHR_ALLERGY" | "LAB_REPORT" | "CROSS_REACTIVITY_DB" | "CONDITION";
    detail: string;
  };
}

interface AlternativeDrug {
  rxcui: string;
  name: string;
  reason: string;             // Why this is a safe alternative
  signal: "GREEN";            // Only suggest GREEN alternatives
}
```

### 1.4 Audit Record

```typescript
interface AuditRecord {
  auditId: string;            // UUID
  timestamp: string;
  eventType: "PRESCRIPTION_CHECK" | "OVERRIDE" | "PROFILE_ACCESS";
  doctorId: string;
  patientId: string;
  facilityId: string;
  prescriptionCheckResult?: AllergyCheckResult;
  override?: {
    overriddenWarnings: string[];   // Warning IDs
    clinicalJustification: string;
    digitalSignature: string;
    witnessId?: string;
  };
  ipAddress: string;
  userAgent: string;
}
```

---

## 2. REST API Contracts

### 2.1 Prescription Check — Photo Upload

```
POST /api/v1/prescription/check/photo
Content-Type: multipart/form-data
Authorization: Bearer <token>

Form Fields:
  - patientId: string (required)
  - image: File (required, JPEG/PNG, max 10MB)
  - facilityId: string (required)

Response 200:
{
  "requestId": "uuid-1234",
  "patientId": "P-5678",
  "overallSignal": "RED",
  "ocrConfidence": 0.92,
  "extractedDrugs": ["Amoxicillin 500mg", "Cetrizine 10mg"],
  "drugResults": [
    {
      "drug": { "rxcui": "723", "name": "Amoxicillin 500mg Capsule" },
      "signal": "RED",
      "warnings": [
        {
          "warningId": "W-001",
          "severity": "CRITICAL",
          "type": "DIRECT_ALLERGEN_MATCH",
          "ingredient": "Amoxicillin Trihydrate",
          "allergen": "Penicillin",
          "message": "Amoxicillin is a Penicillin-class antibiotic. Patient has CONFIRMED Penicillin allergy with history of Anaphylaxis.",
          "evidence": {
            "source": "EHR_ALLERGY",
            "detail": "AllergyIntolerance recorded 2023-05-12, criticality: high"
          }
        }
      ],
      "alternatives": [
        {
          "rxcui": "18631",
          "name": "Azithromycin 500mg Tablet",
          "reason": "Macrolide antibiotic — no cross-reactivity with Penicillin",
          "signal": "GREEN"
        }
      ]
    },
    {
      "drug": { "rxcui": "3498", "name": "Cetirizine 10mg Tablet" },
      "signal": "GREEN",
      "warnings": [],
      "alternatives": []
    }
  ],
  "processingTimeMs": 3200
}

Response 422 (OCR Failed):
{
  "error": "OCR_EXTRACTION_FAILED",
  "message": "Could not extract drug names from image. Please retry with a clearer photo or enter drug names manually.",
  "ocrConfidence": 0.15
}
```

### 2.2 Prescription Check — Manual Entry

```
POST /api/v1/prescription/check
Content-Type: application/json
Authorization: Bearer <token>

Request:
{
  "patientId": "P-5678",
  "facilityId": "F-100",
  "drugs": [
    { "rxcui": "723" },
    { "rxcui": "3498" },
    { "name": "Calamine Lotion" }   // fallback: name-based lookup
  ]
}

Response 200:
{
  "requestId": "uuid-5678",
  "patientId": "P-5678",
  "overallSignal": "RED",
  "drugResults": [ ... ],          // Same structure as photo response
  "processingTimeMs": 850
}
```

### 2.3 Drug Search / Autocomplete

```
GET /api/v1/drugs/search?q=amox&limit=10
Authorization: Bearer <token>

Response 200:
{
  "results": [
    {
      "rxcui": "723",
      "name": "Amoxicillin 500mg Capsule",
      "genericName": "Amoxicillin",
      "brandNames": ["Amoxil"],
      "dosageForm": "Capsule",
      "route": "Oral"
    },
    {
      "rxcui": "724",
      "name": "Amoxicillin 250mg Capsule",
      "genericName": "Amoxicillin",
      "brandNames": ["Amoxil"],
      "dosageForm": "Capsule",
      "route": "Oral"
    },
    {
      "rxcui": "19711",
      "name": "Amoxicillin-Clavulanate 875-125mg Tablet",
      "genericName": "Amoxicillin / Clavulanate",
      "brandNames": ["Augmentin"],
      "dosageForm": "Tablet",
      "route": "Oral"
    }
  ],
  "total": 3
}
```

### 2.4 Patient Allergy Profile

```
GET /api/v1/patients/{patientId}/allergy-profile
Authorization: Bearer <token>

Response 200:
{
  "patientId": "P-5678",
  "demographics": {
    "name": "John Doe",
    "age": 45,
    "gender": "Male"
  },
  "knownAllergens": [
    {
      "code": "91936005",
      "display": "Penicillin",
      "category": "drug",
      "criticality": "high",
      "reaction": {
        "substance": "Penicillin",
        "manifestation": ["Anaphylaxis"],
        "severity": "severe"
      },
      "verificationStatus": "confirmed",
      "recordedDate": "2023-05-12"
    }
  ],
  "labFlaggedSensitivities": [
    {
      "testCode": "6158-0",
      "testName": "Specific IgE - Cephalosporin",
      "value": 1.2,
      "unit": "kU/L",
      "referenceRange": "< 0.35",
      "interpretation": "elevated",
      "relatedSubstances": ["Cephalexin", "Cefazolin"],
      "reportDate": "2024-01-15"
    }
  ],
  "conditions": [
    {
      "code": "G6PD",
      "display": "G6PD Deficiency",
      "contraindicatedIngredients": ["Dapsone", "Primaquine", "Nitrofurantoin"]
    }
  ],
  "lastUpdated": "2024-01-15T10:30:00Z",
  "source": "EHR"
}
```

### 2.5 Override Prescription

```
POST /api/v1/prescription/override
Content-Type: application/json
Authorization: Bearer <token>

Request:
{
  "requestId": "uuid-1234",
  "overriddenWarnings": ["W-001"],
  "clinicalJustification": "Patient has tolerated Amoxicillin previously despite recorded allergy. Allergy record may be outdated. Will monitor closely for 30 minutes post-administration.",
  "digitalSignature": "base64-encoded-signature"
}

Response 200:
{
  "auditId": "AUD-9999",
  "status": "OVERRIDE_RECORDED",
  "message": "Override recorded. Pharmacy and supervising physician notified.",
  "prescriptionId": "RX-4567"
}
```

### 2.6 Drug Ingredient Lookup

```
GET /api/v1/drugs/{rxcui}/ingredients
Authorization: Bearer <token>

Response 200:
{
  "rxcui": "723",
  "name": "Amoxicillin 500mg Capsule",
  "ingredients": [
    {
      "ingredientId": "ING-001",
      "name": "Amoxicillin Trihydrate",
      "type": "active",
      "strength": "500 mg",
      "chemicalFamily": "Penicillin-class Beta-Lactam",
      "allergenCodes": ["91936005"]
    },
    {
      "ingredientId": "ING-002",
      "name": "Magnesium Stearate",
      "type": "excipient",
      "chemicalFamily": null,
      "allergenCodes": []
    },
    {
      "ingredientId": "ING-003",
      "name": "Gelatin",
      "type": "excipient",
      "chemicalFamily": null,
      "allergenCodes": ["412071004"]
    }
  ]
}
```

---

## 3. FHIR R4 Integration — EHR Queries

### 3.1 Fetch Patient Allergies

```
GET [EHR_BASE]/AllergyIntolerance?patient={patientId}&clinical-status=active
Accept: application/fhir+json

Maps to → PatientAllergyProfile.knownAllergens[]
```

### 3.2 Fetch Lab Results (Allergy-Related)

```
GET [EHR_BASE]/Observation?patient={patientId}&category=laboratory&code=6158-0,7258-7
Accept: application/fhir+json

LOINC codes for allergy labs:
  - 6158-0: Specific IgE panel
  - 7258-7: Total IgE
  - Skin prick test results (facility-specific codes)

Maps to → PatientAllergyProfile.labFlaggedSensitivities[]
```

### 3.3 Fetch Patient Conditions

```
GET [EHR_BASE]/Condition?patient={patientId}&clinical-status=active
Accept: application/fhir+json

Maps to → PatientAllergyProfile.conditions[]
```

---

## 4. Database Schema (PostgreSQL)

```sql
-- ============================================
-- DRUG KNOWLEDGE BASE
-- ============================================

CREATE TABLE drugs (
    rxcui           VARCHAR(20) PRIMARY KEY,
    name            VARCHAR(500) NOT NULL,
    generic_name    VARCHAR(500),
    dosage_form     VARCHAR(100),
    route           VARCHAR(100),
    ndc_codes       TEXT[],
    spl_id          VARCHAR(100),
    source          VARCHAR(50) DEFAULT 'OPENFDA',
    last_synced_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE drug_brand_names (
    id              SERIAL PRIMARY KEY,
    rxcui           VARCHAR(20) REFERENCES drugs(rxcui),
    brand_name      VARCHAR(500) NOT NULL
);

CREATE TABLE ingredients (
    ingredient_id   VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(500) NOT NULL,
    chemical_family VARCHAR(200),
    allergen_codes  TEXT[],          -- SNOMED CT codes
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE drug_ingredients (
    id              SERIAL PRIMARY KEY,
    rxcui           VARCHAR(20) REFERENCES drugs(rxcui),
    ingredient_id   VARCHAR(50) REFERENCES ingredients(ingredient_id),
    type            VARCHAR(20) CHECK (type IN ('active', 'inactive', 'excipient')),
    strength        VARCHAR(100),
    UNIQUE(rxcui, ingredient_id)
);

CREATE INDEX idx_drug_ingredients_rxcui ON drug_ingredients(rxcui);
CREATE INDEX idx_drug_ingredients_ingredient ON drug_ingredients(ingredient_id);

-- ============================================
-- CROSS-REACTIVITY GRAPH (via Apache AGE extension for PostgreSQL)
-- ============================================

CREATE TABLE cross_reactivity_groups (
    group_id        VARCHAR(50) PRIMARY KEY,
    group_name      VARCHAR(200) NOT NULL
);

CREATE TABLE cross_reactivity_members (
    id              SERIAL PRIMARY KEY,
    group_id        VARCHAR(50) REFERENCES cross_reactivity_groups(group_id),
    ingredient_id   VARCHAR(50) REFERENCES ingredients(ingredient_id),
    probability     VARCHAR(20) CHECK (probability IN ('high', 'moderate', 'low'))
);

-- ============================================
-- AUDIT LOG (append-only)
-- ============================================

CREATE TABLE audit_logs (
    audit_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type      VARCHAR(50) NOT NULL,
    doctor_id       VARCHAR(100) NOT NULL,
    patient_id      VARCHAR(100) NOT NULL,
    facility_id     VARCHAR(100) NOT NULL,
    request_id      UUID,
    overall_signal  VARCHAR(10),
    drug_results    JSONB,
    processing_ms   INTEGER,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partition by month for performance
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_doctor ON audit_logs(doctor_id);
CREATE INDEX idx_audit_patient ON audit_logs(patient_id);

CREATE TABLE audit_overrides (
    override_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id            UUID REFERENCES audit_logs(audit_id),
    overridden_warnings TEXT[] NOT NULL,
    justification       TEXT NOT NULL,
    digital_signature   TEXT NOT NULL,
    witness_id          VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- FULL-TEXT SEARCH SUPPORT (via pg_trgm extension — no ElasticSearch needed)
-- ============================================

CREATE INDEX idx_drugs_name_trgm ON drugs USING gin (name gin_trgm_ops);
CREATE INDEX idx_drugs_generic_trgm ON drugs USING gin (generic_name gin_trgm_ops);
```

---

## 5. Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `PATIENT_NOT_FOUND` | 404 | Patient ID not found in EHR |
| `DRUG_NOT_FOUND` | 404 | Drug could not be resolved |
| `OCR_EXTRACTION_FAILED` | 422 | Could not extract drug names from image |
| `OCR_LOW_CONFIDENCE` | 200 | Extraction succeeded but confidence < 70% — manual review suggested |
| `EHR_UNAVAILABLE` | 503 | EHR system unreachable — fallback to cached profile |
| `ALLERGY_PROFILE_STALE` | 200 | Profile older than 24h — warning included in response |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `UNAUTHORIZED` | 401 | Invalid or expired token |
| `FORBIDDEN` | 403 | Doctor not authorized for this patient/facility |