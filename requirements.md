# AllerSense - Requirements Document

## 1. Executive Summary

AllerSense is an AI-powered patient allergy prevention system that helps healthcare providers detect potential allergic reactions before prescribing medications. The system analyzes prescribed drugs against patient allergy profiles, medical conditions, and lab sensitivities using AWS bedrock AI to provide real-time safety assessments.

## 2. Problem Statement

Healthcare providers face significant challenges in preventing allergic reactions:
- Patients may have complex allergy profiles with cross-reactive drug families
- Manual checking of drug ingredients against allergies is time-consuming and error-prone
- Medical reports and lab results contain critical allergy information that may be overlooked
- Cross-reactivity between drug families (e.g., Beta-Lactams, NSAIDs) requires specialized knowledge
- Prescription images need to be accurately interpreted and analyzed

## 3. System Goals

### Primary Goals
1. Prevent allergic reactions by checking prescribed drugs against patient allergy profiles
2. Provide AI-powered analysis of drug ingredients and cross-reactivity
3. Extract and analyze medical reports to identify allergy-related information
4. Support both manual drug entry and prescription photo upload workflows
5. Maintain comprehensive audit trails for compliance and safety

### Secondary Goals
1. Enable conversational AI interface for querying patient data
2. Support multiple AI backends (Gemini, Ollama, HuggingFace)
3. Provide alternative drug suggestions when allergies are detected
4. Allow doctor overrides with clinical justification
5. Maintain version control for patient reports

## 4. User Roles

### 4.1 Doctor
- Primary user of the system
- Can create and manage patient profiles
- Uploads patient reports and prescriptions
- Performs allergy checks on prescriptions
- Can override RED warnings with justification
- Interacts with AI chat for patient queries

### 4.2 Patient
- Read-only access to their own data
- Views allergy profile and medical conditions
- Reviews uploaded reports and documents
- Sees lab values and sensitivities

### 4.3 System Administrator
- Manages drug database
- Monitors system health
- Reviews audit logs
- Configures AI backends

## 5. Functional Requirements

### 5.1 Patient Management

#### 5.1.1 Create Patient Profile
**Priority:** High  
**Description:** Doctors can create new patient profiles with demographic information.

**Acceptance Criteria:**
- System accepts external_id, name, age, gender, and weight_kg
- External_id must be unique across all patients
- Patient profile is immediately available after creation
- System generates internal UUID for patient

#### 5.1.2 View Patient Allergy Profile
**Priority:** High  
**Description:** Retrieve comprehensive patient allergy and medical information.

**Acceptance Criteria:**
- Profile includes known allergens with criticality levels
- Profile includes medical conditions with contraindicated ingredients
- Profile includes lab sensitivities with interpretation
- Profile includes patient demographics
- Data is cached for 15 minutes for performance

#### 5.1.3 Add Patient Allergies
**Priority:** High  
**Description:** Add known allergens to patient profile.

**Acceptance Criteria:**
- System accepts allergen name, category, criticality, reaction manifestations, and severity
- Categories include: drug, food, environment, biologic
- Criticality levels: low, high, unable-to-assess
- Severity levels: mild, moderate, severe
- Allergies are immediately reflected in allergy checks

#### 5.1.4 Add Patient Conditions
**Priority:** High  
**Description:** Add medical conditions that may contraindicate certain drugs.

**Acceptance Criteria:**
- System accepts condition name and list of contraindicated ingredients
- Conditions are checked during prescription analysis
- Examples: G6PD Deficiency, Kidney Disease, Liver Disease

#### 5.1.5 Add Lab Sensitivities
**Priority:** Medium  
**Description:** Record lab test results indicating drug sensitivities.

**Acceptance Criteria:**
- System accepts test name, value, unit, reference range, interpretation
- Interpretation values: normal, elevated, high
- Related substances can be specified
- Lab values are considered in allergy analysis

### 5.2 Report Management

#### 5.2.1 Upload Patient Report
**Priority:** High  
**Description:** Upload medical reports (PDF, images) for AI extraction and analysis.

**Acceptance Criteria:**
- Supports PDF, JPEG, PNG, WebP formats
- Maximum file size: 10MB
- AI extracts text from uploaded documents
- AI structures data into medications, lab results, diagnoses, allergies
- Extracted data is stored as structured JSON
- Reports are versioned (version 1, 2, 3...)

#### 5.2.2 View Patient Reports
**Priority:** High  
**Description:** List all reports uploaded for a patient.

**Acceptance Criteria:**
- Shows filename, upload date, status, version
- Displays extracted text when available
- Shows structured data (medications, lab results, diagnoses)
- Indicates which report is the latest version
- Reports are ordered by upload date (newest first)

#### 5.2.3 Replace Report
**Priority:** Medium  
**Description:** Upload a new version of an existing report.

**Acceptance Criteria:**
- Creates new version of report
- Marks previous version as superseded
- New version becomes the latest
- Previous versions remain accessible
- Maintains audit trail of all versions

#### 5.2.4 AI Report Extraction
**Priority:** High  
**Description:** Automatically extract structured data from uploaded reports.

**Acceptance Criteria:**
- Extracts patient information (name, ID, age, gender, DOB)
- Extracts medications with dosage, frequency, route
- Extracts lab results with values, units, reference ranges
- Extracts diagnoses with ICD codes
- Identifies mentioned allergies
- Extracts vital signs
- Generates clinical summary
- Extraction completes within 30 seconds

### 5.3 Prescription Checking

#### 5.3.1 Manual Prescription Check
**Priority:** High  
**Description:** Check manually entered drug names against patient allergies.

**Acceptance Criteria:**
- Accepts list of drug names
- Returns overall signal: GREEN, YELLOW, or RED
- Provides per-drug analysis with signal and reasoning
- Lists specific warnings with severity, type, ingredient, allergen
- Suggests alternative drugs when allergies detected
- Includes AI reasoning for each decision
- Completes within 5 seconds
- Creates audit log entry

#### 5.3.2 Photo Prescription Check
**Priority:** High  
**Description:** Upload prescription photo for OCR and allergy checking.

**Acceptance Criteria:**
- Accepts JPEG, PNG, WebP images up to 10MB
- AI extracts drug names from image
- Returns OCR confidence score
- Lists extracted drug names
- Performs allergy check on extracted drugs
- Returns same analysis as manual check
- Fails gracefully if OCR confidence < 0.3
- Completes within 10 seconds

#### 5.3.3 AI-Powered Allergy Analysis
**Priority:** High  
**Description:** Use AI to analyze drug ingredients and cross-reactivity.

**Acceptance Criteria:**
- AI checks all active and inactive ingredients
- AI identifies cross-reactivity between drug families
- AI considers patient conditions and contraindications
- AI reviews lab values for relevant sensitivities
- AI incorporates information from uploaded reports
- AI provides detailed clinical reasoning for each warning
- AI suggests safe alternative medications
- AI can request additional drug information if uncertain

#### 5.3.4 Web-Enhanced Drug Information
**Priority:** Medium  
**Description:** Fetch drug information from OpenFDA/DailyMed when AI is uncertain.

**Acceptance Criteria:**
- System identifies drugs needing verification
- Fetches ingredient lists from FDA databases
- Retrieves contraindication information
- Provides citations for data sources
- Retries AI analysis with enhanced context
- Completes within 15 seconds total

#### 5.3.5 Signal Classification
**Priority:** High  
**Description:** Classify allergy risk with clear visual signals.

**Acceptance Criteria:**
- GREEN: No known conflicts, safe to prescribe
- YELLOW: Possible cross-reactivity or lab concern, review recommended
- RED: Direct allergen match or critical contraindication, do not prescribe
- Overall signal is worst case across all drugs
- Each drug has individual signal
- Signals are color-coded in UI

#### 5.3.6 Warning Details
**Priority:** High  
**Description:** Provide detailed information about detected risks.

**Acceptance Criteria:**
- Each warning includes severity: CRITICAL, HIGH, MODERATE, LOW
- Warning types: DIRECT_MATCH, CROSS_REACTIVITY, CONTRAINDICATION, LAB_CONCERN
- Identifies specific ingredient causing issue
- Identifies patient allergen it conflicts with
- Provides clear message explaining the risk
- Includes detailed clinical reasoning
- References evidence source (patient allergy, lab report, condition)

#### 5.3.7 Alternative Drug Suggestions
**Priority:** Medium  
**Description:** Suggest safe alternative medications when allergies detected.

**Acceptance Criteria:**
- AI suggests up to 3 alternatives per flagged drug
- Alternatives have GREEN signal (verified safe)
- Includes reason why alternative is safe
- Considers same therapeutic class when possible
- Alternatives are clinically appropriate

### 5.4 Override Management

#### 5.4.1 Doctor Override
**Priority:** High  
**Description:** Allow doctors to override RED warnings with justification.

**Acceptance Criteria:**
- Requires clinical justification text
- Requires digital signature
- Records doctor ID from request header
- Creates immutable audit log entry
- Captures IP address and user agent
- Returns audit ID for tracking
- Override cannot be deleted or modified

### 5.5 AI Chat Interface

#### 5.5.1 Conversational Patient Queries
**Priority:** Medium  
**Description:** Allow doctors to ask questions about patient data in natural language.

**Acceptance Criteria:**
- Accepts patient ID and question text
- Optionally accepts medicine name for drug-specific queries
- Maintains conversation history for context
- AI has access to patient allergies, conditions, lab values
- AI can read uploaded report text
- Returns natural language answer
- Indicates what context was used (allergy count, report availability)
- Completes within 10 seconds

### 5.6 Drug Database

#### 5.6.1 Drug Search
**Priority:** High  
**Description:** Fuzzy search for drugs by name.

**Acceptance Criteria:**
- Uses PostgreSQL pg_trgm for fuzzy matching
- Searches drug name and generic name
- Returns up to 10 results
- Includes rxcui, name, generic name, dosage form, route, brand names
- Results ordered by relevance
- Completes within 500ms

### 5.7 Audit and Compliance

#### 5.7.1 Prescription Check Audit
**Priority:** High  
**Description:** Log every prescription check for compliance.

**Acceptance Criteria:**
- Records request ID, timestamp, doctor ID, patient ID
- Records overall signal and all drug results
- Records processing time
- Records facility ID
- Records IP address and user agent
- Logs are immutable (no updates or deletes)
- Logs are partitioned by month for performance

#### 5.7.2 Override Audit
**Priority:** High  
**Description:** Log all doctor overrides with full context.

**Acceptance Criteria:**
- Links to original prescription check audit entry
- Records overridden warning IDs
- Records clinical justification
- Records digital signature
- Records timestamp, IP, user agent
- Logs are immutable

## 6. Non-Functional Requirements

### 6.1 Performance
- Manual prescription check: < 5 seconds
- Photo prescription check: < 10 seconds
- Drug search: < 500ms
- Report upload: < 30 seconds for extraction
- AI chat response: < 10 seconds
- System supports 100 concurrent users

### 6.2 Scalability
- Database handles 100,000+ patients
- Supports 10,000+ drugs in database
- Handles 1,000+ prescription checks per day
- Stores unlimited patient reports (with S3)

### 6.3 Availability
- System uptime: 99.5%
- Graceful degradation if AI backend unavailable
- Redis cache failures don't break core functionality
- Database connection pooling prevents overload

### 6.4 Security
- All API endpoints require authentication (production)
- Patient data encrypted at rest
- TLS encryption for all network traffic
- Audit logs are immutable
- File uploads validated for type and size
- SQL injection prevention via parameterized queries
- XSS prevention via input sanitization

### 6.5 Compliance
- HIPAA-compliant audit logging
- Immutable audit trail for all checks and overrides
- Patient data access logging
- Secure file storage with encryption

### 6.6 Usability
- Intuitive web interface for doctors and patients
- Clear visual signals (GREEN/YELLOW/RED)
- Detailed reasoning for all AI decisions
- Mobile-responsive design
- Accessible UI components

### 6.7 Maintainability
- Modular backend architecture
- Pluggable AI backends (Gemini, Ollama, HuggingFace)
- Comprehensive error logging with structlog
- Database migrations support
- Environment-based configuration

### 6.8 Reliability
- Automatic database table creation on startup
- Health check endpoints for monitoring
- Graceful error handling throughout
- Retry logic for external API calls
- Fallback mechanisms when AI unavailable

## 7. Technical Constraints

### 7.1 Technology Stack
- Backend: Python 3.11+, FastAPI
- Frontend: Next.js 16+, React 18+, TypeScript
- Database: PostgreSQL 16+ with pg_trgm extension
- Cache: Redis/Valkey
- AI: Google Gemini API (primary), Ollama, HuggingFace (alternatives)
- Storage: AWS S3 or MinIO
- Deployment: AWS ECS Fargate

### 7.2 External Dependencies
- Google Gemini API for AI analysis
- OpenFDA API for drug information (optional)
- DailyMed for drug labels (optional)
- AWS S3 for file storage (production)

### 7.3 Data Formats
- API: JSON over HTTP/HTTPS
- Images: JPEG, PNG, WebP
- Documents: PDF
- Database: PostgreSQL with JSONB for structured data

## 8. Future Enhancements

### 8.1 Phase 2 Features
- Integration with EHR systems via FHIR R4
- Real-time notifications for critical allergies
- Mobile app for doctors
- Barcode scanning for drug identification
- Multi-language support

### 8.2 Phase 3 Features
- Machine learning model for allergy prediction
- Drug interaction checking beyond allergies
- Dosage calculation based on patient weight
- Integration with pharmacy systems
- Telemedicine consultation features

## 9. Success Metrics

### 9.1 Clinical Metrics
- Zero false negatives (missed allergies)
- < 5% false positives (unnecessary warnings)
- 100% of critical allergies detected
- < 1% doctor override rate for RED signals

### 9.2 Performance Metrics
- 95th percentile response time < 5 seconds
- 99.9% API availability
- < 0.1% error rate

### 9.3 Adoption Metrics
- 100+ active doctors within 6 months
- 10,000+ patients in system within 1 year
- 1,000+ prescription checks per day
- 90% user satisfaction score

## 10. Glossary

- **Allergen**: A substance that causes an allergic reaction
- **Cross-reactivity**: When proteins in one substance are similar to proteins in another, causing allergic reactions to both
- **Criticality**: The potential severity of an allergic reaction
- **Contraindication**: A condition or factor that makes a particular treatment inadvisable
- **Lab Sensitivity**: Elevated lab markers (e.g., IgE) indicating potential allergic response
- **OCR**: Optical Character Recognition - extracting text from images
- **Signal**: Risk classification (GREEN/YELLOW/RED) for prescription safety
- **Override**: Doctor's decision to proceed despite a RED warning
- **Audit Trail**: Immutable log of all system actions for compliance
