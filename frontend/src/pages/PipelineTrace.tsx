import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Investigation, PipelineStage, StageResult, EvidenceRecord } from '../types';
import { Header } from '../components/Header';
import { ProgressIndicator } from '../components/ProgressIndicator';
import { StatusBadge } from '../components/StatusBadge';
import { EvidenceModal } from '../components/EvidenceModal';
import { ArrowRight, AlertCircle, RefreshCw, FileText } from 'lucide-react';

const STAGES_LIST: { id: PipelineStage; name: string }[] = [
  { id: 'event_generation', name: 'Event Generation' },
  { id: 'collection', name: 'Collection' },
  { id: 'parsing', name: 'Parsing' },
  { id: 'rule_evaluation', name: 'Rule Evaluation' },
  { id: 'alert_generation', name: 'Alert Generation' },
  { id: 'delivery_visibility', name: 'Delivery Visibility' },
];

export const PipelineTrace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceRecord[]>([]);
  const [selectedStage, setSelectedStage] = useState<PipelineStage | null>(null);
  const [isEvidenceModalOpen, setIsEvidenceModalOpen] = useState(false);

  const [loading, setLoading] = useState(true);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadInvestigation = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const inv = await api.getInvestigation(id);
      setInvestigation(inv);

      // Load evidence for the active run if available
      const latestRun = inv.runs[inv.runs.length - 1];
      if (latestRun) {
        setLoadingEvidence(true);
        const ev = await api.getRunEvidence(latestRun.id);
        setEvidenceList(ev);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load investigation details.');
    } finally {
      setLoading(false);
      setLoadingEvidence(false);
    }
  };

  useEffect(() => {
    loadInvestigation();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <div className="flex-1 flex items-center justify-center p-8 text-sm text-textMuted gap-2">
          <RefreshCw size={18} className="animate-spin text-primaryBlue" />
          <span>Tracing pipeline telemetry...</span>
        </div>
      </div>
    );
  }

  if (error || !investigation) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-1 max-w-3xl w-full mx-auto p-6 flex flex-col items-center justify-center">
          <div className="rounded-lg border border-red-800 bg-red-950/60 p-6 text-center space-y-3">
            <AlertCircle size={32} className="text-red-400 mx-auto" />
            <h2 className="text-base font-semibold text-textPrimary">Failed to load Pipeline Trace</h2>
            <p className="text-xs text-textMuted">{error || 'Investigation could not be located.'}</p>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 rounded bg-primaryBlue text-xs font-semibold text-white mt-2"
            >
              Return to Investigations
            </button>
          </div>
        </main>
      </div>
    );
  }

  const latestRun = investigation.runs[investigation.runs.length - 1];
  const stageResultsMap: Record<string, StageResult> = {};
  if (latestRun) {
    for (const sr of latestRun.stage_results) {
      stageResultsMap[sr.stage] = sr;
    }
  }

  const handleStageClick = (stId: PipelineStage) => {
    setSelectedStage(stId);
    setIsEvidenceModalOpen(true);
  };

  const selectedStageEvidence = selectedStage
    ? evidenceList.filter((e) => e.stage === selectedStage)
    : [];

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header sourceMode={investigation.source_mode} />
      <ProgressIndicator currentStep={2} investigationId={investigation.id} status={investigation.status} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-8">
        {/* Title and Run Meta Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-textPrimary">{investigation.title}</h1>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                Run ID: {latestRun?.id.slice(0, 8)}
              </span>
            </div>
            <p className="text-xs text-textMuted mt-1">
              Deterministic 6-stage SIEM detection pipeline evaluation. Click any stage to inspect raw evidence.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(`/investigations/${investigation.id}/diagnosis`)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primaryBlue hover:bg-primaryBlueHover text-white text-sm font-semibold transition-colors shadow-sm"
            >
              <span>Continue to Diagnosis</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>

        {/* Six-Stage Pipeline Trace: Horizontal on Desktop, Vertical on Mobile */}
        <section aria-labelledby="pipeline-trace-heading" className="space-y-4">
          <h2 id="pipeline-trace-heading" className="text-xs font-semibold uppercase tracking-wider text-textMuted">
            Pipeline Stage Trace
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-6 gap-3">
            {STAGES_LIST.map((stageItem, idx) => {
              const res = stageResultsMap[stageItem.id];
              const stStatus = res?.status || 'UNKNOWN';
              const reason = res?.reason || 'No determination available.';
              const stageEvidenceCount = evidenceList.filter((e) => e.stage === stageItem.id).length;

              return (
                <div
                  key={stageItem.id}
                  onClick={() => handleStageClick(stageItem.id)}
                  tabIndex={0}
                  role="button"
                  aria-label={`View evidence for stage ${stageItem.name}: status ${stStatus}`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleStageClick(stageItem.id);
                    }
                  }}
                  className="rounded-lg border border-border bg-panel p-4 flex flex-col justify-between hover:border-primaryBlue/70 hover:bg-panelSecondary focus:outline-none focus:ring-2 focus:ring-primaryBlue cursor-pointer transition-all shadow-sm"
                >
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-1 text-[11px] font-mono text-textMuted border-b border-border/60 pb-1.5">
                      <span>STAGE 0{idx + 1}</span>
                      <span className="flex items-center gap-1 text-[10px] text-slate-400">
                        <FileText size={10} />
                        <span>{stageEvidenceCount} rec</span>
                      </span>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-textPrimary tracking-tight">
                        {stageItem.name}
                      </h3>
                      <div className="mt-2">
                        <StatusBadge status={stStatus} size="sm" />
                      </div>
                    </div>

                    <p className="text-[11px] text-textMuted line-clamp-3 leading-relaxed pt-1">
                      {reason}
                    </p>
                  </div>

                  <div className="mt-4 pt-2 border-t border-border/40 text-[11px] text-primaryBlue font-medium flex items-center justify-between">
                    <span>Inspect Evidence</span>
                    <span className="font-mono text-xs">→</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Diagnosis Quick Summary Banner */}
        {latestRun?.diagnosis && (
          <section className="rounded-lg border border-border bg-panelSecondary p-5 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-xs font-semibold text-textMuted uppercase tracking-wider">
                  Diagnostic Determination
                </span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-lg font-bold text-textPrimary font-mono">
                    {latestRun.diagnosis.outcome}
                  </span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {latestRun.diagnosis.confidence_label}
                  </span>
                </div>
              </div>

              <button
                onClick={() => navigate(`/investigations/${investigation.id}/diagnosis`)}
                className="self-start sm:self-auto px-4 py-2 rounded bg-primaryBlue hover:bg-primaryBlueHover text-white text-xs font-semibold transition-colors"
              >
                Review Diagnosis & Fix
              </button>
            </div>

            <p className="text-xs text-textMuted leading-relaxed">
              {latestRun.diagnosis.reason}
            </p>
          </section>
        )}
      </main>

      {/* Evidence Inspection Modal */}
      <EvidenceModal
        isOpen={isEvidenceModalOpen}
        onClose={() => setIsEvidenceModalOpen(false)}
        stage={selectedStage || ''}
        evidenceRecords={selectedStageEvidence}
        isLoading={loadingEvidence}
      />
    </div>
  );
};
