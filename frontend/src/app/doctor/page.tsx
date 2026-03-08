'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import Link from 'next/link';
import {
  searchDrugs,
  getPatientProfile,
  checkPrescription,
  checkPrescriptionPhoto,
  overridePrescription,
  uploadReport,
  getReports,
  replaceReport,
  askAI,
  createPatient,
  addAllergy,
  addCondition,
  type DrugResult,
  type PatientAllergyProfile,
  type PrescriptionCheckResponse,
  type DrugCheckResult,
  type PatientReport,
  type ChatMessage,
} from '@/lib/api';

export default function DoctorPortal() {
  // Tab state
  const [activeTab, setActiveTab] = useState<'patients' | 'analysis' | 'chat'>('patients');

  // Patient state
  const [patientId, setPatientId] = useState('');
  const [patient, setPatient] = useState<PatientAllergyProfile | null>(null);
  const [patientLoading, setPatientLoading] = useState(false);
  const [patientError, setPatientError] = useState('');

  // New patient form
  const [showNewPatient, setShowNewPatient] = useState(false);
  const [newPatient, setNewPatient] = useState({ external_id: '', name: '', age: '', gender: '', weight_kg: '' });
  const [newPatientError, setNewPatientError] = useState('');

  // New allergy form
  const [showAddAllergy, setShowAddAllergy] = useState(false);
  const [newAllergy, setNewAllergy] = useState({ allergen_name: '', category: 'drug', criticality: 'high', reaction_severity: '', reaction_manifestations: '' });

  // New condition form
  const [showAddCondition, setShowAddCondition] = useState(false);
  const [newCondition, setNewCondition] = useState({ condition_name: '', contraindicated_ingredients: '' });

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
  const [replacingReportId, setReplacingReportId] = useState<string | null>(null);
  const reportInputRef = useRef<HTMLInputElement>(null);
  const replaceInputRef = useRef<HTMLInputElement>(null);

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatMedicine, setChatMedicine] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // --- Patient lookup ---
  const loadPatient = useCallback(async () => {
    if (!patientId.trim()) return;
    setPatientLoading(true);
    setPatientError('');
    setPatient(null);
    setCheckResult(null);
    setReports([]);
    setChatMessages([]);
    try {
      const profile = await getPatientProfile(patientId.trim());
      setPatient(profile);
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

  // --- Create patient ---
  const handleCreatePatient = useCallback(async () => {
    if (!newPatient.external_id.trim() || !newPatient.name.trim()) return;
    setNewPatientError('');
    try {
      await createPatient({
        external_id: newPatient.external_id.trim(),
        name: newPatient.name.trim(),
        age: newPatient.age ? parseInt(newPatient.age) : undefined,
        gender: newPatient.gender || undefined,
        weight_kg: newPatient.weight_kg ? parseFloat(newPatient.weight_kg) : undefined,
      });
      setPatientId(newPatient.external_id.trim());
      setNewPatient({ external_id: '', name: '', age: '', gender: '', weight_kg: '' });
      setShowNewPatient(false);
      // Auto-load the new patient
      setPatientLoading(true);
      const profile = await getPatientProfile(newPatient.external_id.trim());
      setPatient(profile);
      setPatientLoading(false);
    } catch (e: any) {
      setNewPatientError(e.message || 'Failed to create patient');
      setPatientLoading(false);
    }
  }, [newPatient]);

  // --- Add allergy ---
  const handleAddAllergy = useCallback(async () => {
    if (!patient || !newAllergy.allergen_name.trim()) return;
    try {
      await addAllergy(patient.external_id, {
        allergen_name: newAllergy.allergen_name.trim(),
        category: newAllergy.category,
        criticality: newAllergy.criticality,
        reaction_severity: newAllergy.reaction_severity || undefined,
        reaction_manifestations: newAllergy.reaction_manifestations ? newAllergy.reaction_manifestations.split(',').map(s => s.trim()).filter(Boolean) : undefined,
      });
      setNewAllergy({ allergen_name: '', category: 'drug', criticality: 'high', reaction_severity: '', reaction_manifestations: '' });
      setShowAddAllergy(false);
      // Reload patient
      const profile = await getPatientProfile(patient.external_id);
      setPatient(profile);
    } catch (e: any) {
      alert('Failed to add allergy: ' + (e.message || 'Unknown error'));
    }
  }, [patient, newAllergy]);

  // --- Add condition ---
  const handleAddCondition = useCallback(async () => {
    if (!patient || !newCondition.condition_name.trim()) return;
    try {
      await addCondition(patient.external_id, {
        condition_name: newCondition.condition_name.trim(),
        contraindicated_ingredients: newCondition.contraindicated_ingredients ? newCondition.contraindicated_ingredients.split(',').map(s => s.trim()).filter(Boolean) : undefined,
      });
      setNewCondition({ condition_name: '', contraindicated_ingredients: '' });
      setShowAddCondition(false);
      const profile = await getPatientProfile(patient.external_id);
      setPatient(profile);
    } catch (e: any) {
      alert('Failed to add condition: ' + (e.message || 'Unknown error'));
    }
  }, [patient, newCondition]);

  // --- Report upload ---
  const handleReportUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
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
  }, [patient]);

  const handleReplaceReport = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !patient || !replacingReportId) return;
    setReportUploading(true);
    try {
      const updated = await replaceReport(patient.external_id, replacingReportId, file);
      setReports((prev) => prev.map((r) => (r.id === replacingReportId ? updated : r)));
    } catch (err: any) {
      alert('Replace failed: ' + (err.message || 'Unknown error'));
    } finally {
      setReportUploading(false);
      setReplacingReportId(null);
      if (replaceInputRef.current) replaceInputRef.current.value = '';
    }
  }, [patient, replacingReportId]);

  // --- Drug search ---
  const handleDrugSearch = useCallback((query: string) => {
    setDrugQuery(query);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (query.length < 2) { setDrugResults([]); setShowDropdown(false); return; }
    searchTimeout.current = setTimeout(async () => {
      try {
        const data = await searchDrugs(query);
        setDrugResults(data.results);
        setShowDropdown(true);
      } catch { setDrugResults([]); }
    }, 300);
  }, []);

  const addDrug = useCallback((drug: DrugResult) => {
    setSelectedDrugs((prev) => {
      if (prev.some((d) => d.rxcui === drug.rxcui)) return prev;
      return [...prev, { rxcui: drug.rxcui, name: drug.name }];
    });
    setDrugQuery(''); setShowDropdown(false);
  }, []);

  const addDrugByName = useCallback((name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setSelectedDrugs((prev) => {
      if (prev.some((d) => d.name.toLowerCase() === trimmed.toLowerCase())) return prev;
      return [...prev, { name: trimmed }];
    });
    setDrugQuery(''); setDrugResults([]); setShowDropdown(false);
  }, []);

  const removeDrug = useCallback((index: number) => {
    setSelectedDrugs((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // --- Prescription check ---
  const handleManualCheck = useCallback(async () => {
    if (!patient || selectedDrugs.length === 0) return;
    setChecking(true); setCheckError(''); setCheckResult(null);
    try {
      const result = await checkPrescription(patient.external_id, selectedDrugs);
      setCheckResult(result);
    } catch (e: any) { setCheckError(e.message || 'Check failed'); }
    finally { setChecking(false); }
  }, [patient, selectedDrugs]);

  const handlePhotoUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !patient) return;
    setChecking(true); setCheckError(''); setCheckResult(null);
    try {
      const result = await checkPrescriptionPhoto(patient.external_id, file);
      setCheckResult(result);
    } catch (e: any) { setCheckError(e.message || 'Photo check failed'); }
    finally { setChecking(false); if (fileInputRef.current) fileInputRef.current.value = ''; }
  }, [patient]);

  // --- Override ---
  const handleOverride = useCallback(async () => {
    if (!overrideModal || !checkResult || !overrideJustification.trim()) return;
    setOverrideLoading(true);
    try {
      const warningIds = overrideModal.warnings.map((w) => w.warning_id);
      await overridePrescription(checkResult.request_id, warningIds, overrideJustification);
      setOverrideModal(null); setOverrideJustification('');
      alert('Override recorded successfully.');
    } catch (e: any) { alert('Override failed: ' + (e.message || 'Unknown error')); }
    finally { setOverrideLoading(false); }
  }, [overrideModal, checkResult, overrideJustification]);

  // --- AI Chat ---
  const handleChat = useCallback(async () => {
    if (!patient || !chatInput.trim()) return;
    const question = chatInput.trim();
    setChatInput('');
    setChatMessages((prev) => [...prev, { role: 'user', content: question }]);
    setChatLoading(true);
    try {
      const res = await askAI(patient.external_id, question, chatMedicine, chatMessages);
      setChatMessages((prev) => [...prev, { role: 'assistant', content: res.answer }]);
    } catch (e: any) {
      setChatMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${e.message}` }]);
    } finally { setChatLoading(false); }
  }, [patient, chatInput, chatMedicine, chatMessages]);

  const signalColor = (s: string) => s === 'RED' ? 'bg-red-500' : s === 'YELLOW' ? 'bg-yellow-400' : s === 'GREEN' ? 'bg-green-500' : 'bg-gray-400';
  const signalBorder = (s: string) => s === 'RED' ? 'border-red-500 bg-red-50' : s === 'YELLOW' ? 'border-yellow-400 bg-yellow-50' : s === 'GREEN' ? 'border-green-500 bg-green-50' : 'border-gray-300 bg-gray-50';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">AllerSense</h1>
                <p className="text-xs text-gray-400">Doctor Portal</p>
              </div>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            {patient && (
              <span className="text-sm text-gray-500 mr-2">
                Patient: <span className="font-semibold text-gray-800">{patient.name}</span> ({patient.external_id})
              </span>
            )}
            <Link href="/" className="text-sm text-gray-500 hover:text-gray-700">Home</Link>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Patient Selection Bar */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-3 flex-wrap">
            <input type="text" value={patientId} onChange={(e) => setPatientId(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && loadPatient()} placeholder="Enter Patient ID..." className="flex-1 min-w-[200px] px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-900" />
            <button onClick={loadPatient} disabled={patientLoading || !patientId.trim()} className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium transition-colors">
              {patientLoading ? 'Loading...' : 'Load Patient'}
            </button>
            <button onClick={() => setShowNewPatient(true)} className="px-4 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium transition-colors">
              + New Patient
            </button>
          </div>
          {patientError && <p className="mt-2 text-sm text-red-600">{patientError}</p>}
        </div>

        {/* New Patient Modal */}
        {showNewPatient && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Create New Patient</h3>
              <div className="space-y-3">
                <input type="text" placeholder="Patient ID (e.g., P-9999)" value={newPatient.external_id} onChange={(e) => setNewPatient({ ...newPatient, external_id: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
                <input type="text" placeholder="Full Name" value={newPatient.name} onChange={(e) => setNewPatient({ ...newPatient, name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
                <div className="grid grid-cols-3 gap-3">
                  <input type="number" placeholder="Age" value={newPatient.age} onChange={(e) => setNewPatient({ ...newPatient, age: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
                  <select value={newPatient.gender} onChange={(e) => setNewPatient({ ...newPatient, gender: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="">Gender</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                  <input type="number" placeholder="Weight (kg)" value={newPatient.weight_kg} onChange={(e) => setNewPatient({ ...newPatient, weight_kg: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              {newPatientError && <p className="mt-2 text-sm text-red-600">{newPatientError}</p>}
              <div className="flex gap-3 mt-4">
                <button onClick={() => setShowNewPatient(false)} className="flex-1 py-2.5 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200">Cancel</button>
                <button onClick={handleCreatePatient} disabled={!newPatient.external_id.trim() || !newPatient.name.trim()} className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50">Create</button>
              </div>
            </div>
          </div>
        )}

        {patient && (
          <>
            {/* Tabs */}
            <div className="flex gap-1 mb-6 bg-gray-100 rounded-xl p-1">
              {(['patients', 'analysis', 'chat'] as const).map((tab) => (
                <button key={tab} onClick={() => setActiveTab(tab)} className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-semibold transition-colors capitalize ${activeTab === tab ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
                  {tab === 'patients' ? 'Patient Profile & Data' : tab === 'analysis' ? 'Allergy Analysis' : 'AI Chat'}
                </button>
              ))}
            </div>

            {/* TAB 1: Patient Profile & Data */}
            {activeTab === 'patients' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Patient Info */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-semibold text-gray-800 mb-4 text-lg">Patient Info</h3>
                  <div className="space-y-2">
                    <p className="text-xl font-bold text-gray-900">{patient.name}</p>
                    <p className="text-sm text-gray-500">ID: {patient.external_id}</p>
                    {patient.age && <p className="text-sm text-gray-500">Age: {patient.age}</p>}
                    {patient.gender && <p className="text-sm text-gray-500">Gender: {patient.gender}</p>}
                    {patient.weight_kg && <p className="text-sm text-gray-500">Weight: {patient.weight_kg} kg</p>}
                  </div>
                </div>

                {/* Allergies */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-red-700 text-lg">Known Allergies</h3>
                    <button onClick={() => setShowAddAllergy(true)} className="px-3 py-1 bg-red-100 text-red-700 rounded-lg text-xs font-medium hover:bg-red-200">+ Add</button>
                  </div>
                  {patient.allergies.length > 0 ? patient.allergies.map((a) => (
                    <div key={a.id} className="bg-red-50 border border-red-200 rounded-lg p-3 mb-2">
                      <p className="font-medium text-red-800">{a.allergen_name}</p>
                      <p className="text-xs text-red-600">{a.criticality} criticality | {a.category} | {a.verification_status}</p>
                      {a.reaction_manifestations && a.reaction_manifestations.length > 0 && <p className="text-xs text-red-500 mt-1">Reactions: {a.reaction_manifestations.join(', ')}</p>}
                    </div>
                  )) : <p className="text-sm text-gray-400 italic">No known allergies</p>}
                </div>

                {/* Conditions */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-purple-700 text-lg">Conditions</h3>
                    <button onClick={() => setShowAddCondition(true)} className="px-3 py-1 bg-purple-100 text-purple-700 rounded-lg text-xs font-medium hover:bg-purple-200">+ Add</button>
                  </div>
                  {patient.conditions.length > 0 ? patient.conditions.map((c) => (
                    <div key={c.id} className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-2">
                      <p className="font-medium text-purple-800">{c.condition_name}</p>
                      {c.contraindicated_ingredients && c.contraindicated_ingredients.length > 0 && <p className="text-xs text-purple-600">Avoid: {c.contraindicated_ingredients.join(', ')}</p>}
                    </div>
                  )) : <p className="text-sm text-gray-400 italic">No conditions on file</p>}
                </div>

                {/* Lab Sensitivities */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-semibold text-yellow-700 text-lg mb-4">Lab Sensitivities</h3>
                  {patient.lab_sensitivities.length > 0 ? patient.lab_sensitivities.map((ls) => (
                    <div key={ls.id} className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-2">
                      <p className="font-medium text-yellow-800">{ls.test_name}</p>
                      <p className="text-xs text-yellow-600">{ls.value} {ls.unit} ({ls.interpretation})</p>
                      {ls.related_substances && ls.related_substances.length > 0 && <p className="text-xs text-yellow-500">Related: {ls.related_substances.join(', ')}</p>}
                    </div>
                  )) : <p className="text-sm text-gray-400 italic">No lab sensitivities</p>}
                </div>

                {/* Reports */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 lg:col-span-2">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-800 text-lg">Patient Reports & Documents</h3>
                    <button onClick={() => reportInputRef.current?.click()} disabled={reportUploading} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                      {reportUploading ? 'Uploading...' : '+ Upload Report'}
                    </button>
                    <input ref={reportInputRef} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="hidden" onChange={handleReportUpload} />
                  </div>
                  <input ref={replaceInputRef} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="hidden" onChange={handleReplaceReport} />

                  {reports.length > 0 ? (
                    <div className="space-y-2">
                      {reports.map((r) => (
                        <div key={r.id} className="bg-gray-50 border border-gray-200 rounded-lg p-4 flex items-start justify-between">
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-gray-800 truncate">{r.filename}</p>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {(r.file_size / 1024).toFixed(1)} KB | v{r.version} |{' '}
                              <span className={`font-medium ${r.status === 'ready' ? 'text-green-600' : r.status === 'extracting' ? 'text-yellow-600' : r.status === 'failed' ? 'text-red-600' : 'text-gray-500'}`}>
                                {r.status === 'ready' ? 'Indexed' : r.status === 'extracting' ? 'Processing...' : r.status === 'failed' ? 'Failed' : 'Pending'}
                              </span>
                            </p>
                            {r.structured_data && (
                              <details className="mt-2">
                                <summary className="text-xs text-emerald-600 cursor-pointer hover:text-emerald-800 font-medium">View structured data</summary>
                                <div className="mt-2 space-y-2 text-xs">
                                  {r.structured_data.summary && (
                                    <div className="bg-blue-50 border border-blue-200 rounded p-2">
                                      <span className="font-semibold text-blue-700">Summary:</span>
                                      <p className="text-blue-800 mt-0.5">{r.structured_data.summary}</p>
                                    </div>
                                  )}
                                  {r.structured_data.document_type && (
                                    <span className="inline-block bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full font-medium">{r.structured_data.document_type.replace(/_/g, ' ')}</span>
                                  )}
                                  {r.structured_data.medications && r.structured_data.medications.length > 0 && (
                                    <div className="bg-orange-50 border border-orange-200 rounded p-2">
                                      <p className="font-semibold text-orange-700 mb-1">Medications ({r.structured_data.medications.length})</p>
                                      {r.structured_data.medications.map((m, mi) => (
                                        <div key={mi} className="flex flex-wrap gap-1 mb-1">
                                          <span className="font-medium text-orange-900">{m.name}</span>
                                          {m.dosage && <span className="text-orange-600">• {m.dosage}</span>}
                                          {m.frequency && <span className="text-orange-600">• {m.frequency}</span>}
                                          {m.route && <span className="text-orange-500">• {m.route}</span>}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                  {r.structured_data.lab_results && r.structured_data.lab_results.length > 0 && (
                                    <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                                      <p className="font-semibold text-yellow-700 mb-1">Lab Results ({r.structured_data.lab_results.length})</p>
                                      <table className="w-full text-left">
                                        <thead><tr className="text-yellow-700"><th className="pr-2">Test</th><th className="pr-2">Value</th><th className="pr-2">Ref Range</th><th>Status</th></tr></thead>
                                        <tbody>
                                          {r.structured_data.lab_results.map((lr, li) => (
                                            <tr key={li} className={lr.interpretation === 'critical' ? 'text-red-700 font-bold' : lr.interpretation === 'high' || lr.interpretation === 'low' ? 'text-yellow-800 font-medium' : 'text-gray-700'}>
                                              <td className="pr-2">{lr.test_name}</td>
                                              <td className="pr-2">{lr.value} {lr.unit || ''}</td>
                                              <td className="pr-2">{lr.reference_range || '-'}</td>
                                              <td><span className={`px-1.5 py-0.5 rounded ${lr.interpretation === 'normal' ? 'bg-green-100 text-green-700' : lr.interpretation === 'critical' ? 'bg-red-200 text-red-800' : lr.interpretation === 'high' ? 'bg-yellow-200 text-yellow-800' : lr.interpretation === 'low' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>{lr.interpretation || '?'}</span></td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  )}
                                  {r.structured_data.diagnoses && r.structured_data.diagnoses.length > 0 && (
                                    <div className="bg-purple-50 border border-purple-200 rounded p-2">
                                      <p className="font-semibold text-purple-700 mb-1">Diagnoses</p>
                                      {r.structured_data.diagnoses.map((d, di) => (
                                        <div key={di} className="flex items-center gap-2 mb-0.5">
                                          <span className="text-purple-800 font-medium">{d.condition}</span>
                                          {d.icd_code && <span className="text-purple-500 bg-purple-100 px-1 rounded">{d.icd_code}</span>}
                                          {d.status && <span className="text-purple-400">[{d.status}]</span>}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                  {r.structured_data.allergies_mentioned && r.structured_data.allergies_mentioned.length > 0 && (
                                    <div className="bg-red-50 border border-red-200 rounded p-2">
                                      <p className="font-semibold text-red-700 mb-1">Allergies Mentioned</p>
                                      <div className="flex flex-wrap gap-1">{r.structured_data.allergies_mentioned.map((a, ai) => (<span key={ai} className="bg-red-100 text-red-700 px-2 py-0.5 rounded-full">{a}</span>))}</div>
                                    </div>
                                  )}
                                  {r.structured_data.vitals && r.structured_data.vitals.length > 0 && (
                                    <div className="bg-teal-50 border border-teal-200 rounded p-2">
                                      <p className="font-semibold text-teal-700 mb-1">Vitals</p>
                                      <div className="flex flex-wrap gap-2">{r.structured_data.vitals.map((v, vi) => (<span key={vi} className="bg-teal-100 text-teal-800 px-2 py-0.5 rounded">{v.name}: {v.value} {v.unit || ''}</span>))}</div>
                                    </div>
                                  )}
                                  {r.structured_data.clinical_notes && (
                                    <div className="bg-gray-50 border border-gray-200 rounded p-2">
                                      <p className="font-semibold text-gray-600 mb-0.5">Clinical Notes</p>
                                      <p className="text-gray-700">{r.structured_data.clinical_notes}</p>
                                    </div>
                                  )}
                                </div>
                              </details>
                            )}
                            {r.extracted_text && (
                              <details className="mt-1">
                                <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">View raw text</summary>
                                <pre className="mt-1 text-xs text-gray-600 bg-gray-100 p-2 rounded max-h-40 overflow-y-auto whitespace-pre-wrap">{r.extracted_text}</pre>
                              </details>
                            )}
                          </div>
                          <button onClick={() => { setReplacingReportId(r.id); replaceInputRef.current?.click(); }} disabled={reportUploading} className="ml-3 text-blue-500 hover:text-blue-700 disabled:opacity-50" title="Replace">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : <p className="text-sm text-gray-400 italic">No reports uploaded yet. Upload lab reports, prescriptions, or medical documents.</p>}
                </div>
              </div>
            )}

            {/* TAB 2: Allergy Analysis */}
            {activeTab === 'analysis' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                  {/* Drug Entry */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <h3 className="font-semibold text-gray-800 text-lg mb-4">Check Prescription for Allergies</h3>
                    <div className="flex gap-2 mb-4">
                      <button onClick={() => setPhotoMode(false)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${!photoMode ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>Manual Entry</button>
                      <button onClick={() => setPhotoMode(true)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${photoMode ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>Photo Upload</button>
                    </div>

                    {!photoMode ? (
                      <>
                        <div className="relative mb-4">
                          <div className="flex gap-2">
                            <div className="relative flex-1">
                              <input type="text" value={drugQuery} onChange={(e) => handleDrugSearch(e.target.value)} onFocus={() => drugResults.length > 0 && setShowDropdown(true)} onBlur={() => setTimeout(() => setShowDropdown(false), 200)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); showDropdown && drugResults.length > 0 ? addDrug(drugResults[0]) : addDrugByName(drugQuery); } }} placeholder="Type any drug/medicine name..." className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-900" />
                              {showDropdown && drugResults.length > 0 && (
                                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                                  {drugResults.map((drug) => (
                                    <button key={drug.id} onMouseDown={() => addDrug(drug)} className="w-full text-left px-4 py-3 hover:bg-blue-50 border-b border-gray-100 last:border-0">
                                      <div className="font-medium text-gray-900">{drug.name}</div>
                                      <div className="text-xs text-gray-500">{drug.generic_name} {drug.dosage_form && `| ${drug.dosage_form}`}</div>
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                            <button onClick={() => addDrugByName(drugQuery)} disabled={!drugQuery.trim()} className="px-5 py-2.5 bg-gray-700 text-white rounded-lg hover:bg-gray-800 disabled:opacity-40 font-medium transition-colors whitespace-nowrap">+ Add</button>
                          </div>
                          <p className="text-xs text-gray-400 mt-1">Type any medicine name and click Add or press Enter. You can also pick from suggestions if available.</p>
                        </div>
                        {selectedDrugs.length > 0 && (
                          <div className="space-y-2 mb-4">
                            {selectedDrugs.map((drug, i) => (
                              <div key={i} className="flex items-center justify-between bg-gray-50 px-4 py-2.5 rounded-lg">
                                <span className="text-gray-800 font-medium">{drug.name}</span>
                                <button onClick={() => removeDrug(i)} className="text-red-500 hover:text-red-700 text-sm font-medium">Remove</button>
                              </div>
                            ))}
                          </div>
                        )}
                        <button onClick={handleManualCheck} disabled={checking || selectedDrugs.length === 0} className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-semibold text-lg transition-colors">
                          {checking ? <span className="flex items-center justify-center gap-2"><svg className="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Analyzing with Gemini AI...</span> : 'Check for Allergies'}
                        </button>
                      </>
                    ) : (
                      <div>
                        <div onClick={() => fileInputRef.current?.click()} className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
                          <svg className="w-12 h-12 mx-auto text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                          <p className="text-gray-600 font-medium">Click to upload prescription photo</p>
                          <p className="text-sm text-gray-400 mt-1">JPEG, PNG, or WebP (max 10MB)</p>
                          {checking && <div className="mt-4 flex items-center justify-center gap-2 text-blue-600"><svg className="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Processing with Gemini AI...</div>}
                        </div>
                        <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handlePhotoUpload} />
                      </div>
                    )}
                    {checkError && <p className="mt-3 text-sm text-red-600 bg-red-50 p-3 rounded-lg">{checkError}</p>}
                  </div>

                  {/* Results */}
                  {checkResult && (
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                      <h3 className="font-semibold text-gray-800 text-lg mb-4">Allergy Check Results</h3>
                      <div className={`flex items-center gap-4 p-4 rounded-xl border-2 mb-6 ${signalBorder(checkResult.overall_signal)}`}>
                        <div className={`w-16 h-16 rounded-full ${signalColor(checkResult.overall_signal)} flex items-center justify-center flex-shrink-0`}>
                          {checkResult.overall_signal === 'GREEN' && <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                          {checkResult.overall_signal === 'YELLOW' && <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 9v2m0 4h.01" /></svg>}
                          {checkResult.overall_signal === 'RED' && <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" /></svg>}
                        </div>
                        <div>
                          <p className="text-xl font-bold text-gray-900">
                            {checkResult.overall_signal === 'GREEN' ? 'Safe to Prescribe' : checkResult.overall_signal === 'YELLOW' ? 'Review Recommended' : 'DO NOT PRESCRIBE'}
                          </p>
                          <p className="text-sm text-gray-600">Processed in {checkResult.processing_time_ms}ms{checkResult.ocr_confidence != null && ` | OCR: ${(checkResult.ocr_confidence * 100).toFixed(0)}%`}</p>
                        </div>
                      </div>
                      {checkResult.extracted_drugs && checkResult.extracted_drugs.length > 0 && (
                        <div className="mb-4 p-3 bg-blue-50 rounded-lg"><p className="text-sm font-medium text-blue-800">Extracted from photo:</p><p className="text-sm text-blue-700">{checkResult.extracted_drugs.join(', ')}</p></div>
                      )}
                      {checkResult.citations && checkResult.citations.length > 0 && (
                        <div className="mb-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
                          <p className="text-sm font-semibold text-indigo-800 mb-1">References</p>
                          {checkResult.citations.map((c, ci) => (<a key={ci} href={c.url} target="_blank" rel="noopener noreferrer" className="block text-sm text-indigo-600 hover:underline">{c.source}</a>))}
                        </div>
                      )}
                      <div className="space-y-4">
                        {checkResult.drug_results.map((dr, i) => (
                          <div key={i} className={`border-2 rounded-xl p-4 ${signalBorder(dr.signal)}`}>
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-3"><div className={`w-4 h-4 rounded-full ${signalColor(dr.signal)}`} /><span className="font-semibold text-gray-900">{dr.drug.name || 'Unknown Drug'}</span></div>
                              <span className={`px-3 py-1 rounded-full text-xs font-bold text-white ${signalColor(dr.signal)}`}>{dr.signal}</span>
                            </div>
                            {dr.reasoning && (<div className="mb-3 p-3 bg-white/80 border border-gray-200 rounded-lg"><p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">AI Reasoning</p><p className="text-sm text-gray-700 leading-relaxed">{dr.reasoning}</p></div>)}
                            {dr.warnings.length > 0 && (<div className="mt-3 space-y-2">{dr.warnings.map((w, wi) => (
                              <div key={wi} className="bg-white/70 rounded-lg p-3 border border-gray-200">
                                <div className="flex items-start gap-2">
                                  <span className={`px-2 py-0.5 rounded text-xs font-bold text-white flex-shrink-0 mt-0.5 ${w.severity === 'CRITICAL' ? 'bg-red-600' : w.severity === 'HIGH' ? 'bg-orange-500' : w.severity === 'MODERATE' ? 'bg-yellow-500' : 'bg-gray-400'}`}>{w.severity}</span>
                                  <div className="flex-1">
                                    <p className="text-sm text-gray-800 font-medium">{w.message}</p>
                                    {w.reasoning && <p className="text-sm text-gray-600 mt-1 bg-gray-50 p-2 rounded">{w.reasoning}</p>}
                                  </div>
                                </div>
                              </div>
                            ))}</div>)}
                            {dr.alternatives.length > 0 && (<div className="mt-3"><p className="text-sm font-medium text-gray-700 mb-2">Safe Alternatives:</p>{dr.alternatives.map((alt, ai) => (<div key={ai} className="flex items-center gap-2 bg-green-50 px-3 py-2 rounded-lg mb-1"><div className="w-3 h-3 rounded-full bg-green-500" /><span className="text-sm font-medium text-green-800">{alt.name}</span><span className="text-xs text-green-600 ml-1">{alt.reason}</span></div>))}</div>)}
                            {dr.signal === 'RED' && (<button onClick={() => setOverrideModal(dr)} className="mt-3 px-4 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium hover:bg-red-200">Override &amp; Prescribe Anyway</button>)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Side panel: quick patient info */}
                <div className="space-y-4">
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 sticky top-20">
                    <h4 className="font-semibold text-gray-800 mb-3">Quick Patient View</h4>
                    <p className="text-sm font-bold text-gray-900">{patient.name}</p>
                    <p className="text-xs text-gray-500 mb-3">{patient.external_id} {patient.age && `| ${patient.age}y`} {patient.gender && `| ${patient.gender}`}</p>
                    {patient.allergies.length > 0 && (<><p className="text-xs font-semibold text-red-700 mb-1">Allergies:</p>{patient.allergies.map((a) => (<p key={a.id} className="text-xs text-red-600 mb-0.5">- {a.allergen_name} ({a.criticality})</p>))}</>)}
                    {patient.conditions.length > 0 && (<><p className="text-xs font-semibold text-purple-700 mt-2 mb-1">Conditions:</p>{patient.conditions.map((c) => (<p key={c.id} className="text-xs text-purple-600 mb-0.5">- {c.condition_name}</p>))}</>)}
                    {reports.length > 0 && <p className="text-xs text-gray-400 mt-2">{reports.length} report(s) on file</p>}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: AI Chat */}
            {activeTab === 'chat' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden" style={{ height: 'calc(100vh - 250px)' }}>
                <div className="flex flex-col h-full">
                  {/* Chat header */}
                  <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-white">
                    <h3 className="font-bold text-lg">AI Medical Assistant</h3>
                    <p className="text-sm text-blue-100">Ask questions about {patient.name}&apos;s data, allergies, medications, and reports. Powered by Gemini AI.</p>
                  </div>

                  {/* Optional medicine context */}
                  <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
                    <label className="text-xs font-medium text-gray-500">Medicine context (optional):</label>
                    <input type="text" value={chatMedicine} onChange={(e) => setChatMedicine(e.target.value)} placeholder="e.g., Amoxicillin, Ibuprofen..." className="mt-1 w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>

                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                    {chatMessages.length === 0 && (
                      <div className="text-center py-12">
                        <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
                        <p className="text-gray-400 font-medium">Start a conversation</p>
                        <p className="text-sm text-gray-300 mt-1">Ask about allergies, drug safety, report findings, or any medical concern for this patient.</p>
                        <div className="mt-6 flex flex-wrap gap-2 justify-center">
                          {['Does this patient have any drug allergies?', 'Is Amoxicillin safe for this patient?', 'Summarize the patient reports', 'What medications should be avoided?'].map((q) => (
                            <button key={q} onClick={() => { setChatInput(q); }} className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-xs font-medium hover:bg-blue-100 transition-colors">{q}</button>
                          ))}
                        </div>
                      </div>
                    )}
                    {chatMessages.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                          <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="flex justify-start">
                        <div className="bg-gray-100 rounded-2xl px-4 py-3">
                          <div className="flex items-center gap-2 text-sm text-gray-500">
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                            Analyzing with Gemini AI...
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Input */}
                  <div className="px-6 py-4 border-t border-gray-200 bg-white">
                    <div className="flex gap-3">
                      <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleChat()} placeholder="Ask about this patient..." className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-gray-900" />
                      <button onClick={handleChat} disabled={chatLoading || !chatInput.trim()} className="px-6 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 font-medium transition-colors">
                        Send
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {!patient && (
          <div className="text-center py-20">
            <svg className="w-20 h-20 mx-auto text-gray-300 mb-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
            <h2 className="text-2xl font-bold text-gray-700 mb-2">No Patient Selected</h2>
            <p className="text-gray-400 mb-4">Enter a patient ID above to load their profile, or create a new patient.</p>
          </div>
        )}
      </div>

      {/* Add Allergy Modal */}
      {showAddAllergy && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Add Known Allergy</h3>
            <div className="space-y-3">
              <input type="text" placeholder="Allergen name (e.g., Penicillin)" value={newAllergy.allergen_name} onChange={(e) => setNewAllergy({ ...newAllergy, allergen_name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
              <div className="grid grid-cols-2 gap-3">
                <select value={newAllergy.category} onChange={(e) => setNewAllergy({ ...newAllergy, category: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900">
                  <option value="drug">Drug</option><option value="food">Food</option><option value="environment">Environment</option><option value="biologic">Biologic</option>
                </select>
                <select value={newAllergy.criticality} onChange={(e) => setNewAllergy({ ...newAllergy, criticality: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-lg text-gray-900">
                  <option value="high">High</option><option value="low">Low</option><option value="unable-to-assess">Unable to assess</option>
                </select>
              </div>
              <input type="text" placeholder="Reaction severity (mild/moderate/severe)" value={newAllergy.reaction_severity} onChange={(e) => setNewAllergy({ ...newAllergy, reaction_severity: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
              <input type="text" placeholder="Reactions (comma-separated: rash, hives, anaphylaxis)" value={newAllergy.reaction_manifestations} onChange={(e) => setNewAllergy({ ...newAllergy, reaction_manifestations: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => setShowAddAllergy(false)} className="flex-1 py-2.5 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200">Cancel</button>
              <button onClick={handleAddAllergy} disabled={!newAllergy.allergen_name.trim()} className="flex-1 py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50">Add Allergy</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Condition Modal */}
      {showAddCondition && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Add Medical Condition</h3>
            <div className="space-y-3">
              <input type="text" placeholder="Condition name (e.g., Asthma, Diabetes)" value={newCondition.condition_name} onChange={(e) => setNewCondition({ ...newCondition, condition_name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
              <input type="text" placeholder="Contraindicated ingredients (comma-separated)" value={newCondition.contraindicated_ingredients} onChange={(e) => setNewCondition({ ...newCondition, contraindicated_ingredients: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => setShowAddCondition(false)} className="flex-1 py-2.5 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200">Cancel</button>
              <button onClick={handleAddCondition} disabled={!newCondition.condition_name.trim()} className="flex-1 py-2.5 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50">Add Condition</button>
            </div>
          </div>
        </div>
      )}

      {/* Override Modal */}
      {overrideModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6">
            <h3 className="text-lg font-bold text-red-700 mb-2">Override Warning</h3>
            <p className="text-sm text-gray-600 mb-4">Override RED signal for <strong>{overrideModal.drug.name}</strong>. This is permanently logged.</p>
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              {overrideModal.warnings.map((w, i) => (<p key={i} className="text-sm text-red-700">{w.message}</p>))}
            </div>
            <textarea value={overrideJustification} onChange={(e) => setOverrideJustification(e.target.value)} placeholder="Clinical justification (required)..." rows={4} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 outline-none mb-4 focus:ring-2 focus:ring-red-500" />
            <div className="flex gap-3">
              <button onClick={() => { setOverrideModal(null); setOverrideJustification(''); }} className="flex-1 py-2.5 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200">Cancel</button>
              <button onClick={handleOverride} disabled={!overrideJustification.trim() || overrideLoading} className="flex-1 py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50">{overrideLoading ? 'Recording...' : 'Confirm Override'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
