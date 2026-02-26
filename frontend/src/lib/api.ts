const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface DrugResult {
  rxcui: string;
  name: string;
  generic_name?: string;
  dosage_form?: string;
  route?: string;
  brand_names?: string[];
  id: string;
}

export interface Warning {
  warning_id: string;
  severity: string;
  type: string;
  ingredient: string;
  allergen: string;
  message: string;
  reasoning?: string;
  evidence: { source: string; detail: string };
}

export interface AlternativeDrug {
  rxcui: string;
  name: string;
  reason: string;
  signal: string;
}

export interface DrugCheckResult {
  drug: { rxcui: string; name: string };
  signal: 'GREEN' | 'YELLOW' | 'RED';
  reasoning?: string;
  warnings: Warning[];
  alternatives: AlternativeDrug[];
}

export interface Citation {
  source: string;
  url: string;
}

export interface PrescriptionCheckResponse {
  request_id: string;
  patient_id: string;
  overall_signal: 'GREEN' | 'YELLOW' | 'RED';
  drug_results: DrugCheckResult[];
  processing_time_ms: number;
  ocr_confidence?: number;
  extracted_drugs?: string[];
  citations?: Citation[];
}

export interface PatientReport {
  id: string;
  filename: string;
  file_size: number;
  content_type: string;
  status: string;
  version: number;
  is_latest: boolean;
  extracted_text?: string;
  uploaded_at: string;
  extracted_at?: string;
}

export interface PatientAllergyProfile {
  id: string;
  external_id: string;
  name: string;
  age?: number;
  gender?: string;
  allergies: {
    id: string;
    allergen_name: string;
    category: string;
    criticality: string;
    reaction_manifestations?: string[];
    reaction_severity?: string;
    verification_status: string;
  }[];
  lab_sensitivities: {
    id: string;
    test_name: string;
    value: number;
    unit: string;
    interpretation: string;
    related_substances?: string[];
  }[];
  conditions: {
    id: string;
    condition_name: string;
    contraindicated_ingredients?: string[];
  }[];
}

export async function searchDrugs(query: string): Promise<{ results: DrugResult[]; total: number }> {
  const res = await fetch(`${API_BASE}/api/v1/drugs/search?q=${encodeURIComponent(query)}&limit=10`);
  if (!res.ok) throw new Error('Drug search failed');
  return res.json();
}

export async function getPatientProfile(patientId: string): Promise<PatientAllergyProfile> {
  const res = await fetch(`${API_BASE}/api/v1/patients/${encodeURIComponent(patientId)}/allergy-profile`);
  if (!res.ok) throw new Error('Patient not found');
  return res.json();
}

export async function checkPrescription(
  patientId: string,
  drugs: { rxcui?: string; name?: string }[],
): Promise<PrescriptionCheckResponse> {
  const res = await fetch(`${API_BASE}/api/v1/prescription/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_id: patientId, drugs }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Prescription check failed');
  }
  return res.json();
}

export async function checkPrescriptionPhoto(
  patientId: string,
  imageFile: File,
): Promise<PrescriptionCheckResponse> {
  const formData = new FormData();
  formData.append('patient_id', patientId);
  formData.append('image', imageFile);

  const res = await fetch(`${API_BASE}/api/v1/prescription/check/photo`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === 'string' ? err.detail : err.detail?.message || 'OCR check failed');
  }
  return res.json();
}

export async function overridePrescription(
  requestId: string,
  warningIds: string[],
  justification: string,
): Promise<{ audit_id: string; status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/prescription/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      request_id: requestId,
      overridden_warnings: warningIds,
      clinical_justification: justification,
      digital_signature: 'dev-signature',
    }),
  });
  if (!res.ok) throw new Error('Override failed');
  return res.json();
}

export async function uploadReport(
  patientId: string,
  file: File,
): Promise<PatientReport> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/v1/patients/${encodeURIComponent(patientId)}/reports`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Report upload failed');
  }
  return res.json();
}

export async function getReports(
  patientId: string,
): Promise<{ reports: PatientReport[]; total: number }> {
  const res = await fetch(`${API_BASE}/api/v1/patients/${encodeURIComponent(patientId)}/reports`);
  if (!res.ok) throw new Error('Failed to load reports');
  return res.json();
}

export async function replaceReport(
  patientId: string,
  reportId: string,
  file: File,
): Promise<PatientReport> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(
    `${API_BASE}/api/v1/patients/${encodeURIComponent(patientId)}/reports/${encodeURIComponent(reportId)}`,
    { method: 'PUT', body: formData },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Report replace failed');
  }
  return res.json();
}
