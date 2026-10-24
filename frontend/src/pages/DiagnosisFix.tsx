import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Investigation, EvidenceRecord } from '../types';
import { Header } from '../components/Header';
import { ProgressIndicator } from '../components/ProgressIndicator';
import { EvidenceModal } from '../components/EvidenceModal';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Info,
  Clock,
  ExternalLink,
} from 'lucide-react';

export const DiagnosisFix: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Review Form
  const [reviewerName, setReviewerName] = useState('Analyst Jane');
  const [reviewNote, setReviewNote] = useState('Reviewed evidence trace; confirmed failure point.');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  // Remediation Form
  const [approverName, setApproverName] = useState('SecOps Lead');
  const [approveNote, setApproveNote] = useState('Approved simulated patch application for retest.');
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);

  // Evidence modal state
  const [modalStage, setModalStage] = useState<string | null>(null);
  const [isEvidenceModalOpen, setIsEvidenceModalOpen] = useState(false);

  const loadData = async () => {
    if (!id) return;
    try {
      const inv = await api.getInvestigation(id);
      setInvestigation(inv);
      const latestRun = inv.runs[inv.runs.length - 1];
      if (latestRun) {
        const ev = await api.getRunEvidence(latestRun.id);
        setEvidenceList(ev);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load diagnosis details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <div className="flex-1 flex items-center justify-center p-8 text-sm text-textMuted">
          Loading diagnosis...
        </div>
      </div>
    );
  }

  if (error || !investigation) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <div className="flex-1 flex items-center justify-center p-8 text-sm text-red-300">
          {error || 'Investigation not found.'}
        </div>
      </div>
    );
  }

  const latestRun = investigation.runs[investigation.runs.length - 1];
  const diag = latestRun?.diagnosis;
  const rem = diag?.remediation;

  const isHealthyOrUndetermined = diag?.outcome === 'HEALTHY' || diag?.outcome === 'UNDETERMINED';
  const isAccepted = diag?.review_status === 'ACCEPT';
  const isApproved = rem?.approval_status === 'APPROVED';

  const handleReview = async (decision: 'ACCEPT' | 'REJECT') => {
    if (!diag) return;
    if (!reviewerName.trim()) {
      setError('Reviewer name is required and cannot be empty.');
      return;
    }
    setIsSubmittingReview(true);
    setError(null);
    try {
      await api.reviewDiagnosis(diag.id, decision, reviewerName.trim(), reviewNote);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to submit review.');
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const handleApprove = async (decision: 'APPROVE' | 'REJECT') => {
    if (!rem) return;
    if (!approverName.trim()) {
      setError('Approver name is required and cannot be empty.');
      return;
    }
    setIsSubmittingApproval(true);
    setError(null);
    try {
      await api.approveRemediation(rem.id, decision, approverName.trim(), approveNote);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to submit remediation decision.');
    } finally {
      setIsSubmittingApproval(false);
    }
  };

  const openEvidenceForRef = (refId: string) => {
    const found = evidenceList.find((e) => e.id.includes(refId) || refId.includes(e.checkpoint_id));
    setModalStage(found ? found.stage : diag?.failure_stage || 'collection');
    setIsEvidenceModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header sourceMode={investigation.source_mode} />
      <ProgressIndicator currentStep={3} investigationId={investigation.id} status={investigation.status} />

      <main className="flex-1 max-w-5xl w-full mx-auto p-6 space-y-8">
        {/* Page Title & Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
          <div>
            <h1 className="text-xl font-bold text-textPrimary">Diagnosis & Remediation Review</h1>
            <p className="text-xs text-textMuted mt-1">
              Review deterministic root-cause finding, evaluate evidence chain, and authorize simulated fix.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(`/investigations/${investigation.id}/trace`)}
              className="text-xs text-textMuted hover:text-textPrimary transition-colors"
            >
              ← Back to Trace
            </button>
            {isApproved && (
              <button
                onClick={() => navigate(`/investigations/${investigation.id}/retest`)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primaryBlue hover:bg-primaryBlueHover text-white text-xs font-semibold transition-colors shadow-sm"
              >
                <span>Continue to Retest</span>
                <ArrowRight size={14} />
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-red-950/80 border border-red-700 text-red-200 text-xs flex items-center gap-2">
            <AlertTriangle size={16} className="text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Section 1: Deterministic Diagnostic Finding */}
        {diag ? (
          <section aria-labelledby="finding-heading" className="rounded-xl border border-border bg-panel p-6 space-y-4 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
              <div>
                <span className="text-xs font-semibold text-textMuted uppercase tracking-wider">
                  Diagnostic Finding
                </span>
                <h2 id="finding-heading" className="text-lg font-bold text-textPrimary font-mono mt-0.5">
                  {diag.outcome}
                  {diag.failure_stage && (
                    <span className="text-primaryBlue ml-2 font-sans font-semibold text-base">
                      (Earliest Failure: {diag.failure_stage})
                    </span>
                  )}
                </h2>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-medium px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {diag.confidence_label}
                </span>
                <span className="text-xs text-textMuted font-mono flex items-center gap-1">
                  <Clock size={12} />
                  <span>{diag.latency_ms} ms</span>
                </span>
              </div>
            </div>

            <div className="text-xs text-textPrimary leading-relaxed bg-slate-900/60 p-4 rounded border border-border">
              {diag.reason}
            </div>

            {/* Clickable Evidence References */}
            {diag.evidence_refs && diag.evidence_refs.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-xs font-semibold text-textMuted uppercase tracking-wider">
                  Supporting Evidence References:
                </span>
                <div className="flex flex-wrap gap-2 pt-1">
                  {diag.evidence_refs.map((refId) => (
                    <button
                      key={refId}
                      onClick={() => openEvidenceForRef(refId)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 font-mono text-xs border border-slate-700 transition-colors"
                    >
                      <span>{refId}</span>
                      <ExternalLink size={11} />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* What is Unknown Section */}
            {diag.limitations && diag.limitations.length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-border/60">
                <span className="text-xs font-semibold text-textMuted uppercase tracking-wider flex items-center gap-1 text-amber-400">
                  <Info size={13} />
                  <span>What is Unknown / Explicit Limitations</span>
                </span>
                <ul className="list-disc list-inside space-y-1 text-xs text-textMuted pl-1">
                  {diag.limitations.map((lim, idx) => (
                    <li key={idx}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        ) : (
          <div className="p-6 rounded-lg border border-border bg-panel text-sm text-textMuted">
            No diagnostic determination found for this run.
          </div>
        )}

        {/* Section 2: For HEALTHY or UNDETERMINED: Show "Evidence to collect next", no remediation controls */}
        {isHealthyOrUndetermined ? (
          <section className="rounded-xl border border-border bg-panel p-6 space-y-4">
            <h3 className="text-sm font-semibold text-textPrimary uppercase tracking-wider">
              Telemetry Guidance: Evidence to Collect Next
            </h3>
            <p className="text-xs text-textMuted">
              {diag?.outcome === 'HEALTHY'
                ? 'All checkpoints evaluated nominally. No corrective remediation required.'
                : 'Telemetry gaps prevent earliest failure attribution without guessing. Collect the following checkpoints to resolve pipeline ambiguity:'}
            </p>
            <div className="rounded bg-slate-900/80 border border-border p-4 text-xs font-mono text-slate-300 space-y-1">
              <div>• Verify raw audit log generation at source checkpoint EG-1</div>
              <div>• Ensure collector agent forwarding heartbeat at COL-1</div>
              <div>• Verify SIEM ingest parser decoded field telemetry at PAR-1</div>
            </div>
            <div className="text-xs text-textMuted italic">
              Notice: No remediation actions can be proposed for non-localized states.
            </div>
          </section>
        ) : (
          <>
            {/* Section 3: Remediation Proposal (Always labelled SIMULATED) */}
            <section aria-labelledby="remediation-heading" className="rounded-xl border border-border bg-panel p-6 space-y-4 shadow-sm">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <h3 id="remediation-heading" className="text-base font-semibold text-textPrimary">
                    Proposed Remediation Action
                  </h3>
                  <span className="text-xs font-mono font-bold text-amber-400">
                    SIMULATED: no real system is modified
                  </span>
                </div>
                <div className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  Status: {rem?.approval_status || 'PENDING'}
                </div>
              </div>

              <div className="p-4 rounded bg-slate-900/90 border border-border text-xs text-slate-200 leading-relaxed font-mono">
                {rem?.proposed_change || 'No specific automated remediation rule available.'}
              </div>

              {/* Review Section */}
              <div className="border-t border-border pt-4 space-y-3">
                <h4 className="text-xs font-semibold text-textMuted uppercase tracking-wider">
                  Step 1: Record Human Analyst Review
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-textMuted uppercase">
                      Reviewer Name (Required)
                    </label>
                    <input
                      type="text"
                      required
                      value={reviewerName}
                      disabled={isAccepted}
                      onChange={(e) => setReviewerName(e.target.value)}
                      className="w-full px-3 py-2 rounded bg-slate-900 border border-border text-xs text-textPrimary focus:outline-none focus:border-primaryBlue disabled:opacity-60"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-textMuted uppercase">
                      Review Note
                    </label>
                    <input
                      type="text"
                      value={reviewNote}
                      disabled={isAccepted}
                      onChange={(e) => setReviewNote(e.target.value)}
                      className="w-full px-3 py-2 rounded bg-slate-900 border border-border text-xs text-textPrimary focus:outline-none focus:border-primaryBlue disabled:opacity-60"
                    />
                  </div>
                </div>

                {!isAccepted ? (
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      type="button"
                      disabled={isSubmittingReview || !reviewerName.trim()}
                      onClick={() => handleReview('ACCEPT')}
                      className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5"
                    >
                      <CheckCircle2 size={14} />
                      <span>Accept Diagnosis</span>
                    </button>
                    <button
                      type="button"
                      disabled={isSubmittingReview || !reviewerName.trim()}
                      onClick={() => handleReview('REJECT')}
                      className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5"
                    >
                      <XCircle size={14} />
                      <span>Reject Diagnosis</span>
                    </button>
                  </div>
                ) : (
                  <div className="p-3 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center justify-between">
                    <span>
                      Diagnosis Accepted by <strong>{diag?.reviewed_by}</strong> on {diag?.reviewed_at?.slice(0, 16)} ({diag?.review_note})
                    </span>
                    <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-emerald-900">ACCEPTED</span>
                  </div>
                )}
              </div>

              {/* Remediation Approval Section */}
              <div className="border-t border-border pt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-textMuted uppercase tracking-wider">
                    Step 2: Remediation Approval & Simulated Execution
                  </h4>
                  {!isAccepted && (
                    <span className="text-[11px] text-amber-400 italic">
                      Approve disabled until diagnosis review is recorded ACCEPT
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-textMuted uppercase">
                      Approver Name (Required)
                    </label>
                    <input
                      type="text"
                      required
                      value={approverName}
                      disabled={!isAccepted || isApproved}
                      onChange={(e) => setApproverName(e.target.value)}
                      className="w-full px-3 py-2 rounded bg-slate-900 border border-border text-xs text-textPrimary focus:outline-none focus:border-primaryBlue disabled:opacity-60"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="block text-[11px] text-textMuted uppercase">
                      Approval Note
                    </label>
                    <input
                      type="text"
                      value={approveNote}
                      disabled={!isAccepted || isApproved}
                      onChange={(e) => setApproveNote(e.target.value)}
                      className="w-full px-3 py-2 rounded bg-slate-900 border border-border text-xs text-textPrimary focus:outline-none focus:border-primaryBlue disabled:opacity-60"
                    />
                  </div>
                </div>

                {!isApproved ? (
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      type="button"
                      disabled={!isAccepted || isSubmittingApproval || !approverName.trim()}
                      onClick={() => handleApprove('APPROVE')}
                      className="px-5 py-2.5 rounded bg-primaryBlue hover:bg-primaryBlueHover text-white text-xs font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-sm"
                    >
                      <CheckCircle2 size={14} />
                      <span>Approve Simulated Fix</span>
                    </button>
                    <button
                      type="button"
                      disabled={!isAccepted || isSubmittingApproval || !approverName.trim()}
                      onClick={() => handleApprove('REJECT')}
                      className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                    >
                      <XCircle size={14} />
                      <span>Reject Fix</span>
                    </button>
                  </div>
                ) : (
                  <div className="p-3 rounded bg-blue-950/60 border border-blue-800 text-blue-200 text-xs flex items-center justify-between">
                    <div>
                      <span>Remediation Approved by <strong>{rem?.approved_by}</strong> on {rem?.decided_at?.slice(0, 16)}</span>
                      <div className="text-[11px] text-blue-300 mt-0.5">Execution Status: <code>SIMULATED_APPLIED</code> (Ready for retest)</div>
                    </div>
                    <button
                      onClick={() => navigate(`/investigations/${investigation.id}/retest`)}
                      className="px-3.5 py-1.5 rounded bg-primaryBlue hover:bg-primaryBlueHover text-white font-semibold text-xs flex items-center gap-1"
                    >
                      <span>Go to Retest</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </main>

      {/* Evidence Modal */}
      <EvidenceModal
        isOpen={isEvidenceModalOpen}
        onClose={() => setIsEvidenceModalOpen(false)}
        stage={modalStage || ''}
        evidenceRecords={evidenceList.filter((e) => e.stage === modalStage)}
        isLoading={false}
      />
    </div>
  );
};
