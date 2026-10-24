import React from 'react';
import { Check, Circle } from 'lucide-react';
import { Link } from 'react-router-dom';

interface ProgressIndicatorProps {
  currentStep: 1 | 2 | 3 | 4;
  investigationId?: string;
  status?: string;
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  currentStep,
  investigationId,
}) => {
  const steps = [
    { num: 1, label: 'Setup', path: '/' },
    { num: 2, label: 'Pipeline Trace', path: investigationId ? `/investigations/${investigationId}/trace` : '#' },
    { num: 3, label: 'Diagnosis & Fix', path: investigationId ? `/investigations/${investigationId}/diagnosis` : '#' },
    { num: 4, label: 'Retest & Report', path: investigationId ? `/investigations/${investigationId}/retest` : '#' },
  ];

  return (
    <nav aria-label="Investigation progress" className="w-full bg-panel border-b border-border py-2.5 px-6">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <ol className="flex items-center w-full justify-between gap-2">
          {steps.map((step, idx) => {
            const isCompleted = step.num < currentStep;
            const isCurrent = step.num === currentStep;
            const isClickable = Boolean(investigationId) && step.num <= currentStep;

            const content = (
              <div className="flex items-center gap-2">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-bold transition-colors ${
                    isCompleted
                      ? 'bg-emerald-950 border border-emerald-600 text-emerald-400'
                      : isCurrent
                      ? 'bg-primaryBlue border border-blue-400 text-white shadow-sm'
                      : 'bg-slate-800 border border-slate-700 text-textMuted'
                  }`}
                >
                  {isCompleted ? <Check size={13} /> : step.num}
                </div>
                <span
                  className={`text-xs font-medium ${
                    isCurrent
                      ? 'text-textPrimary font-semibold'
                      : isCompleted
                      ? 'text-emerald-400/90'
                      : 'text-textMuted'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            );

            return (
              <React.Fragment key={step.num}>
                <li className="flex items-center">
                  {isClickable && step.path !== '#' ? (
                    <Link to={step.path} className="hover:opacity-80 transition-opacity focus:outline-none focus:ring-1 focus:ring-primaryBlue rounded px-1">
                      {content}
                    </Link>
                  ) : (
                    <div>{content}</div>
                  )}
                </li>
                {idx < steps.length - 1 && (
                  <div
                    aria-hidden="true"
                    className={`flex-1 h-0.5 mx-3 hidden sm:block ${
                      step.num < currentStep ? 'bg-emerald-700/60' : 'bg-slate-800'
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </ol>
      </div>
    </nav>
  );
};
