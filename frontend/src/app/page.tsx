'use client';

import { useState, useRef, useCallback } from 'react';
import {
  searchDrugs,
  getPatientProfile,
  checkPrescription,
  checkPrescriptionPhoto,
  overridePrescription,
  uploadReport,
  getReports,
  deleteReport,
  type DrugResult,
  type PatientAllergyProfile,
  type PrescriptionCheckResponse,
  type DrugCheckResult,
  type PatientReport,
} from '@/lib/api';

export default function Home() {
  // Patient state
  const [patientId, setPatientId] = useState('');
  const [patient, setPatient] = useState<PatientAllergyProfile | null>(null);
  const [patientLoading, setPatientLoading] = useState(false);
  const [patientError, setPatientError] = useState('');

  // Drug search state
  const [drugQuery, setDrugQuery] = useState('');
  const [drugResults, setDrugResults] = useState<DrugResult[]>([]);
  const [selectedDrugs, setSelectedDrugs] = useState<{ rxcui?: string; name: string }[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchTimeout = useRef<NodeJS.Timeout | null>(null);

  // Check result state
  const [checkResult, setCheckResult] = useState<PrescriptionCheckResponse | null>(null);
  const [checking, setChecking] = useState(false);
  const [checkError, setCheckError] = useState('');

  // Photo upload state
  const [photoMode, setPhotoMode] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Override state
  const [overrideModal, setOverrideModal] = useState<DrugCheckResult | null>(null);
  const [overrideJustification, setOverrideJustification] = useState('');
  const [overrideLoading, setOverrideLoading] = useState(false);

  // Report state
  const [reports, setReports] = useState<PatientReport[]>([]);
  const [reportUploading, setReportUploading] = useState(false);
  const reportInputRef = useRef<HTMLInputElement>(null);

  // --- Patient lookup ---
  const loadPatient = useCallback(async () => {
    if (!patientId.trim()) return;
    setPatientLoading(true);
    setPatientError('');
    setPatient(null);
    setCheckResult(null);
    setReports([]);
    try {
      const profile = await getPatientProfile(patientId.trim());
      setPatient(profile);
      // Load reports for this patient
      try {
        const rData = await getReports(patientId.trim());
        setReports(rData.reports);
      } catch { /* no reports yet */ }
    } catch (e: any) {
      setPatientError(e.message || 'Patient not found');
    } finally {
      setPatientLoading(false);
    }
  }, [patientId]);

  // --- Report upload ---
  const handleReportUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file || !patient) return;
      setReportUploading(true);
      try {
        const report = await uploadReport(patient.external_id, file);
        setReports((prev) => [report, ...prev]);
      } catch (err: any) {
        alert('Report upload failed: ' + (err.message || 'Unknown error'));
      } finally {
        setReportUploading(false);
        if (reportInputRef.current) reportInputRef.current.value = '';
      }
    },
    [patient],
  );

  const handleDeleteReport = useCallback(
    async (reportId: string) => {
      if (!patient) return;
      try {
        await deleteReport(patient.external_id, reportId);
        setReports((prev) => prev.filter((r) => r.id !== reportId));
      } catch (err: any) {
        alert('Delete failed: ' + (err.message || 'Unknown error'));
      }
    },
    [patient],
  );

  // --- Drug search ---
  const handleDrugSearch = useCallback(
    (query: string) => {
      setDrugQuery(query);
      if (searchTimeout.current) clearTimeout(searchTimeout.current);
      if (query.length < 2) {
        setDrugResults([]);
        setShowDropdown(false);
        return;
      }
      searchTimeout.current = setTimeout(async () => {
        try {
          const data = await searchDrugs(query);
          setDrugResults(data.results);
          setShowDropdown(true);
        } catch {
          setDrugResults([]);
        }
      }, 300);
    },
    [],
  );

  const addDrug = useCallback((drug: DrugResult) => {
    setSelectedDrugs((prev) => {
      if (prev.some((d) => d.rxcui === drug.rxcui)) return prev;
      return [...prev, { rxcui: drug.rxcui, name: drug.name }];
    });
    setDrugQuery('');
    setShowDropdown(false);
  }, []);

  const removeDrug = useCallback((index: number) => {
    setSelectedDrugs((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // --- Prescription check (manual) ---
  const handleManualCheck = useCallback(async () => {
    if (!patient || selectedDrugs.length === 0) return;
    setChecking(true);
    setCheckError('');
    setCheckResult(null);
    try {
      const result = await checkPrescription(patient.external_id, selectedDrugs);
      setCheckResult(result);
    } catch (e: any) {
      setCheckError(e.message || 'Check failed');
    } finally {
      setChecking(false);
    }
  }, [patient, selectedDrugs]);

  // --- Prescription check (photo) ---
  const handlePhotoUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file || !patient) return;
      setChecking(true);
      setCheckError('');
      setCheckResult(null);
      try {
        const result = await checkPrescriptionPhoto(patient.external_id, file);
        setCheckResult(result);
      } catch (e: any) {
        setCheckError(e.message || 'Photo check failed');
      } finally {
        setChecking(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    },
    [patient],
  );

  // --- Override ---
  const handleOverride = useCallback(async () => {
    if (!overrideModal || !checkResult || !overrideJustification.trim()) return;
    setOverrideLoading(true);
    try {
      const warningIds = overrideModal.warnings.map((w) => w.warning_id);
      await overridePrescription(checkResult.request_id, warningIds, overrideJustification);
      setOverrideModal(null);
      setOverrideJustification('');
      alert('Override recorded successfully. This action has been logged for audit.');
    } catch (e: any) {
      alert('Override failed: ' + (e.message || 'Unknown error'));
    } finally {
      setOverrideLoading(false);
    }
  }, [overrideModal, checkResult, overrideJustification]);

  const signalColor = (signal: string) => {
    switch (signal) {
      case 'RED': return 'bg-red-500';
      case 'YELLOW': return 'bg-yellow-400';
      case 'GREEN': return 'bg-green-500';
      default: return 'bg-gray-400';
    }
  };

  const signalBorder = (signal: string) => {
    switch (signal) {
      case 'RED': return 'border-red-500 bg-red-50';
      case 'YELLOW': return 'border-yellow-400 bg-yellow-50';
      case 'GREEN': return 'border-green-500 bg-green-50';
      default: return 'border-gray-300 bg-gray-50';
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <header className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">MedGuard</h1>
            <p className="text-sm text-gray-500">Medicine Allergy Detection System</p>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Patient + Drug input */}
        <div className="lg:col-span-2 space-y-6">
          {/* Step 1: Patient Selection */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <span className="w-7 h-7 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold">1</span>
              Select Patient
            </h2>
            <div className="flex gap-3">
              <input
                type="text"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadPatient()}
                placeholder="Enter Patient ID (e.g., P-5678)"
                className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-900"
              />
              <button
                onClick={loadPatient}
                disabled={patientLoading || !patientId.trim()}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
              >
                {patientLoading ? 'Loading...' : 'Load'}
              </button>
            </div>
            {patientError && <p className="mt-2 text-sm text-red-600">{patientError}</p>}
            <p className="mt-2 text-xs text-gray-400">Demo patients: P-5678 (John Doe, Penicillin allergy) or P-1234 (Jane Smith, Aspirin allergy)</p>
          </div>

          {/* Step 2: Drug Entry */}
          {patient && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <span className="w-7 h-7 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold">2</span>
                Enter Prescription
              </h2>

              {/* Toggle: Manual / Photo */}
              <div className="flex gap-2 mb-4">
                <button
                  onClick={() => setPhotoMode(false)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${!photoMode ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                >
                  Manual Entry
                </button>
                <button
                  onClick={() => setPhotoMode(true)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${photoMode ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                >
                  Photo Upload
                </button>
              </div>

              {!photoMode ? (
                <>
                  {/* Drug search */}
                  <div className="relative mb-4">
                    <input
                      type="text"
                      value={drugQuery}
                      onChange={(e) => handleDrugSearch(e.target.value)}
                      onFocus={() => drugResults.length > 0 && setShowDropdown(true)}
                      onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
                      placeholder="Search drug name (e.g., Amoxicillin, Ibuprofen)..."
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-900"
                    />
                    {showDropdown && drugResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                        {drugResults.map((drug) => (
                          <button
                            key={drug.id}
                            onMouseDown={() => addDrug(drug)}
                            className="w-full text-left px-4 py-3 hover:bg-blue-50 border-b border-gray-100 last:border-0"
                          >
                            <div className="font-medium text-gray-900">{drug.name}</div>
                            <div className="text-xs text-gray-500">
                              {drug.generic_name} {drug.dosage_form && `| ${drug.dosage_form}`} {drug.route && `| ${drug.route}`}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Selected drugs */}
                  {selectedDrugs.length > 0 && (
                    <div className="space-y-2 mb-4">
                      {selectedDrugs.map((drug, i) => (
                        <div key={i} className="flex items-center justify-between bg-gray-50 px-4 py-2.5 rounded-lg">
                          <span className="text-gray-800 font-medium">{drug.name}</span>
                          <button onClick={() => removeDrug(i)} className="text-red-500 hover:text-red-700 text-sm font-medium">
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    onClick={handleManualCheck}
                    disabled={checking || selectedDrugs.length === 0}
                    className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold text-lg transition-colors"
                  >
                    {checking ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                        Checking Allergies...
                      </span>
                    ) : 'Check for Allergies'}
                  </button>
                </>
              ) : (
                /* Photo upload */
                <div>
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
                  >
                    <svg className="w-12 h-12 mx-auto text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <p className="text-gray-600 font-medium">Click to upload prescription photo</p>
                    <p className="text-sm text-gray-400 mt-1">JPEG, PNG, or WebP (max 10MB)</p>
                    {checking && (
                      <div className="mt-4 flex items-center justify-center gap-2 text-blue-600">
                        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                        Processing with MedGemma AI...
                      </div>
                    )}
                  </div>
                  <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handlePhotoUpload} />
                </div>
              )}

              {checkError && <p className="mt-3 text-sm text-red-600 bg-red-50 p-3 rounded-lg">{checkError}</p>}
            </div>
          )}

          {/* Step 3: Results */}
          {checkResult && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <span className="w-7 h-7 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold">3</span>
                Allergy Check Results
              </h2>

              {/* Overall signal */}
              <div className={`flex items-center gap-4 p-4 rounded-xl border-2 mb-6 ${signalBorder(checkResult.overall_signal)}`}>
                <div className={`w-16 h-16 rounded-full ${signalColor(checkResult.overall_signal)} flex items-center justify-center flex-shrink-0`}>
                  {checkResult.overall_signal === 'GREEN' && <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                  {checkResult.overall_signal === 'YELLOW' && <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 9v2m0 4h.01M12 3l9.66 16.5H2.34L12 3z" /></svg>}
                  {checkResult.overall_signal === 'RED' && <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" /></svg>}
                </div>
                <div>
                  <p className="text-xl font-bold text-gray-900">
                    {checkResult.overall_signal === 'GREEN' && 'Safe to Prescribe'}
                    {checkResult.overall_signal === 'YELLOW' && 'Review Recommended'}
                    {checkResult.overall_signal === 'RED' && 'DO NOT PRESCRIBE'}
                  </p>
                  <p className="text-sm text-gray-600">
                    Processed in {checkResult.processing_time_ms}ms
                    {checkResult.ocr_confidence != null && ` | OCR confidence: ${(checkResult.ocr_confidence * 100).toFixed(0)}%`}
                  </p>
                </div>
              </div>

              {/* OCR extracted drugs */}
              {checkResult.extracted_drugs && checkResult.extracted_drugs.length > 0 && (
                <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm font-medium text-blue-800">Extracted from photo:</p>
                  <p className="text-sm text-blue-700">{checkResult.extracted_drugs.join(', ')}</p>
                </div>
              )}

              {/* Citations */}
              {checkResult.citations && checkResult.citations.length > 0 && (
                <div className="mb-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
                  <p className="text-sm font-semibold text-indigo-800 mb-2">References & Citations</p>
                  <div className="space-y-1">
                    {checkResult.citations.map((c, ci) => (
                      <a
                        key={ci}
                        href={c.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800 hover:underline"
                      >
                        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                        {c.source}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Per-drug results */}
              <div className="space-y-4">
                {checkResult.drug_results.map((dr, i) => (
                  <div key={i} className={`border-2 rounded-xl p-4 ${signalBorder(dr.signal)}`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <div className={`w-4 h-4 rounded-full ${signalColor(dr.signal)}`} />
                        <span className="font-semibold text-gray-900">{dr.drug.name || 'Unknown Drug'}</span>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold text-white ${signalColor(dr.signal)}`}>
                        {dr.signal}
                      </span>
                    </div>

                    {/* Warnings */}
                    {dr.warnings.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {dr.warnings.map((w, wi) => (
                          <div key={wi} className="bg-white/70 rounded-lg p-3 border border-gray-200">
                            <div className="flex items-start gap-2">
                              <span className={`px-2 py-0.5 rounded text-xs font-bold text-white flex-shrink-0 mt-0.5 ${w.severity === 'CRITICAL' ? 'bg-red-600' : w.severity === 'HIGH' ? 'bg-orange-500' : w.severity === 'MODERATE' ? 'bg-yellow-500' : 'bg-gray-400'}`}>
                                {w.severity}
                              </span>
                              <div>
                                <p className="text-sm text-gray-800 font-medium">{w.message}</p>
                                <p className="text-xs text-gray-500 mt-1">
                                  Source: {w.evidence.source} | {w.evidence.detail}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Alternatives */}
                    {dr.alternatives.length > 0 && (
                      <div className="mt-3">
                        <p className="text-sm font-medium text-gray-700 mb-2">Safe Alternatives (AI-suggested):</p>
                        <div className="space-y-1">
                          {dr.alternatives.map((alt, ai) => (
                            <div key={ai} className="flex items-center gap-2 bg-green-50 px-3 py-2 rounded-lg">
                              <div className="w-3 h-3 rounded-full bg-green-500 flex-shrink-0" />
                              <div>
                                <span className="text-sm font-medium text-green-800">{alt.name}</span>
                                <span className="text-xs text-green-600 ml-2">{alt.reason}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Override button for RED signals */}
                    {dr.signal === 'RED' && (
                      <button
                        onClick={() => setOverrideModal(dr)}
                        className="mt-3 px-4 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium hover:bg-red-200 transition-colors"
                      >
                        Override &amp; Prescribe Anyway
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right column: Patient profile */}
        <div className="space-y-6">
          {patient && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 sticky top-6">
              <h3 className="font-semibold text-gray-800 mb-4">Patient Profile</h3>
              <div className="space-y-3">
                <div>
                  <p className="text-lg font-bold text-gray-900">{patient.name}</p>
                  <p className="text-sm text-gray-500">
                    ID: {patient.external_id} {patient.age && `| Age: ${patient.age}`} {patient.gender && `| ${patient.gender}`}
                  </p>
                </div>

                {/* Known allergies */}
                {patient.allergies.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-red-700 mb-1">Known Allergies</p>
                    {patient.allergies.map((a) => (
                      <div key={a.id} className="bg-red-50 border border-red-200 rounded-lg p-2.5 mb-1.5">
                        <p className="font-medium text-red-800 text-sm">{a.allergen_name}</p>
                        <p className="text-xs text-red-600">
                          {a.criticality} criticality | {a.verification_status}
                          {a.reaction_manifestations && a.reaction_manifestations.length > 0 && ` | ${a.reaction_manifestations.join(', ')}`}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Lab sensitivities */}
                {patient.lab_sensitivities.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-yellow-700 mb-1">Lab Sensitivities</p>
                    {patient.lab_sensitivities.map((ls) => (
                      <div key={ls.id} className="bg-yellow-50 border border-yellow-200 rounded-lg p-2.5 mb-1.5">
                        <p className="font-medium text-yellow-800 text-sm">{ls.test_name}</p>
                        <p className="text-xs text-yellow-600">
                          {ls.value} {ls.unit} ({ls.interpretation})
                          {ls.related_substances && ls.related_substances.length > 0 && ` | Related: ${ls.related_substances.join(', ')}`}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Conditions */}
                {patient.conditions.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-purple-700 mb-1">Conditions</p>
                    {patient.conditions.map((c) => (
                      <div key={c.id} className="bg-purple-50 border border-purple-200 rounded-lg p-2.5 mb-1.5">
                        <p className="font-medium text-purple-800 text-sm">{c.condition_name}</p>
                        {c.contraindicated_ingredients && c.contraindicated_ingredients.length > 0 && (
                          <p className="text-xs text-purple-600">Avoid: {c.contraindicated_ingredients.join(', ')}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {patient.allergies.length === 0 && patient.lab_sensitivities.length === 0 && patient.conditions.length === 0 && (
                  <p className="text-sm text-gray-400 italic">No known allergies or conditions on file.</p>
                )}
              </div>
            </div>
          )}

          {/* Patient Reports */}
          {patient && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-800">Patient Reports</h3>
                <button
                  onClick={() => reportInputRef.current?.click()}
                  disabled={reportUploading}
                  className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {reportUploading ? 'Uploading...' : '+ Upload'}
                </button>
                <input
                  ref={reportInputRef}
                  type="file"
                  accept="application/pdf,image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={handleReportUpload}
                />
              </div>

              {reports.length > 0 ? (
                <div className="space-y-2">
                  {reports.map((r) => (
                    <div key={r.id} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                      <div className="flex items-start justify-between">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-gray-800 truncate" title={r.filename}>
                            {r.filename}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {(r.file_size / 1024).toFixed(1)} KB
                            {' | '}
                            <span className={`font-medium ${
                              r.status === 'ready' ? 'text-green-600' :
                              r.status === 'extracting' ? 'text-yellow-600' :
                              r.status === 'failed' ? 'text-red-600' : 'text-gray-500'
                            }`}>
                              {r.status === 'ready' ? 'Indexed' :
                               r.status === 'extracting' ? 'Processing...' :
                               r.status === 'failed' ? 'Failed' : 'Pending'}
                            </span>
                          </p>
                        </div>
                        <button
                          onClick={() => handleDeleteReport(r.id)}
                          className="text-red-400 hover:text-red-600 text-xs ml-2 flex-shrink-0"
                          title="Delete report"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400 italic">No reports uploaded yet. Upload lab reports or medical documents to enhance allergy checks.</p>
              )}
            </div>
          )}

          {!patient && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="font-semibold text-gray-800 mb-2">Getting Started</h3>
              <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
                <li>Enter a patient ID to load their allergy profile</li>
                <li>Search and select drugs, or upload a prescription photo</li>
                <li>The system checks ingredients against known allergies</li>
                <li>Review the GREEN / YELLOW / RED signal</li>
              </ol>
            </div>
          )}
        </div>
      </div>

      {/* Override Modal */}
      {overrideModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6">
            <h3 className="text-lg font-bold text-red-700 mb-2">Override Warning</h3>
            <p className="text-sm text-gray-600 mb-4">
              You are about to override a RED signal for <strong>{overrideModal.drug.name}</strong>.
              This action will be permanently logged for audit purposes.
            </p>

            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              {overrideModal.warnings.map((w, i) => (
                <p key={i} className="text-sm text-red-700">{w.message}</p>
              ))}
            </div>

            <label className="block text-sm font-medium text-gray-700 mb-1">
              Clinical Justification (required)
            </label>
            <textarea
              value={overrideJustification}
              onChange={(e) => setOverrideJustification(e.target.value)}
              placeholder="Enter your clinical justification for overriding this warning..."
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none text-gray-900 mb-4"
            />

            <div className="flex gap-3">
              <button
                onClick={() => { setOverrideModal(null); setOverrideJustification(''); }}
                className="flex-1 py-2.5 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleOverride}
                disabled={!overrideJustification.trim() || overrideLoading}
                className="flex-1 py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {overrideLoading ? 'Recording...' : 'Confirm Override'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
