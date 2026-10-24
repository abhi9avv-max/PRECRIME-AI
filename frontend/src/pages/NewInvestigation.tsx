import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Scenario, InvestigationSummary, MetricsData } from '../types';
import { Header } from '../components/Header';
import { MetricsPanel } from '../components/MetricsPanel';
import { WazuhModal } from '../components/WazuhModal';
import { StatusBadge } from '../components/StatusBadge';
import { PlusCircle, Search, ShieldAlert, ArrowRight, Database, AlertCircle } from 'lucide-react';

export const NewInvestigation: React.FC = () => {
  const navigate = useNavigate();

  const [title, setTitle] = useState('Detection failure on credential access');
  const [sourceMode, setSourceMode] = useState<'DEMO' | 'WAZUH'>('DEMO');
  const [wazuhTested, setWazuhTested] = useState(false);
  const [isWazuhModalOpen, setIsWazuhModalOpen] = useState(false);

  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedFamily, setSelectedFamily] = useState('parsing_failure');
  const [selectedVariant, setSelectedVariant] = useState('a');

  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load scenarios, history, and metrics
  const loadData = async () => {
    try {
      const [scList, invList, metData] = await Promise.all([
        api.listScenarios(),
        api.listInvestigations(),
        api.getMetrics(),
      ]);
      setScenarios(scList);
      setInvestigations(invList);
      setMetrics(metData);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to backend service. Ensure backend is running on port 8000.');
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Unique scenario families
  const families = Array.from(new Set(scenarios.map((s) => s.family)));
  const currentFamilyScenarios = scenarios.filter((s) => s.family === selectedFamily);
  const selectedScenario = scenarios.find(
    (s) => s.family === selectedFamily && s.variant === selectedVariant
  );

  const handleStartInvestigation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedScenario) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // 1. Create Investigation
      const inv = await api.createInvestigation(title, sourceMode);
      // 2. Start Initial Run
      await api.startRun(inv.id, selectedScenario.id);
      // 3. Navigate to Pipeline Trace
      navigate(`/investigations/${inv.id}/trace`);
    } catch (err: any) {
      setError(err.message || 'Failed to initialize investigation run.');
      setIsSubmitting(false);
    }
  };

  const handleOpenInvestigation = (inv: InvestigationSummary) => {
    if (inv.status === 'CREATED' || inv.status === 'RUN_FAILED' || inv.status === 'RUN_COMPLETED') {
      navigate(`/investigations/${inv.id}/trace`);
    } else if (inv.status === 'REVIEWED' || inv.status === 'REMEDIATION_APPROVED') {
      navigate(`/investigations/${inv.id}/diagnosis`);
    } else {
      navigate(`/investigations/${inv.id}/retest`);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header sourceMode={sourceMode} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-8">
        {/* Backend connectivity warning */}
        {error && (
          <div className="p-4 rounded-lg bg-red-950/80 border border-red-700 text-red-200 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle size={18} className="shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadData}
              className="px-3 py-1 rounded bg-red-900 hover:bg-red-800 text-xs font-medium transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Section 1: Prominent Start Investigation Form (Screen 1) */}
        <section aria-labelledby="start-investigation-heading" className="rounded-xl border border-border bg-panel p-6 shadow-xl">
          <div className="border-b border-border pb-4 mb-6">
            <h1 id="start-investigation-heading" className="text-xl font-bold text-textPrimary tracking-tight">
              Start SIEM Detection-Failure Investigation
            </h1>
            <p className="text-xs text-textMuted mt-1">
              Select an observable failure scenario and run deterministic pipeline verification to prove the root cause.
            </p>
          </div>

          <form onSubmit={handleStartInvestigation} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Investigation Title */}
              <div className="space-y-2">
                <label htmlFor="inv-title" className="block text-xs font-semibold uppercase tracking-wider text-textMuted">
                  Investigation Title
                </label>
                <input
                  id="inv-title"
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Failure in Windows Logon Event Rule"
                  className="w-full px-3.5 py-2.5 rounded bg-slate-900 border border-border text-sm text-textPrimary focus:outline-none focus:border-primaryBlue focus:ring-1 focus:ring-primaryBlue"
                />
              </div>

              {/* Data Source Mode */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-textMuted">
                    Telemetry Source
                  </label>
                  {!wazuhTested && (
                    <button
                      type="button"
                      onClick={() => setIsWazuhModalOpen(true)}
                      className="text-xs text-primaryBlue hover:underline flex items-center gap-1"
                    >
                      <ShieldAlert size={12} />
                      <span>Test Wazuh Connection</span>
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setSourceMode('DEMO')}
                    className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded border text-xs font-medium transition-colors ${
                      sourceMode === 'DEMO'
                        ? 'bg-blue-950/70 border-primaryBlue text-white font-semibold shadow-sm'
                        : 'bg-slate-900 border-border text-textMuted hover:text-textPrimary'
                    }`}
                  >
                    <Database size={14} />
                    <span>Synthetic Demo</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      if (!wazuhTested) {
                        setIsWazuhModalOpen(true);
                      } else {
                        setSourceMode('WAZUH');
                      }
                    }}
                    className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded border text-xs font-medium transition-colors ${
                      sourceMode === 'WAZUH'
                        ? 'bg-cyan-950/70 border-cyan-500 text-cyan-200 font-semibold'
                        : 'bg-slate-900 border-border text-textMuted hover:text-textPrimary'
                    }`}
                  >
                    <ShieldAlert size={14} />
                    <span>Wazuh Live {wazuhTested ? '(Ready)' : '(Unverified)'}</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Scenario Family & Variant Selectors */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              <div className="space-y-2">
                <label htmlFor="scenario-family" className="block text-xs font-semibold uppercase tracking-wider text-textMuted">
                  Scenario Family
                </label>
                <select
                  id="scenario-family"
                  value={selectedFamily}
                  onChange={(e) => {
                    setSelectedFamily(e.target.value);
                    setSelectedVariant('a');
                  }}
                  className="w-full px-3.5 py-2.5 rounded bg-slate-900 border border-border text-sm text-textPrimary focus:outline-none focus:border-primaryBlue"
                >
                  {families.map((fam) => (
                    <option key={fam} value={fam}>
                      {fam.replace('_', ' ').toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="block text-xs font-semibold uppercase tracking-wider text-textMuted">
                  Scenario Variant
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {currentFamilyScenarios.map((sc) => (
                    <button
                      type="button"
                      key={sc.id}
                      onClick={() => setSelectedVariant(sc.variant)}
                      className={`flex flex-col items-start p-2.5 rounded border text-left transition-colors ${
                        selectedVariant === sc.variant
                          ? 'bg-blue-950/60 border-primaryBlue text-textPrimary shadow-sm'
                          : 'bg-slate-900 border-border text-textMuted hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="font-mono text-xs font-bold uppercase">
                          Variant {sc.variant.toUpperCase()}
                        </span>
                        <span
                          className={`text-[10px] font-mono px-1.5 py-0.2 rounded ${
                            sc.split === 'development'
                              ? 'bg-slate-800 text-slate-300'
                              : 'bg-purple-950 text-purple-300 border border-purple-800'
                          }`}
                        >
                          {sc.split === 'development' ? 'Dev' : 'Held-Out'}
                        </span>
                      </div>
                      <span className="text-[11px] text-textMuted mt-1 line-clamp-1">
                        {sc.name}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Scenario Description Card */}
            {selectedScenario && (
              <div className="rounded bg-slate-900/60 border border-border p-3.5 text-xs text-textMuted flex items-start gap-2">
                <span className="font-semibold text-textPrimary shrink-0">Scenario Brief:</span>
                <span>{selectedScenario.description}</span>
              </div>
            )}

            {/* Prominent Action Button: Obvious within 3 seconds */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting || !selectedScenario}
                aria-label="Start Investigation"
                className="w-full sm:w-auto px-8 py-3.5 rounded-lg bg-primaryBlue hover:bg-primaryBlueHover text-white text-base font-semibold transition-all shadow-lg hover:shadow-primaryBlue/25 disabled:opacity-50 flex items-center justify-center gap-2 group"
              >
                <span>Start Investigation</span>
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </form>
        </section>

        {/* Section 2: Investigation History Table */}
        <section aria-labelledby="history-heading" className="rounded-xl border border-border bg-panel p-6">
          <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
            <div>
              <h2 id="history-heading" className="text-base font-semibold text-textPrimary">
                Prior Investigations
              </h2>
              <p className="text-xs text-textMuted mt-0.5">
                Saved detection failure investigations and verification status
              </p>
            </div>
            <button
              onClick={loadData}
              className="text-xs text-textMuted hover:text-textPrimary transition-colors flex items-center gap-1"
            >
              <span>Refresh</span>
            </button>
          </div>

          {loadingHistory ? (
            <div className="py-8 text-center text-sm text-textMuted">Loading investigations...</div>
          ) : investigations.length === 0 ? (
            <div className="py-10 px-4 text-center border border-dashed border-border rounded-lg space-y-3">
              <div className="text-sm font-medium text-textPrimary">No investigations recorded yet</div>
              <p className="text-xs text-textMuted max-w-md mx-auto leading-relaxed">
                PRECRIME AI investigates why expected security alerts fail to trigger. Select a scenario above to start your first verification loop.
              </p>
              <button
                type="button"
                onClick={() => {
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                className="inline-flex items-center gap-2 px-4 py-2 rounded bg-primaryBlue hover:bg-primaryBlueHover text-white text-xs font-semibold transition-colors mt-2"
              >
                <PlusCircle size={14} />
                <span>Start Investigation</span>
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border text-textMuted uppercase font-mono tracking-wider">
                    <th className="py-2.5 px-3">Title</th>
                    <th className="py-2.5 px-3">Source</th>
                    <th className="py-2.5 px-3">Investigation Status</th>
                    <th className="py-2.5 px-3">Outcome</th>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {investigations.map((inv) => (
                    <tr
                      key={inv.id}
                      onClick={() => handleOpenInvestigation(inv)}
                      className="hover:bg-slate-900/60 transition-colors cursor-pointer group"
                    >
                      <td className="py-3 px-3 font-medium text-textPrimary">
                        {inv.title}
                      </td>
                      <td className="py-3 px-3 font-mono text-textMuted">
                        {inv.source_mode}
                      </td>
                      <td className="py-3 px-3">
                        <StatusBadge status={inv.status} size="sm" />
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-300">
                        {inv.latest_outcome ? (
                          <span className={inv.latest_outcome === 'FAILURE_LOCALIZED' ? 'text-amber-400' : 'text-emerald-400'}>
                            {inv.latest_outcome} {inv.failure_stage ? `(${inv.failure_stage})` : ''}
                          </span>
                        ) : (
                          <span className="text-textMuted">Pending</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-textMuted">
                        {new Date(inv.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <span className="text-primaryBlue group-hover:translate-x-1 inline-flex items-center gap-1 transition-transform">
                          Open <ArrowRight size={12} />
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Section 3: Reusable Metrics Panel */}
        <section aria-labelledby="metrics-panel-heading">
          <MetricsPanel metrics={metrics} onRefresh={loadData} />
        </section>
      </main>

      {/* Wazuh Connection Modal */}
      <WazuhModal
        isOpen={isWazuhModalOpen}
        onClose={() => setIsWazuhModalOpen(false)}
        onSuccess={() => {
          setWazuhTested(true);
          setSourceMode('WAZUH');
        }}
        onSwitchToDemo={() => {
          setSourceMode('DEMO');
        }}
      />
    </div>
  );
};
