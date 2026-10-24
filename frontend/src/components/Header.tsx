import React from 'react';
import { Link } from 'react-router-dom';
import { Database, Shield } from 'lucide-react';

interface HeaderProps {
  sourceMode?: 'DEMO' | 'WAZUH';
}

export const Header: React.FC<HeaderProps> = ({ sourceMode = 'DEMO' }) => {
  return (
    <header className="border-b border-border bg-panel sticky top-0 z-40 px-6 py-3.5 shadow-md">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <Link to="/" className="flex items-center gap-3 group focus:outline-none focus:ring-2 focus:ring-primaryBlue rounded-md p-1">
          {/* Simple crisp SVG shield with trace/check, strictly no gradients */}
          <div className="w-9 h-9 rounded bg-slate-900 border border-primaryBlue flex items-center justify-center text-primaryBlue group-hover:border-accentCyan transition-colors">
            <svg
              className="w-5 h-5 text-primaryBlue group-hover:text-accentCyan transition-colors"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-wider text-textPrimary font-mono">
                PRECRIME<span className="text-primaryBlue"> AI</span>
              </span>
              <span className="text-[11px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                SIEM Investigator
              </span>
            </div>
            <p className="text-xs text-textMuted tracking-tight">
              Find the failure. Prove the cause. Verify the fix.
            </p>
          </div>
        </Link>

        <div className="flex items-center gap-4 self-end md:self-auto">
          {sourceMode === 'WAZUH' ? (
            <div
              role="status"
              aria-label="Active source: WAZUH LIVE"
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-cyan-950/70 border border-cyan-800/80 text-cyan-300 text-xs font-mono font-medium"
            >
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>WAZUH LIVE</span>
            </div>
          ) : (
            <div
              role="status"
              aria-label="Active source: SYNTHETIC DEMO"
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-slate-800/80 border border-slate-700 text-slate-300 text-xs font-mono font-medium"
            >
              <Database size={13} className="text-textMuted" />
              <span>SYNTHETIC DEMO</span>
            </div>
          )}

          <Link
            to="/"
            className="text-xs font-medium text-textMuted hover:text-textPrimary transition-colors px-2 py-1"
          >
            All Investigations
          </Link>
        </div>
      </div>
    </header>
  );
};
