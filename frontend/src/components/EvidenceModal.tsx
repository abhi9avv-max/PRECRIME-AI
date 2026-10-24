import React from 'react';
import { X, Hash, Calendar, Server } from 'lucide-react';
import { EvidenceRecord, PipelineStage } from '../types';

interface EvidenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  stage: PipelineStage | string;
  expectedInfo?: Record<string, any>;
  evidenceRecords: EvidenceRecord[];
  isLoading: boolean;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({
  isOpen,
  onClose,
  stage,
  expectedInfo,
  evidenceRecords,
  isLoading,
}) => {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Evidence for stage ${stage}`}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
    >
      <div className="bg-panel border border-border rounded-lg max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-panelSecondary">
          <div>
            <h3 className="text-base font-semibold text-textPrimary flex items-center gap-2">
              <span>Evidence Records</span>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300">
                {stage}
              </span>
            </h3>
            <p className="text-xs text-textMuted mt-0.5">
              Append-only telemetry checkpoint records and cryptographic hashes
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close evidence modal"
            className="p-1 rounded hover:bg-slate-800 text-textMuted hover:text-textPrimary transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Expected vs Observed Summary */}
          {expectedInfo && (
            <div className="rounded border border-border bg-slate-900/60 p-4">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-2">
                Stage Expectation Specification
              </h4>
              <pre className="text-xs font-mono text-slate-300 overflow-x-auto p-2 bg-slate-950 rounded border border-slate-800">
                {JSON.stringify(expectedInfo, null, 2)}
              </pre>
            </div>
          )}

          {/* Evidence Records List */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-3 flex items-center justify-between">
              <span>Observed Checkpoint Records ({evidenceRecords.length})</span>
            </h4>

            {isLoading ? (
              <div className="py-8 text-center text-sm text-textMuted flex items-center justify-center gap-2">
                <span className="w-2 h-2 rounded-full bg-primaryBlue animate-ping" />
                <span>Loading checkpoint telemetry...</span>
              </div>
            ) : evidenceRecords.length === 0 ? (
              <div className="rounded border border-dashed border-border p-6 text-center text-sm text-textMuted">
                No telemetry records found for this stage checkpoint.
              </div>
            ) : (
              <div className="space-y-4">
                {evidenceRecords.map((rec) => (
                  <div
                    key={rec.id}
                    className="rounded border border-border bg-panelSecondary p-4 space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs border-b border-border/60 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-textPrimary">
                          {rec.checkpoint_id}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded font-mono font-semibold text-[11px] ${
                            rec.availability === 'AVAILABLE'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : 'bg-amber-950 text-amber-400 border border-amber-800'
                          }`}
                        >
                          {rec.availability}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[11px] flex items-center gap-1">
                          <Server size={11} />
                          <span>{rec.source_label}</span>
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-textMuted text-[11px]">
                        <span className="flex items-center gap-1">
                          <Calendar size={11} />
                          <span>{new Date(rec.observed_at).toLocaleTimeString()}</span>
                        </span>
                        <span className="flex items-center gap-1 font-mono text-slate-400">
                          <Hash size={11} />
                          <span>{rec.content_hash.slice(0, 10)}...</span>
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-[11px] font-semibold text-textMuted uppercase">
                        Payload (Secrets Redacted):
                      </span>
                      <pre className="text-xs font-mono text-slate-300 bg-slate-950 p-2.5 rounded border border-slate-800 mt-1.5 overflow-x-auto max-h-48">
                        {JSON.stringify(rec.payload, null, 2)}
                      </pre>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border bg-panelSecondary flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-textPrimary border border-borderLight transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
