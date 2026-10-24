import React, { useState } from 'react';
import { MetricsData } from '../types';
import { api } from '../api/client';
import { Play, RefreshCw, AlertCircle, Info, CheckCircle2 } from 'lucide-react';

interface MetricsPanelProps {
  metrics: MetricsData | null;
  onRefresh: () => void;
  className?: string;
}

export const MetricsPanel: React.FC<MetricsPanelProps> = ({ metrics, onRefresh, className = '' }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'combined' | 'development' | 'held_out'>('combined');
  const [error, setError] = useState<string | null>(null);

  const handleRunSuite = async () => {
    setIsRunning(true);
    setError(null);
    try {
      await api.runEvaluationSuite();
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Failed to execute evaluation suite');
    } finally {
      setIsRunning(false);
    }
  };

  if (!metrics || !metrics.has_data || !metrics.combined) {
    return (
      <div className={`rounded-lg border border-border bg-panel p-6 ${className}`}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-textPrimary flex items-center gap-2">
              <span>Empirical Validation Metrics</span>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-textMuted border border-slate-700">
                12-Case Benchmark
              </span>
            </h3>
            <p className="text-sm text-textMuted mt-1">
              {metrics?.message || 'No evaluation has been run yet. Run the validation suite to compute empirical metrics from test cases.'}
            </p>
          </div>
          <button
            onClick={handleRunSuite}
            disabled={isRunning}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primaryBlue hover:bg-primaryBlueHover text-white text-sm font-medium transition-colors disabled:opacity-50 shadow-sm shrink-0"
          >
            {isRunning ? (
              <>
                <RefreshCw size={15} className="animate-spin" />
                <span>Running Suite (12 cases)...</span>
              </>
            ) : (
              <>
                <Play size={15} />
                <span>Run Validation Suite</span>
              </>
            )}
          </button>
        </div>
        {error && (
          <div className="mt-4 p-3 rounded bg-red-950/60 border border-red-800/80 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle size={15} />
            <span>{error}</span>
          </div>
        )}
      </div>
    );
  }

  const currentSlice =
    activeTab === 'development'
      ? metrics.development
      : activeTab === 'held_out'
      ? metrics.held_out
      : metrics.combined;

  return (
    <div className={`rounded-lg border border-border bg-panel overflow-hidden ${className}`}>
      {/* Header bar */}
      <div className="p-5 border-b border-border flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-textPrimary">Empirical Engine Metrics</h3>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300">
              Verified from DB rows
            </span>
          </div>
          <p className="text-xs text-textMuted mt-1">
            {metrics.disclaimer || 'Evaluated on 12 synthetic cases. Not a measure of production accuracy.'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Slice Selector Tabs */}
          <div className="inline-flex rounded-md p-1 bg-slate-900 border border-border text-xs font-medium">
            <button
              onClick={() => setActiveTab('combined')}
              className={`px-2.5 py-1 rounded transition-colors ${
                activeTab === 'combined'
                  ? 'bg-primaryBlue text-white shadow-sm font-semibold'
                  : 'text-textMuted hover:text-textPrimary'
              }`}
            >
              Combined ({metrics.combined.case_count})
            </button>
            <button
              onClick={() => setActiveTab('development')}
              className={`px-2.5 py-1 rounded transition-colors ${
                activeTab === 'development'
                  ? 'bg-primaryBlue text-white shadow-sm font-semibold'
                  : 'text-textMuted hover:text-textPrimary'
              }`}
            >
              Development ({metrics.development?.case_count || 6})
            </button>
            <button
              onClick={() => setActiveTab('held_out')}
              className={`px-2.5 py-1 rounded transition-colors ${
                activeTab === 'held_out'
                  ? 'bg-primaryBlue text-white shadow-sm font-semibold'
                  : 'text-textMuted hover:text-textPrimary'
              }`}
            >
              Held-Out ({metrics.held_out?.case_count || 6})
            </button>
          </div>

          <button
            onClick={handleRunSuite}
            disabled={isRunning}
            aria-label="Re-run validation suite"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-borderLight transition-colors disabled:opacity-50"
          >
            <RefreshCw size={13} className={isRunning ? 'animate-spin' : ''} />
            <span>{isRunning ? 'Running...' : 'Re-run'}</span>
          </button>
        </div>
      </div>

      {/* Grid of Metric Cards */}
      <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Card 1: Localization Accuracy */}
        <div className="rounded border border-border bg-panelSecondary p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-textMuted tracking-wider uppercase">
              Failure Localization Accuracy
            </span>
            <div className="text-2xl font-bold font-mono text-emerald-400 mt-2">
              {currentSlice.failure_localization_accuracy.display}
            </div>
          </div>
          <p className="text-[11px] text-textMuted mt-3 border-t border-border/60 pt-2">
            {currentSlice.failure_localization_accuracy.definition}
          </p>
        </div>

        {/* Card 2: False Attribution Rate */}
        <div className="rounded border border-border bg-panelSecondary p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-textMuted tracking-wider uppercase">
              False Attribution Rate
            </span>
            <div className="text-2xl font-bold font-mono text-cyan-400 mt-2">
              {currentSlice.false_attribution_rate.display}
            </div>
          </div>
          <p className="text-[11px] text-textMuted mt-3 border-t border-border/60 pt-2">
            {currentSlice.false_attribution_rate.definition}
          </p>
        </div>

        {/* Card 3: Abstention Quality */}
        <div className="rounded border border-border bg-panelSecondary p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-textMuted tracking-wider uppercase">
              Abstention on Gaps / Conflicts
            </span>
            <div className="text-2xl font-bold font-mono text-amber-400 mt-2">
              {currentSlice.abstention_quality.supported_abstention.display}
            </div>
          </div>
          <p className="text-[11px] text-textMuted mt-3 border-t border-border/60 pt-2">
            Unnecessary abstentions: <span className="font-mono text-slate-300 font-semibold">{currentSlice.abstention_quality.unnecessary_abstention.display}</span>
          </p>
        </div>

        {/* Card 4: Retest Accuracy */}
        <div className="rounded border border-border bg-panelSecondary p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-textMuted tracking-wider uppercase">
              Retest Verification Accuracy
            </span>
            <div className="text-2xl font-bold font-mono text-emerald-400 mt-2">
              {currentSlice.retest_verification_accuracy.display}
            </div>
          </div>
          <p className="text-[11px] text-textMuted mt-3 border-t border-border/60 pt-2">
            {currentSlice.retest_verification_accuracy.definition}
          </p>
        </div>

        {/* Card 5: Evidence Coverage */}
        <div className="rounded border border-border bg-panelSecondary p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-textMuted tracking-wider uppercase">
              Checkpoint Evidence Coverage
            </span>
            <div className="text-2xl font-bold font-mono text-blue-400 mt-2">
              {currentSlice.evidence_coverage.display}
            </div>
          </div>
          <p className="text-[11px] text-textMuted mt-3 border-t border-border/60 pt-2">
            {currentSlice.evidence_coverage.definition}
          </p>
        </div>

        {/* Card 6: Diagnosis Latency */}
        <div className="rounded border border-border bg-panelSecondary p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-textMuted tracking-wider uppercase">
              Diagnosis Latency
            </span>
            <div className="text-lg font-bold font-mono text-slate-200 mt-2 flex items-baseline gap-2">
              <span>{currentSlice.diagnosis_latency.mean_ms} ms</span>
              <span className="text-xs font-normal text-textMuted">
                (med: {currentSlice.diagnosis_latency.median_ms}ms, max: {currentSlice.diagnosis_latency.max_ms}ms)
              </span>
            </div>
          </div>
          <p className="text-[11px] text-textMuted mt-3 border-t border-border/60 pt-2">
            Manual analyst baseline: <span className="italic text-slate-400">{currentSlice.diagnosis_latency.manual_baseline}</span>
          </p>
        </div>
      </div>

      {/* Footer Note */}
      <div className="px-5 py-3 bg-slate-900/60 border-t border-border flex items-center gap-2 text-xs text-textMuted">
        <Info size={14} className="text-slate-400 shrink-0" />
        <span>
          Precision, Recall, F1, and ROC-AUC are intentionally omitted as SIEM detection failure triage does not represent a valid binary classification task.
        </span>
      </div>
    </div>
  );
};
