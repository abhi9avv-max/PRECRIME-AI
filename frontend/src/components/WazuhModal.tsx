import React, { useState } from 'react';
import { X, CheckCircle2, AlertTriangle, RefreshCw, ShieldAlert } from 'lucide-react';
import { api } from '../api/client';

interface WazuhModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  onSwitchToDemo: () => void;
}

export const WazuhModal: React.FC<WazuhModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  onSwitchToDemo,
}) => {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{ connected: boolean; message: string } | null>(null);

  if (!isOpen) return null;

  const handleTest = async () => {
    setTesting(true);
    setResult(null);
    try {
      const res = await api.testWazuh();
      setResult(res);
      if (res.connected) {
        onSuccess();
      }
    } catch (err: any) {
      setResult({
        connected: false,
        message: err.message || 'Error executing Wazuh connectivity check.',
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Wazuh Connection Test"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
    >
      <div className="bg-panel border border-border rounded-lg max-w-md w-full shadow-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between bg-panelSecondary">
          <div className="flex items-center gap-2">
            <ShieldAlert size={18} className="text-cyan-400" />
            <h3 className="text-sm font-semibold text-textPrimary">Wazuh SIEM Connection</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-slate-800 text-textMuted hover:text-textPrimary transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-xs text-textMuted leading-relaxed">
            Live Wazuh mode connects to your configured Wazuh Manager API endpoint using server environment credentials (<code className="text-cyan-300">WAZUH_API_URL</code>, <code className="text-cyan-300">WAZUH_API_USER</code>, <code className="text-cyan-300">WAZUH_API_PASSWORD</code>).
          </p>

          <div className="rounded bg-slate-900/80 border border-border p-3 text-xs space-y-2">
            <div className="font-semibold text-textPrimary">Read-Only Live Testing</div>
            <div className="text-textMuted">
              PRECRIME AI tests authentication only and never alters Wazuh manager configuration. Evidence collection for live Wazuh is currently not implemented.
            </div>
          </div>

          {result && (
            <div
              className={`p-3 rounded text-xs flex items-start gap-2.5 ${
                result.connected
                  ? 'bg-emerald-950/70 border border-emerald-800 text-emerald-300'
                  : 'bg-red-950/70 border border-red-800 text-red-300'
              }`}
            >
              {result.connected ? (
                <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
              )}
              <div className="space-y-1">
                <div className="font-semibold">
                  {result.connected ? 'Connection Established' : 'Connection Failed'}
                </div>
                <div className="text-[11px] leading-relaxed">{result.message}</div>
              </div>
            </div>
          )}
        </div>

        <div className="px-5 py-3.5 border-t border-border bg-panelSecondary flex items-center justify-between gap-3">
          <button
            onClick={() => {
              onSwitchToDemo();
              onClose();
            }}
            className="text-xs text-textMuted hover:text-textPrimary transition-colors underline"
          >
            Switch to Synthetic Demo
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={handleTest}
              disabled={testing}
              className="px-3.5 py-1.5 rounded bg-primaryBlue hover:bg-primaryBlueHover text-white text-xs font-medium transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              {testing ? (
                <>
                  <RefreshCw size={13} className="animate-spin" />
                  <span>Testing...</span>
                </>
              ) : (
                <span>Test Connection</span>
              )}
            </button>
            {result?.connected && (
              <button
                onClick={onClose}
                className="px-3.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors"
              >
                Use Wazuh
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
