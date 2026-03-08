'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import {
  getPatientProfile,
  getReports,
  type PatientAllergyProfile,
  type PatientReport,
} from '@/lib/api';

export default function PatientPortal() {
  const [patientId, setPatientId] = useState('');
  const [patient, setPatient] = useState<PatientAllergyProfile | null>(null);
  const [reports, setReports] = useState<PatientReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadProfile = useCallback(async () => {
    if (!patientId.trim()) return;
    setLoading(true);
    setError('');
    setPatient(null);
    setReports([]);
    try {
      const profile = await getPatientProfile(patientId.trim());
      setPatient(profile);
      try {
        const rData = await getReports(patientId.trim());
        setReports(rData.reports);
      } catch { /* no reports */ }
    } catch (e: any) {
      setError(e.message || 'Patient not found. Please check your Patient ID.');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-teal-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-9 h-9 bg-gradient-to-br from-emerald-600 to-teal-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">AllerSense</h1>
              <p className="text-xs text-gray-400">Patient Portal</p>
            </div>
          </Link>
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-700">Home</Link>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Login */}
        {!patient && (
          <div className="max-w-md mx-auto">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-100 rounded-full mb-4">
                <svg className="w-8 h-8 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Welcome to Your Health Portal</h2>
              <p className="text-gray-500 mt-1">Enter your Patient ID to view your medical records</p>
            </div>

            <div className="bg-white rounded-2xl shadow-md border border-gray-200 p-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Patient ID</label>
              <input
                type="text"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadProfile()}
                placeholder="e.g., P-5678"
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none text-gray-900 text-lg"
              />
              {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
              <button
                onClick={loadProfile}
                disabled={loading || !patientId.trim()}
                className="w-full mt-4 py-3 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 disabled:opacity-50 font-semibold text-lg transition-colors"
              >
                {loading ? 'Loading...' : 'View My Records'}
              </button>
            </div>

            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-4">
              <p className="text-sm text-blue-800 font-medium mb-1">Read-Only Access</p>
              <p className="text-xs text-blue-600">This portal is for viewing only. Contact your doctor to update your medical records, upload documents, or make changes to your profile.</p>
            </div>
          </div>
        )}

        {/* Patient Dashboard */}
        {patient && (
          <div>
            {/* Welcome banner */}
            <div className="bg-gradient-to-r from-emerald-600 to-teal-600 rounded-2xl p-6 mb-6 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-emerald-100 text-sm">Welcome back,</p>
                  <h2 className="text-2xl font-bold">{patient.name}</h2>
                  <p className="text-emerald-200 text-sm mt-1">
                    ID: {patient.external_id}
                    {patient.age && ` | Age: ${patient.age}`}
                    {patient.gender && ` | ${patient.gender}`}
                  </p>
                </div>
                <button onClick={() => { setPatient(null); setReports([]); setPatientId(''); }} className="px-4 py-2 bg-white/20 rounded-lg text-sm font-medium hover:bg-white/30 transition-colors">
                  Log Out
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Allergy Alert Card */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                    <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                  <h3 className="font-semibold text-gray-800">My Allergies</h3>
                  <span className="ml-auto bg-red-100 text-red-700 text-xs font-bold px-2 py-0.5 rounded-full">{patient.allergies.length}</span>
                </div>
                {patient.allergies.length > 0 ? (
                  <div className="space-y-2">
                    {patient.allergies.map((a) => (
                      <div key={a.id} className="bg-red-50 border border-red-200 rounded-lg p-3">
                        <p className="font-medium text-red-800">{a.allergen_name}</p>
                        <p className="text-xs text-red-600 mt-0.5">
                          {a.category} | {a.criticality} criticality | {a.verification_status}
                        </p>
                        {a.reaction_manifestations && a.reaction_manifestations.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {a.reaction_manifestations.map((r, i) => (
                              <span key={i} className="bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded-full">{r}</span>
                            ))}
                          </div>
                        )}
                        {a.reaction_severity && (
                          <p className="text-xs text-red-500 mt-1">Severity: {a.reaction_severity}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 italic">No known allergies on file.</p>
                )}
              </div>

              {/* Conditions Card */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                    <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                  <h3 className="font-semibold text-gray-800">My Conditions</h3>
                  <span className="ml-auto bg-purple-100 text-purple-700 text-xs font-bold px-2 py-0.5 rounded-full">{patient.conditions.length}</span>
                </div>
                {patient.conditions.length > 0 ? (
                  <div className="space-y-2">
                    {patient.conditions.map((c) => (
                      <div key={c.id} className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                        <p className="font-medium text-purple-800">{c.condition_name}</p>
                        {c.contraindicated_ingredients && c.contraindicated_ingredients.length > 0 && (
                          <div className="mt-1.5">
                            <p className="text-xs text-purple-600 font-medium">Ingredients to avoid:</p>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {c.contraindicated_ingredients.map((ing, i) => (
                                <span key={i} className="bg-purple-100 text-purple-700 text-xs px-2 py-0.5 rounded-full">{ing}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 italic">No conditions on file.</p>
                )}
              </div>

              {/* Lab Values Card */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center">
                    <svg className="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                    </svg>
                  </div>
                  <h3 className="font-semibold text-gray-800">Lab Values</h3>
                  <span className="ml-auto bg-yellow-100 text-yellow-700 text-xs font-bold px-2 py-0.5 rounded-full">{patient.lab_sensitivities.length}</span>
                </div>
                {patient.lab_sensitivities.length > 0 ? (
                  <div className="space-y-2">
                    {patient.lab_sensitivities.map((ls) => (
                      <div key={ls.id} className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-yellow-800">{ls.test_name}</p>
                          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${ls.interpretation === 'normal' ? 'bg-green-100 text-green-700' : ls.interpretation === 'elevated' ? 'bg-yellow-200 text-yellow-800' : 'bg-red-100 text-red-700'}`}>
                            {ls.interpretation}
                          </span>
                        </div>
                        <p className="text-sm text-yellow-700 mt-1">{ls.value} {ls.unit}</p>
                        {ls.related_substances && ls.related_substances.length > 0 && (
                          <p className="text-xs text-yellow-600 mt-1">Related: {ls.related_substances.join(', ')}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 italic">No lab values on file.</p>
                )}
              </div>

              {/* Reports Card (full width) */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:col-span-2 lg:col-span-3">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                    <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h3 className="font-semibold text-gray-800">My Documents &amp; Reports</h3>
                  <span className="ml-auto bg-blue-100 text-blue-700 text-xs font-bold px-2 py-0.5 rounded-full">{reports.length}</span>
                </div>

                {reports.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {reports.map((r) => (
                      <div key={r.id} className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-gray-800 text-sm truncate" title={r.filename}>{r.filename}</p>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {(r.file_size / 1024).toFixed(1)} KB | v{r.version}
                            </p>
                            <div className="flex items-center gap-2 mt-1.5">
                              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${r.status === 'ready' ? 'bg-green-100 text-green-700' : r.status === 'extracting' ? 'bg-yellow-100 text-yellow-700' : r.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
                                {r.status === 'ready' ? 'Processed' : r.status === 'extracting' ? 'Processing...' : r.status === 'failed' ? 'Failed' : 'Pending'}
                              </span>
                            </div>
                            <p className="text-xs text-gray-400 mt-1">
                              Uploaded: {new Date(r.uploaded_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-sm text-gray-400">No documents uploaded yet.</p>
                    <p className="text-xs text-gray-300 mt-1">Your doctor will upload reports and prescriptions here.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Info footer */}
            <div className="mt-6 bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3">
              <svg className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-sm text-emerald-800 font-medium">Need to update your records?</p>
                <p className="text-xs text-emerald-600 mt-0.5">Contact your healthcare provider to update allergies, conditions, or upload new documents. This portal provides read-only access to your medical data.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
